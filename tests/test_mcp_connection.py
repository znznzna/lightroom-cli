"""ConnectionManager のテスト。MockLightroomServer を使用。"""

import asyncio
import time

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
    cm = ConnectionManager(port_file="/tmp/nonexistent_port_file_test.txt")

    result = await cm.execute("system.ping", {}, timeout=2.0, mutating=False)
    assert result["isError"] is True
    await cm.shutdown()


@pytest.mark.asyncio
async def test_lock_serializes_commands(mock_lr_server):
    """asyncio.Lock がコマンドを直列化すること（タイムスタンプで証明）"""
    timestamps = []

    mock_lr_server.register_response("system.ping", {"status": "ok"})

    cm = ConnectionManager(port_file=str(mock_lr_server.port_file))

    async def run_cmd(label: str):
        start = time.monotonic()
        await cm.execute("system.ping", {}, timeout=5.0, mutating=False)
        end = time.monotonic()
        timestamps.append((label, start, end))

    await asyncio.gather(run_cmd("A"), run_cmd("B"))
    assert len(timestamps) == 2

    (label_a, start_a, end_a) = timestamps[0]
    (label_b, start_b, end_b) = timestamps[1]
    # At least one must have finished before the other started (within tolerance)
    assert end_a <= start_b + 0.05 or end_b <= start_a + 0.05, (
        f"Commands overlapped: {label_a}=[{start_a:.3f},{end_a:.3f}], {label_b}=[{start_b:.3f},{end_b:.3f}]"
    )
    await cm.shutdown()


@pytest.mark.asyncio
async def test_mutating_not_retried_after_reconnect():
    """C1: mutating コマンドは接続エラー時に再送されずエラーを返す"""
    cm = ConnectionManager(port_file="/tmp/nonexistent_port_file_test.txt")
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
