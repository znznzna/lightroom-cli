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
