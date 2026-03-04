import asyncio
import time
import pytest
from lightroom_sdk.client import LightroomClient
from lightroom_sdk.socket_bridge import SocketBridge


@pytest.mark.asyncio
async def test_execute_command_no_blocking_sleep(mock_lr_server):
    """time.sleep(0.1)が削除され、コマンド実行がブロックしないことを検証"""
    mock_lr_server.register_response("system.ping", {"status": "ok"})

    client = LightroomClient.__new__(LightroomClient)
    client._bridge = SocketBridge(port_file=str(mock_lr_server.port_file))
    await client._bridge.connect(retry_attempts=1)

    start = time.monotonic()
    for _ in range(10):
        await client.execute_command("system.ping")
    elapsed = time.monotonic() - start

    # 10回実行して1秒未満ならsleep(0.1)が除去されている
    assert elapsed < 1.0, f"10 commands took {elapsed:.2f}s (expected <1.0s without sleep)"
    await client.disconnect()


@pytest.mark.asyncio
async def test_ping_returns_result(mock_lr_server):
    """ping()がresultを返すことを検証"""
    mock_lr_server.register_response("system.ping", {"status": "ok"})

    client = LightroomClient.__new__(LightroomClient)
    client._bridge = SocketBridge(port_file=str(mock_lr_server.port_file))
    await client._bridge.connect(retry_attempts=1)

    result = await client.ping()
    assert result["status"] == "ok"
    await client.disconnect()
