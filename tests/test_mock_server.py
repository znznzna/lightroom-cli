import asyncio
import json
import pytest


@pytest.mark.asyncio
async def test_mock_server_responds_to_command(mock_lr_server):
    """MockServerがコマンドに応答できることを検証"""
    mock_lr_server.register_response("system.ping", {"status": "ok"})

    # ポートファイルからポート取得
    ports = mock_lr_server.port_file.read_text().strip().split(",")
    sender_port, receiver_port = int(ports[0]), int(ports[1])

    # receiver_portに接続してコマンド送信（LRのreceiver = Python側のsend先）
    _, writer = await asyncio.open_connection("localhost", receiver_port)
    reader, _ = await asyncio.open_connection("localhost", sender_port)

    request = {"id": "test-1", "command": "system.ping", "params": {}}
    writer.write(json.dumps(request).encode() + b"\n")
    await writer.drain()

    data = await asyncio.wait_for(reader.readline(), timeout=5.0)
    response = json.loads(data)

    assert response["id"] == "test-1"
    assert response["success"] is True
    assert response["result"]["status"] == "ok"
    writer.close()


@pytest.mark.asyncio
async def test_mock_server_sends_event(mock_lr_server):
    """MockServerがイベントをpushできることを検証"""
    ports = mock_lr_server.port_file.read_text().strip().split(",")
    sender_port = int(ports[0])

    reader, _ = await asyncio.open_connection("localhost", sender_port)
    await asyncio.sleep(0.1)  # サーバーがwriter登録するのを待つ

    await mock_lr_server.send_event("photo.selected", {"photoId": "abc"})

    data = await asyncio.wait_for(reader.readline(), timeout=5.0)
    event = json.loads(data)

    assert event["event"] == "photo.selected"
    assert event["data"]["photoId"] == "abc"
