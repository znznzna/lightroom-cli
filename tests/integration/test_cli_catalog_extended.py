import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.commands.catalog.get_bridge")
def test_catalog_select(mock_get_bridge, runner):
    """lr catalog select がphotoIdでの写真選択を実行する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"selected": 2},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "select", "123", "456"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.setSelectedPhotos", {"photoIds": ["123", "456"]}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_find_by_path(mock_get_bridge, runner):
    """lr catalog find-by-path がパスで写真を検索する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "2", "success": True,
        "result": {"id": 123, "filename": "IMG_001.jpg"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "find-by-path", "/photos/IMG_001.jpg"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.findPhotoByPath", {"path": "/photos/IMG_001.jpg"}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_collections(mock_get_bridge, runner):
    """lr catalog collections がコレクション一覧を返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "3", "success": True,
        "result": {"collections": [], "count": 0},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "collections"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.getCollections", {}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_keywords(mock_get_bridge, runner):
    """lr catalog keywords がキーワード一覧を返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "4", "success": True,
        "result": {"keywords": [], "count": 0},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "keywords"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.getKeywords", {}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_folders(mock_get_bridge, runner):
    """lr catalog folders がフォルダ一覧を返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "5", "success": True,
        "result": {"folders": [], "count": 0},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "folders"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.getFolders", {"includeSubfolders": False}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_folders_recursive(mock_get_bridge, runner):
    """lr catalog folders --recursive がサブフォルダ付きで返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "6", "success": True,
        "result": {"folders": [], "count": 0, "includeSubfolders": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "folders", "--recursive"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.getFolders", {"includeSubfolders": True}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_set_title(mock_get_bridge, runner):
    """lr catalog set-title 123 'Sunset' がcatalog.setTitleに正しいパラメータを送信する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "7", "success": True,
        "result": {"photoId": "123", "title": "Sunset", "message": "Title set successfully"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "set-title", "123", "Sunset"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.setTitle", {"photoId": "123", "title": "Sunset"}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_set_caption(mock_get_bridge, runner):
    """lr catalog set-caption 123 'A beautiful sunset' がcatalog.setCaptionに正しいパラメータを送信する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "8", "success": True,
        "result": {"photoId": "123", "caption": "A beautiful sunset", "message": "Caption set successfully"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "set-caption", "123", "A beautiful sunset"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.setCaption", {"photoId": "123", "caption": "A beautiful sunset"}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_set_color_label(mock_get_bridge, runner):
    """lr catalog set-color-label 123 red がcatalog.setColorLabelに正しいパラメータを送信する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "9", "success": True,
        "result": {"photoId": "123", "label": "red", "message": "Color label set successfully"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "set-color-label", "123", "red"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.setColorLabel", {"photoId": "123", "label": "red"}, timeout=30.0
    )
