"""バッチ現像処理のテスト (batchApplySettings, batchSetValue)"""

import pytest

from lightroom_sdk.client import LightroomClient
from lightroom_sdk.exceptions import LightroomSDKError


@pytest.mark.asyncio
async def test_batch_apply_settings_multiple_photos(mock_lr_server):
    """3枚の写真に設定を適用し、全枚の結果が返ること"""
    mock_lr_server.register_response(
        "develop.batchApplySettings",
        {
            "processed": 3,
            "succeeded": 3,
            "results": [
                {"photoId": 1, "success": True, "applied": 2},
                {"photoId": 2, "success": True, "applied": 2},
                {"photoId": 3, "success": True, "applied": 2},
            ],
        },
    )
    async with LightroomClient(port_file=str(mock_lr_server.port_file)) as client:
        result = await client.execute_command(
            "develop.batchApplySettings",
            {
                "photoIds": [1, 2, 3],
                "settings": {"Exposure": 0.5, "Contrast": 25},
            },
        )
    assert result["processed"] == 3
    assert result["succeeded"] == 3
    assert len(result["results"]) == 3
    assert all(r["success"] for r in result["results"])


@pytest.mark.asyncio
async def test_batch_apply_settings_partial_failure(mock_lr_server):
    """5枚中2枚が見つからない場合、3枚は成功し部分結果が返ること"""
    mock_lr_server.register_response(
        "develop.batchApplySettings",
        {
            "processed": 5,
            "succeeded": 3,
            "results": [
                {"photoId": 1, "success": True, "applied": 1},
                {"photoId": 2, "success": False, "error": "Photo not found"},
                {"photoId": 3, "success": True, "applied": 1},
                {"photoId": 4, "success": False, "error": "Photo not found"},
                {"photoId": 5, "success": True, "applied": 1},
            ],
        },
    )
    async with LightroomClient(port_file=str(mock_lr_server.port_file)) as client:
        result = await client.execute_command(
            "develop.batchApplySettings",
            {
                "photoIds": [1, 2, 3, 4, 5],
                "settings": {"Exposure": 0.5},
            },
        )
    assert result["processed"] == 5
    assert result["succeeded"] == 3
    failed = [r for r in result["results"] if not r["success"]]
    assert len(failed) == 2


@pytest.mark.asyncio
async def test_batch_apply_settings_max_50_limit(mock_lr_server):
    """51枚指定でエラーが返ること"""
    mock_lr_server.register_response(
        "develop.batchApplySettings",
        {"error": {"code": "BATCH_SIZE_EXCEEDED", "message": "Maximum batch size is 50 photos"}},
    )
    async with LightroomClient(port_file=str(mock_lr_server.port_file)) as client:
        with pytest.raises(LightroomSDKError) as exc_info:
            await client.execute_command(
                "develop.batchApplySettings",
                {
                    "photoIds": list(range(1, 52)),
                    "settings": {"Exposure": 0.5},
                },
            )
    assert exc_info.value.code == "BATCH_SIZE_EXCEEDED"


@pytest.mark.asyncio
async def test_batch_apply_settings_empty_photo_ids(mock_lr_server):
    """空の photoIds でエラー"""
    mock_lr_server.register_response(
        "develop.batchApplySettings",
        {"error": {"code": "MISSING_PHOTO_IDS", "message": "Photo IDs array is required"}},
    )
    async with LightroomClient(port_file=str(mock_lr_server.port_file)) as client:
        with pytest.raises(LightroomSDKError) as exc_info:
            await client.execute_command(
                "develop.batchApplySettings",
                {"photoIds": [], "settings": {"Exposure": 0.5}},
            )
    assert exc_info.value.code == "MISSING_PHOTO_IDS"


@pytest.mark.asyncio
async def test_batch_set_value_single_param(mock_lr_server):
    """develop.batchSetValue で1パラメータを複数写真に適用"""
    mock_lr_server.register_response(
        "develop.batchSetValue",
        {
            "processed": 3,
            "succeeded": 3,
            "results": [
                {"photoId": 1, "success": True},
                {"photoId": 2, "success": True},
                {"photoId": 3, "success": True},
            ],
        },
    )
    async with LightroomClient(port_file=str(mock_lr_server.port_file)) as client:
        result = await client.execute_command(
            "develop.batchSetValue",
            {"photoIds": [1, 2, 3], "param": "Exposure", "value": 0.5},
        )
    assert result["processed"] == 3
    assert result["succeeded"] == 3
    assert len(result["results"]) == 3


@pytest.mark.asyncio
async def test_batch_set_value_max_50_limit(mock_lr_server):
    """51枚で制限エラー"""
    mock_lr_server.register_response(
        "develop.batchSetValue",
        {"error": {"code": "BATCH_SIZE_EXCEEDED", "message": "Maximum batch size is 50 photos"}},
    )
    async with LightroomClient(port_file=str(mock_lr_server.port_file)) as client:
        with pytest.raises(LightroomSDKError) as exc_info:
            await client.execute_command(
                "develop.batchSetValue",
                {"photoIds": list(range(1, 52)), "param": "Exposure", "value": 0.5},
            )
    assert exc_info.value.code == "BATCH_SIZE_EXCEEDED"
