import asyncio

import pytest

from lightroom_sdk.resilient_bridge import ConnectionState, ResilientSocketBridge


@pytest.mark.asyncio
async def test_initial_state_is_disconnected():
    bridge = ResilientSocketBridge(port_file="/tmp/nonexistent.txt")
    assert bridge.state == ConnectionState.DISCONNECTED


@pytest.mark.asyncio
async def test_connect_transitions_to_connected(mock_lr_server):
    mock_lr_server.register_response("system.ping", {"status": "ok"})
    bridge = ResilientSocketBridge(port_file=str(mock_lr_server.port_file))
    await bridge.connect()
    assert bridge.state == ConnectionState.CONNECTED
    await bridge.disconnect()


@pytest.mark.asyncio
async def test_auto_reconnect_on_send_failure(mock_lr_server):
    """接続断後のsend_command()が自動再接続する"""
    mock_lr_server.register_response("system.ping", {"status": "ok"})
    bridge = ResilientSocketBridge(
        port_file=str(mock_lr_server.port_file),
        max_reconnect_attempts=2,
        heartbeat_interval=0,  # テスト用: ハートビート無効
    )
    await bridge.connect()

    # 内部bridgeを強制切断
    bridge._bridge._connected = False

    # send_commandが自動再接続を試みる
    result = await bridge.send_command("system.ping")
    assert result["result"]["status"] == "ok"
    assert bridge.state == ConnectionState.CONNECTED
    await bridge.disconnect()


@pytest.mark.asyncio
async def test_shutdown_event_transitions_to_shutdown(mock_lr_server):
    """server.shutdownイベントでSHUTDOWN状態になる"""
    bridge = ResilientSocketBridge(
        port_file=str(mock_lr_server.port_file),
        heartbeat_interval=0,
    )
    await bridge.connect()
    await mock_lr_server.wait_for_client()

    await mock_lr_server.send_event("server.shutdown", {"reason": "test"})
    await asyncio.sleep(0.3)

    assert bridge.state == ConnectionState.SHUTDOWN


# --- 接続断のあとで再送してよいか（H-3） -------------------------------------------


@pytest.fixture
def lost_after_send(monkeypatch):
    """要求を実際に Lightroom（モック）へ届けたあとで、応答を受け取る前に接続が切れたことにする。

    対象のコマンドは 1 回目だけ切れる。2 回目以降と他のコマンドはそのまま通す。
    """
    from lightroom_sdk.socket_bridge import SocketBridge

    original = SocketBridge.send_command
    targets: set[str] = set()

    async def send_then_lose(self, command, params=None, timeout=30.0, **kwargs):
        response = await original(self, command, params, timeout, **kwargs)
        if command in targets:
            targets.discard(command)
            raise ConnectionResetError("connection reset after the request was sent")
        return response

    monkeypatch.setattr(SocketBridge, "send_command", send_then_lose)
    return targets


async def _connected_bridge(server) -> ResilientSocketBridge:
    server.register_response("system.ping", {"status": "ok"})
    bridge = ResilientSocketBridge(port_file=str(server.port_file), max_reconnect_attempts=2, heartbeat_interval=0)
    await bridge.connect()
    return bridge


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "command",
    [
        "develop.setValue",  # mutating
        "develop.createAIMaskWithAdjustments",  # mutating（マスクが 2 枚できる）
        "selection.nextPhoto",  # 読み取りだが、2 回送ると 2 枚進む
        "develop.toggleOverlay",  # 読み取りだが、2 回送ると元に戻る
        "no.suchCommand",  # スキーマにないコマンドは安全側に倒す
    ],
)
async def test_unsafe_command_is_not_resent_after_connection_lost(mock_lr_server, lost_after_send, command):
    from lightroom_sdk.exceptions import ResultUnknownError

    bridge = await _connected_bridge(mock_lr_server)
    lost_after_send.add(command)

    with pytest.raises(ResultUnknownError) as excinfo:
        await bridge.send_command(command, {"param": "Exposure", "value": 0.5})

    assert excinfo.value.code == "RESULT_UNKNOWN"
    assert mock_lr_server.received.count(command) == 1
    assert bridge.state == ConnectionState.DISCONNECTED

    # 次のコマンドは新しい接続で普通に通る
    result = await bridge.send_command("system.ping")
    assert result["result"]["status"] == "ok"
    assert bridge.state == ConnectionState.CONNECTED
    assert mock_lr_server.received.count(command) == 1
    await bridge.disconnect()


