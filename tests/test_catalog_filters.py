"""findPhotos フィルタ拡張のテスト"""

import pytest

from lightroom_sdk.client import LightroomClient


@pytest.mark.asyncio
async def test_find_photos_with_folder_path_filter(mock_lr_server):
    """folderPath フィルタで部分一致する写真のみ返ること"""
    mock_lr_server.register_response(
        "catalog.findPhotos",
        {
            "photos": [
                {"id": 1, "filename": "IMG_001.jpg", "path": "/Photos/2024/IMG_001.jpg"},
            ],
            "total": 1,
        },
    )
    async with LightroomClient(port_file=str(mock_lr_server.port_file)) as client:
        result = await client.execute_command(
            "catalog.findPhotos",
            {"searchDesc": {"folderPath": "2024"}, "limit": 50, "offset": 0},
        )
    assert len(result["photos"]) == 1
    assert "2024" in result["photos"][0]["path"]


@pytest.mark.asyncio
async def test_find_photos_with_capture_date_from_filter(mock_lr_server):
    """captureDateFrom 以降の写真のみ返ること"""
    mock_lr_server.register_response(
        "catalog.findPhotos",
        {
            "photos": [
                {"id": 2, "filename": "IMG_002.jpg", "dateTimeOriginal": "2024-06-15T10:00:00"},
            ],
            "total": 1,
        },
    )
    async with LightroomClient(port_file=str(mock_lr_server.port_file)) as client:
        result = await client.execute_command(
            "catalog.findPhotos",
            {"searchDesc": {"captureDateFrom": "2024-06-01"}, "limit": 50, "offset": 0},
        )
    assert len(result["photos"]) == 1
    assert result["photos"][0]["dateTimeOriginal"] >= "2024-06-01"


@pytest.mark.asyncio
async def test_find_photos_with_capture_date_to_filter(mock_lr_server):
    """captureDateTo 以前の写真のみ返ること"""
    mock_lr_server.register_response(
        "catalog.findPhotos",
        {
            "photos": [
                {"id": 3, "filename": "IMG_003.jpg", "dateTimeOriginal": "2024-01-15T10:00:00"},
            ],
            "total": 1,
        },
    )
    async with LightroomClient(port_file=str(mock_lr_server.port_file)) as client:
        result = await client.execute_command(
            "catalog.findPhotos",
            {"searchDesc": {"captureDateTo": "2024-06-30"}, "limit": 50, "offset": 0},
        )
    assert len(result["photos"]) == 1
    assert result["photos"][0]["dateTimeOriginal"] <= "2024-06-30"


@pytest.mark.asyncio
async def test_find_photos_with_file_format_filter(mock_lr_server):
    """fileFormat の完全一致フィルタ"""
    mock_lr_server.register_response(
        "catalog.findPhotos",
        {
            "photos": [
                {"id": 4, "filename": "IMG_004.cr3", "fileFormat": "RAW"},
            ],
            "total": 1,
        },
    )
    async with LightroomClient(port_file=str(mock_lr_server.port_file)) as client:
        result = await client.execute_command(
            "catalog.findPhotos",
            {"searchDesc": {"fileFormat": "RAW"}, "limit": 50, "offset": 0},
        )
    assert len(result["photos"]) == 1
    assert result["photos"][0]["fileFormat"] == "RAW"


@pytest.mark.asyncio
async def test_find_photos_with_keyword_filter(mock_lr_server):
    """keyword の部分一致フィルタ"""
    mock_lr_server.register_response(
        "catalog.findPhotos",
        {
            "photos": [
                {"id": 5, "filename": "IMG_005.jpg", "keywords": ["landscape", "sunset"]},
            ],
            "total": 1,
        },
    )
    async with LightroomClient(port_file=str(mock_lr_server.port_file)) as client:
        result = await client.execute_command(
            "catalog.findPhotos",
            {"searchDesc": {"keyword": "land"}, "limit": 50, "offset": 0},
        )
    assert len(result["photos"]) == 1


@pytest.mark.asyncio
async def test_find_photos_with_filename_filter(mock_lr_server):
    """filename の部分一致フィルタ"""
    mock_lr_server.register_response(
        "catalog.findPhotos",
        {
            "photos": [
                {"id": 6, "filename": "IMG_006.jpg"},
            ],
            "total": 1,
        },
    )
    async with LightroomClient(port_file=str(mock_lr_server.port_file)) as client:
        result = await client.execute_command(
            "catalog.findPhotos",
            {"searchDesc": {"filename": "IMG_006"}, "limit": 50, "offset": 0},
        )
    assert len(result["photos"]) == 1
    assert "IMG_006" in result["photos"][0]["filename"]


@pytest.mark.asyncio
async def test_find_photos_with_combined_filters(mock_lr_server):
    """複合フィルタ（rating + flag + fileFormat）"""
    mock_lr_server.register_response(
        "catalog.findPhotos",
        {
            "photos": [
                {"id": 7, "filename": "IMG_007.cr3", "rating": 5, "flag": "pick", "fileFormat": "RAW"},
            ],
            "total": 1,
        },
    )
    async with LightroomClient(port_file=str(mock_lr_server.port_file)) as client:
        result = await client.execute_command(
            "catalog.findPhotos",
            {
                "searchDesc": {"rating": 5, "flag": "pick", "fileFormat": "RAW"},
                "limit": 50,
                "offset": 0,
            },
        )
    assert len(result["photos"]) == 1
    assert result["photos"][0]["rating"] == 5


@pytest.mark.asyncio
async def test_find_photos_with_unknown_filter_key(mock_lr_server):
    """不明なフィルタキーで warnings フィールドが返ること"""
    mock_lr_server.register_response(
        "catalog.findPhotos",
        {
            "photos": [],
            "total": 0,
            "warnings": ["Unknown filter key: unknownKey"],
        },
    )
    async with LightroomClient(port_file=str(mock_lr_server.port_file)) as client:
        result = await client.execute_command(
            "catalog.findPhotos",
            {"searchDesc": {"unknownKey": "value"}, "limit": 50, "offset": 0},
        )
    assert "warnings" in result
    assert any("unknownKey" in w for w in result["warnings"])


@pytest.mark.asyncio
async def test_find_photos_with_invalid_rating_value(mock_lr_server):
    """不正な rating 値でエラーレスポンス"""
    from lightroom_sdk.exceptions import LightroomSDKError

    mock_lr_server.register_response(
        "catalog.findPhotos",
        {"error": {"code": "INVALID_PARAM", "message": "rating must be a number"}},
    )
    async with LightroomClient(port_file=str(mock_lr_server.port_file)) as client:
        with pytest.raises(LightroomSDKError) as exc_info:
            await client.execute_command(
                "catalog.findPhotos",
                {"searchDesc": {"rating": "invalid"}, "limit": 50, "offset": 0},
            )
    assert exc_info.value.code == "INVALID_PARAM"
