import asyncio
import pytest
from lightroom_sdk.resilient_bridge import ResilientSocketBridge, ConnectionState


@pytest.mark.asyncio
async def test_initial_state_is_disconnected():
    bridge = ResilientSocketBridge(port_file="/tmp/nonexistent.txt")
    assert bridge.state == ConnectionState.DISCONNECTED


@pytest.mark.asyncio
async def test_connect_transitions_to_connected(mock_lr_server):
    mock_lr_server.register_response("system.ping", {"status": "ok"})
    bridge = ResilientSocketBridge(
        port_file=str(mock_lr_server.port_file)
    )
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