@pytest.mark.asyncio
async def test_retry_safe_read_is_resent_after_connection_lost(mock_lr_server, lost_after_send):
    mock_lr_server.register_response("develop.getSettings", {"Exposure": 0.5})
    bridge = await _connected_bridge(mock_lr_server)
    lost_after_send.add("develop.getSettings")

    result = await bridge.send_command("develop.getSettings")

    assert result["result"] == {"Exposure": 0.5}
    assert mock_lr_server.received.count("develop.getSettings") == 2
    assert bridge.state == ConnectionState.CONNECTED
    await bridge.disconnect()


@pytest.mark.asyncio
async def test_mutating_command_is_sent_once_when_connection_was_already_down(mock_lr_server):
    """送る前から切れていたなら、何も届いていないので再接続して 1 回だけ送る"""
    bridge = await _connected_bridge(mock_lr_server)
    bridge._bridge._connected = False

    result = await bridge.send_command("develop.setValue", {"param": "Exposure", "value": 0.5})

    assert result["success"] is True
    assert mock_lr_server.received.count("develop.setValue") == 1
    await bridge.disconnect()


def test_retry_safe_flags():
    from lightroom_sdk.schema import COMMAND_SCHEMAS

    assert COMMAND_SCHEMAS["develop.getSettings"].retry_safe
    assert COMMAND_SCHEMAS["catalog.searchPhotos"].retry_safe
    for name in ("develop.setValue", "selection.nextPhoto", "selection.previousPhoto", "develop.toggleOverlay"):
        assert not COMMAND_SCHEMAS[name].retry_safe, name


@pytest.mark.asyncio
async def test_mcp_returns_result_unknown(mock_lr_server, lost_after_send):
    from mcp_server.connection import ConnectionManager

    mock_lr_server.register_response("system.ping", {"status": "ok"})
    cm = ConnectionManager(port_file=str(mock_lr_server.port_file))
    await cm.execute("system.ping", {}, timeout=5.0, mutating=False)
    lost_after_send.add("selection.nextPhoto")

    result = await cm.execute("selection.nextPhoto", {}, timeout=5.0, mutating=False)

    assert result["isError"] is True
    assert result["code"] == "RESULT_UNKNOWN"
    assert mock_lr_server.received.count("selection.nextPhoto") == 1
    await cm.shutdown()


def test_cli_reports_result_unknown():
    import json
    from unittest.mock import AsyncMock, patch

    from click.testing import CliRunner

    from cli.main import cli
    from lightroom_sdk.exceptions import ResultUnknownError

    bridge = AsyncMock()
    bridge.send_command.side_effect = ResultUnknownError("lost")
    with patch("cli.helpers.get_bridge", return_value=bridge):
        result = CliRunner().invoke(cli, ["-o", "json", "selection", "next"])

    assert result.exit_code == 3
    assert json.loads(result.stderr)["error"]["code"] == "RESULT_UNKNOWN"


@pytest.mark.asyncio
async def test_heartbeat_does_not_pile_up_after_result_unknown(mock_lr_server, lost_after_send):
    """結果不明で接続を捨てて繋ぎ直しても、ハートビートは 1 本だけ"""
    mock_lr_server.register_response("system.ping", {"status": "ok"})
    bridge = ResilientSocketBridge(port_file=str(mock_lr_server.port_file), heartbeat_interval=0.05)
    await bridge.connect()
    first = bridge._heartbeat_task
    lost_after_send.add("develop.setValue")

    from lightroom_sdk.exceptions import ResultUnknownError

    with pytest.raises(ResultUnknownError):
        await bridge.send_command("develop.setValue", {"param": "Exposure", "value": 0.5})
    await bridge.send_command("system.ping")

    assert first.done()
    alive = [t for t in asyncio.all_tasks() if t.get_coro().__qualname__.endswith("_heartbeat_loop")]
    assert alive == [bridge._heartbeat_task]
    await bridge.disconnect()
    assert bridge._heartbeat_task is None


