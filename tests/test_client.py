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


@pytest.mark.asyncio
async def test_create_ai_mask_basic(mock_lr_server):
    """create_ai_mask が develop.createAIMaskWithAdjustments を正しいパラメータで送信する"""
    mock_lr_server.register_response(
        "develop.createAIMaskWithAdjustments",
        {
            "maskType": "aiSelection",
            "selectionType": "sky",
            "message": "Created AI sky mask",
        },
    )

    client = LightroomClient.__new__(LightroomClient)
    client._bridge = SocketBridge(port_file=str(mock_lr_server.port_file))
    await client._bridge.connect(retry_attempts=1)
    try:
        result = await client.create_ai_mask("sky")
        assert result["selectionType"] == "sky"
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_create_ai_mask_with_adjustments(mock_lr_server):
    """create_ai_mask に adjustments を渡すと params に含まれる"""
    mock_lr_server.register_response(
        "develop.createAIMaskWithAdjustments",
        {
            "maskType": "aiSelection",
            "selectionType": "subject",
            "adjustments": {"Exposure": 0.5},
        },
    )

    client = LightroomClient.__new__(LightroomClient)
    client._bridge = SocketBridge(port_file=str(mock_lr_server.port_file))
    await client._bridge.connect(retry_attempts=1)
    try:
        result = await client.create_ai_mask("subject", adjustments={"Exposure": 0.5})
        assert result["adjustments"] == {"Exposure": 0.5}
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_create_ai_mask_with_part(mock_lr_server):
    """create_ai_mask に part を渡すと params に含まれる"""
    mock_lr_server.register_response(
        "develop.createAIMaskWithAdjustments",
        {
            "maskType": "aiSelection",
            "selectionType": "people",
            "part": "eyes",
        },
    )

    client = LightroomClient.__new__(LightroomClient)
    client._bridge = SocketBridge(port_file=str(mock_lr_server.port_file))
    await client._bridge.connect(retry_attempts=1)
    try:
        result = await client.create_ai_mask("people", part="eyes")
        assert result["part"] == "eyes"
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_batch_ai_mask_with_photo_ids(mock_lr_server):
    """batch_ai_mask が photoIds 付きで送信される"""
    mock_lr_server.register_response(
        "develop.batchAIMask",
        {
            "total": 2,
            "succeeded": 2,
            "failed": 0,
            "results": [
                {"photoId": "1", "status": "success"},
                {"photoId": "2", "status": "success"},
            ],
        },
    )

    client = LightroomClient.__new__(LightroomClient)
    client._bridge = SocketBridge(port_file=str(mock_lr_server.port_file))
    await client._bridge.connect(retry_attempts=1)
    try:
        result = await client.batch_ai_mask("sky", photo_ids=["1", "2"])
        assert result["total"] == 2
        assert result["succeeded"] == 2
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_batch_ai_mask_all_selected(mock_lr_server):
    """batch_ai_mask --all-selected で allSelected=True が送信される"""
    mock_lr_server.register_response(
        "develop.batchAIMask",
        {
            "total": 3,
            "succeeded": 3,
            "failed": 0,
            "results": [],
        },
    )

    client = LightroomClient.__new__(LightroomClient)
    client._bridge = SocketBridge(port_file=str(mock_lr_server.port_file))
    await client._bridge.connect(retry_attempts=1)
    try:
        result = await client.batch_ai_mask("subject", all_selected=True)
        assert result["total"] == 3
    finally:
        await client.disconnect()
