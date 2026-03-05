import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.helpers.get_bridge")
def test_catalog_get_selected(mock_get_bridge, runner):
    """lr catalog get-selected が選択中の写真を返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": [{"id": "photo-1", "filename": "IMG_001.jpg"}],
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "get-selected"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.getSelectedPhotos", {}, timeout=30.0
    )


@patch("cli.helpers.get_bridge")
def test_catalog_list_with_options(mock_get_bridge, runner):
    """lr catalog list --limit 10 --offset 5 がパラメータを渡す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "2", "success": True, "result": [],
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "list", "--limit", "10", "--offset", "5"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.getAllPhotos", {"limit": 10, "offset": 5}, timeout=60.0
    )


@patch("cli.helpers.get_bridge")
def test_catalog_set_rating(mock_get_bridge, runner):
    """lr catalog set-rating photo-1 5 がratingを設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "3", "success": True, "result": {"rating": 5},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "set-rating", "photo-1", "5"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.setRating", {"photoId": "photo-1", "rating": 5}, timeout=30.0
    )


@patch("cli.helpers.get_bridge")
def test_catalog_set_rating_sends_correct_command(mock_get_bridge, runner):
    """lr catalog set-rating がcatalog.setRatingコマンドを送信する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "10", "success": True,
        "result": {"photoId": "123", "rating": 4, "message": "Rating set successfully"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["catalog", "set-rating", "123", "4"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.setRating", {"photoId": "123", "rating": 4}, timeout=30.0
    )


@patch("cli.helpers.get_bridge")
def test_catalog_add_keywords_sends_correct_command(mock_get_bridge, runner):
    """lr catalog add-keywords がcatalog.addKeywordsコマンドを送信する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "11", "success": True,
        "result": {"photoId": "123", "addedKeywords": ["landscape", "sunset"], "count": 2},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["catalog", "add-keywords", "123", "landscape", "sunset"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.addKeywords", {"photoId": "123", "keywords": ["landscape", "sunset"]}, timeout=30.0,
    )
