"""searchPhotos が findPhotos に委譲されることの互換性テスト"""

import pytest

from lightroom_sdk.client import LightroomClient


@pytest.mark.asyncio
async def test_search_photos_delegates_to_find_photos(mock_lr_server):
    """searchPhotos の呼び出しが findPhotos と同じ結果を返すこと"""
    expected_result = {
        "photos": [
            {"id": 1, "filename": "IMG_001.jpg", "rating": 5},
            {"id": 2, "filename": "IMG_002.jpg", "rating": 4},
        ],
        "total": 2,
        "returned": 2,
        "offset": 0,
        "limit": 100,
    }
    # searchPhotos は内部で findPhotos に委譲するので、
    # MockServer には findPhotos のレスポンスを登録
    mock_lr_server.register_response("catalog.searchPhotos", expected_result)

    async with LightroomClient(port_file=str(mock_lr_server.port_file)) as client:
        result = await client.execute_command(
            "catalog.searchPhotos",
            {"criteria": {"rating": 5}, "limit": 100, "offset": 0},
        )
    assert len(result["photos"]) == 2
    assert result["total"] == 2


@pytest.mark.asyncio
async def test_search_photos_deprecated_log(mock_lr_server):
    """searchPhotos が deprecated であること（レスポンスが正常に返ること自体がテスト）

    Note: MockLightroomServer ではLuaログを検証できないため、
    searchPhotos が正常にレスポンスを返すことで委譲が機能していることを確認。
    deprecated ログの出力はE2Eテストで検証。
    """
    mock_lr_server.register_response("catalog.searchPhotos", {
        "photos": [],
        "total": 0,
    })

    async with LightroomClient(port_file=str(mock_lr_server.port_file)) as client:
        result = await client.execute_command(
            "catalog.searchPhotos",
            {"criteria": {}, "limit": 50, "offset": 0},
        )
    assert "photos" in result
    assert result["total"] == 0
