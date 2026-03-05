import asyncio

import pytest

from lightroom_sdk.socket_bridge import SocketBridge


@pytest.mark.asyncio
async def test_on_event_registers_and_fires(mock_lr_server):
    """on_event()で登録したハンドラがイベント受信時に呼ばれる"""
    received = []

    bridge = SocketBridge(port_file=str(mock_lr_server.port_file))
    bridge.on_event("photo.selected", lambda data: received.append(data))

    await bridge.connect(retry_attempts=1)
    await mock_lr_server.wait_for_client()

    # MockServerからイベント送信
    await mock_lr_server.send_event("photo.selected", {"photoId": "123"})
    await asyncio.sleep(0.3)

    assert len(received) == 1
    assert received[0]["photoId"] == "123"
    await bridge.disconnect()


@pytest.mark.asyncio
async def test_unregistered_event_ignored(mock_lr_server):
    """未登録イベントがエラーにならないことを検証"""
    bridge = SocketBridge(port_file=str(mock_lr_server.port_file))
    await bridge.connect(retry_attempts=1)
    await mock_lr_server.wait_for_client()

    await mock_lr_server.send_event("unknown.event", {})
    await asyncio.sleep(0.3)
    # エラーが発生しなければOK

    await bridge.disconnect()
