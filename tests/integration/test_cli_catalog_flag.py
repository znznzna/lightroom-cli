import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.commands.catalog.get_bridge")
def test_catalog_get_info_includes_pick_status(mock_get_bridge, runner):
    """lr catalog get-info がpickStatusを含むメタデータを返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1",
        "success": True,
        "result": {
            "id": 12345,
            "filename": "IMG_001.jpg",
            "rating": 3,
            "pickStatus": 1,
            "colorLabel": "red",
        },
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "get-info", "12345"])
    assert result.exit_code == 0
    assert "pickStatus" in result.output


@patch("cli.commands.catalog.get_bridge")
def test_catalog_set_flag_pick(mock_get_bridge, runner):
    """lr catalog set-flag <id> pick がフラグを設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "2",
        "success": True,
        "result": {"photoId": "12345", "flag": 1, "message": "Flag set successfully"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "set-flag", "12345", "pick"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.setFlag", {"photoId": "12345", "flag": 1}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_set_flag_reject(mock_get_bridge, runner):
    """lr catalog set-flag <id> reject がRejectフラグを設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "3",
        "success": True,
        "result": {"photoId": "12345", "flag": -1, "message": "Flag set successfully"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "set-flag", "12345", "reject"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.setFlag", {"photoId": "12345", "flag": -1}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_set_flag_none(mock_get_bridge, runner):
    """lr catalog set-flag <id> none がフラグを解除する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "4",
        "success": True,
        "result": {"photoId": "12345", "flag": 0, "message": "Flag set successfully"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "set-flag", "12345", "none"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.setFlag", {"photoId": "12345", "flag": 0}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_get_flag(mock_get_bridge, runner):
    """lr catalog get-flag <id> がフラグ状態を取得する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "5",
        "success": True,
        "result": {"photoId": "12345", "pickStatus": 1, "label": "pick"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "get-flag", "12345"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.getFlag", {"photoId": "12345"}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_find_with_flag_option(mock_get_bridge, runner):
    """lr catalog find --flag pick がフラグ条件検索を実行する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "6",
        "success": True,
        "result": {
            "photos": [{"id": 1, "filename": "IMG_001.jpg", "pickStatus": 1}],
            "total": 1,
            "returned": 1,
        },
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "find", "--flag", "pick"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once()
    call_args = mock_bridge.send_command.call_args
    assert call_args[0][0] == "catalog.findPhotos"
    assert call_args[0][1]["searchDesc"]["flag"] == "pick"


@patch("cli.commands.catalog.get_bridge")
def test_catalog_find_with_rating_option(mock_get_bridge, runner):
    """lr catalog find --rating 5 がレーティング条件検索を実行する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "7",
        "success": True,
        "result": {"photos": [], "total": 0, "returned": 0},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "find", "--rating", "5"])
    assert result.exit_code == 0
    call_args = mock_bridge.send_command.call_args
    assert call_args[0][1]["searchDesc"]["rating"] == 5


@patch("cli.commands.catalog.get_bridge")
def test_catalog_find_with_multiple_options(mock_get_bridge, runner):
    """lr catalog find --flag pick --rating 5 --color-label red が複合条件検索を実行する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "8",
        "success": True,
        "result": {"photos": [], "total": 0, "returned": 0},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(
        cli, ["catalog", "find", "--flag", "pick", "--rating", "5", "--color-label", "red"]
    )
    assert result.exit_code == 0
    call_args = mock_bridge.send_command.call_args
    search_desc = call_args[0][1]["searchDesc"]
    assert search_desc["flag"] == "pick"
    assert search_desc["rating"] == 5
    assert search_desc["colorLabel"] == "red"