@pytest.mark.asyncio
async def test_drop_during_resend_is_result_unknown(mock_lr_server, lost_after_send):
    """送信前に切れていて再接続後に送り、その送信中に切れた場合も結果不明として返す"""
    from lightroom_sdk.exceptions import ResultUnknownError

    bridge = await _connected_bridge(mock_lr_server)
    bridge._bridge._connected = False
    lost_after_send.add("develop.setValue")

    with pytest.raises(ResultUnknownError):
        await bridge.send_command("develop.setValue", {"param": "Exposure", "value": 0.5})

    assert mock_lr_server.received.count("develop.setValue") == 1
    assert bridge.state == ConnectionState.DISCONNECTED
    await bridge.disconnect()


@pytest.mark.asyncio
async def test_retry_safe_read_gives_up_after_second_drop(mock_lr_server, monkeypatch):
    """読み取りでも再送は 1 回だけ。2 回目も切れたら接続エラーをそのまま返す"""
    from lightroom_sdk.socket_bridge import SocketBridge

    original = SocketBridge.send_command

    async def always_lose(self, command, params=None, timeout=30.0, **kwargs):
        response = await original(self, command, params, timeout, **kwargs)
        if command == "develop.getSettings":
            raise ConnectionResetError("lost again")
        return response

    monkeypatch.setattr(SocketBridge, "send_command", always_lose)
    bridge = await _connected_bridge(mock_lr_server)

    with pytest.raises(ConnectionResetError):
        await bridge.send_command("develop.getSettings")

    assert mock_lr_server.received.count("develop.getSettings") == 2
    assert bridge.state == ConnectionState.DISCONNECTED
    await bridge.disconnect()


@pytest.mark.asyncio
async def test_cleanup_after_result_unknown_does_not_close_dropped_bridge_again(mock_lr_server, lost_after_send):
    """捨てた bridge を後片付けで閉じ直さない（閉じ直しの例外で RESULT_UNKNOWN が消えないように）"""
    from lightroom_sdk.exceptions import ResultUnknownError

    bridge = await _connected_bridge(mock_lr_server)
    dropped = bridge._bridge
    calls = []

    async def failing_disconnect():
        calls.append(1)
        raise ConnectionResetError("reset while closing")

    dropped.disconnect = failing_disconnect
    lost_after_send.add("develop.setValue")

    with pytest.raises(ResultUnknownError):
        await bridge.send_command("develop.setValue", {"param": "Exposure", "value": 0.5})
    await bridge.disconnect()  # CLI の finally と同じ後片付け

    assert calls == [1]
    assert bridge._bridge is None


@pytest.mark.asyncio
async def test_drop_does_not_close_a_bridge_reconnected_meanwhile(mock_lr_server, lost_after_send):
    """ハートビートの停止を待つ間に別のコマンドが繋ぎ直しても、その新しい接続は閉じない"""
    from lightroom_sdk.exceptions import ResultUnknownError

    mock_lr_server.register_response("system.ping", {"status": "ok"})
    bridge = ResilientSocketBridge(port_file=str(mock_lr_server.port_file), heartbeat_interval=30)
    await bridge.connect()
    original_stop = bridge._stop_heartbeat
    concurrent = []
    started = []

    async def stop_with_concurrent_command():
        await original_stop()
        if not started:  # 1 回目（_drop_bridge の中）だけ、待ち時間の間に別のコマンドを走らせる
            started.append(True)
            concurrent.append(await bridge.send_command("system.ping"))

    bridge._stop_heartbeat = stop_with_concurrent_command
    lost_after_send.add("develop.setValue")

    with pytest.raises(ResultUnknownError):
        await bridge.send_command("develop.setValue", {"param": "Exposure", "value": 0.5})

    assert concurrent and concurrent[0]["result"]["status"] == "ok"
    assert bridge.state == ConnectionState.CONNECTED
    assert bridge._bridge is not None and bridge._bridge._connected
    result = await bridge.send_command("system.ping")
    assert result["result"]["status"] == "ok"
    await bridge.disconnect()
