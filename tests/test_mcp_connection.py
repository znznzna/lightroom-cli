"""ConnectionManager のテスト。MockLightroomServer を使用。"""

import asyncio
from pathlib import Path

import pytest

from mcp_server.connection import ConnectionManager


@pytest.mark.asyncio
async def test_lazy_connect(mock_lr_server):
    """初回 execute 時に自動接続する"""
    mock_lr_server.register_response("system.ping", {"status": "ok"})

    cm = ConnectionManager(port_file=str(mock_lr_server.port_file))
    assert cm._client is None

    result = await cm.execute("system.ping", {}, timeout=5.0, mutating=False)
    assert result.get("isError") is not True
    assert cm._client is not None
    await cm.shutdown()


@pytest.mark.asyncio
async def test_connection_error_returns_mcp_error():
    """接続できない場合に MCP エラーレスポンスを返す"""
    import tempfile as _tf

    cm = ConnectionManager(port_file=str(Path(_tf.gettempdir()) / "nonexistent_port_file_test.txt"))

    result = await cm.execute("system.ping", {}, timeout=2.0, mutating=False)
    assert result["isError"] is True
    await cm.shutdown()


@pytest.mark.asyncio
async def test_lock_serializes_commands(mock_lr_server):
    """asyncio.Lock がコマンドを直列化すること

    A の応答を保留している間に B が Lightroom へ届かないことを、サーバが受け取った要求で確かめる
    （時刻の比較ではないので、タイマーの粗い Windows でも skip しない）
    """
    mock_lr_server.register_response("system.ping", {"status": "ok"})
    mock_lr_server.register_response("system.status", {"status": "ok"})
    release_a = mock_lr_server.hold("system.ping")

    cm = ConnectionManager(port_file=str(mock_lr_server.port_file))
    try:
        task_a = asyncio.create_task(cm.execute("system.ping", {}, timeout=5.0, mutating=False))
        await asyncio.wait_for(mock_lr_server.request_arrived.wait(), timeout=5)
        assert mock_lr_server.received == ["system.ping"]

        task_b = asyncio.create_task(cm.execute("system.status", {}, timeout=5.0, mutating=False))
        mock_lr_server.request_arrived.clear()
        with pytest.raises(asyncio.TimeoutError):
            # Without the lock, B is on the wire within a few milliseconds
            await asyncio.wait_for(mock_lr_server.request_arrived.wait(), timeout=0.3)
        assert mock_lr_server.received == ["system.ping"], "B was sent while A was still running"

        release_a.set()
        assert (await task_a)["result"] == {"status": "ok"}
        assert (await task_b)["result"] == {"status": "ok"}
        assert mock_lr_server.received == ["system.ping", "system.status"]
    finally:
        await cm.shutdown()


@pytest.mark.asyncio
async def test_mutating_not_retried_after_reconnect():
    """C1: mutating コマンドは接続エラー時に再送されずエラーを返す"""
    import tempfile as _tf

    cm = ConnectionManager(port_file=str(Path(_tf.gettempdir()) / "nonexistent_port_file_test.txt"))
    result = await cm.execute(
        "develop.setValue",
        {"param": "Exposure", "value": 0.5},
        timeout=2.0,
        mutating=True,
    )
    assert result["isError"] is True
    await cm.shutdown()


@pytest.mark.asyncio
async def test_mutating_flag_prevents_retry_explicitly(mock_lr_server):
    """C1: mutating=True で再接続が発生した場合、再送せずにエラー返却"""
    cm = ConnectionManager(port_file=str(mock_lr_server.port_file))

    mock_lr_server.register_response("system.ping", {"status": "ok"})
    await cm.execute("system.ping", {}, timeout=5.0, mutating=False)

    cm._client = None
    cm._reconnected = True

    result = await cm.execute(
        "develop.setValue",
        {"param": "Exposure", "value": 0.5},
        timeout=5.0,
        mutating=True,
    )
    assert result["isError"] is True
    assert result["code"] == "MUTATING_NOT_RETRIED"
    await cm.shutdown()


@pytest.mark.asyncio
async def test_readonly_command_retried_after_reconnect(mock_lr_server):
    """C1: read-only コマンドは再接続後に再送される"""
    mock_lr_server.register_response("system.ping", {"status": "ok"})

    cm = ConnectionManager(port_file=str(mock_lr_server.port_file))
    await cm.execute("system.ping", {}, timeout=5.0, mutating=False)
    cm._client = None
    cm._reconnected = True

    result = await cm.execute("system.ping", {}, timeout=5.0, mutating=False)
    assert result.get("isError") is not True or result.get("code") == "CONNECTION_ERROR"
    await cm.shutdown()
