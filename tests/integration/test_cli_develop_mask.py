import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.commands.develop.get_bridge")
def test_develop_mask_list(mock_get_bridge, runner):
    """lr develop mask list が全マスク一覧を返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"masks": []},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "mask", "list"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.getAllMasks", {}, timeout=30.0
    )


@patch("cli.commands.develop.get_bridge")
def test_develop_mask_selected(mock_get_bridge, runner):
    """lr develop mask selected が選択中マスクを返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "2", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "mask", "selected"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.getSelectedMask", {}, timeout=30.0)


@patch("cli.commands.develop.get_bridge")
def test_develop_mask_go_to(mock_get_bridge, runner):
    """lr develop mask go-to がマスキング画面に遷移する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "13", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "mask", "go-to"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.goToMasking", {}, timeout=30.0)


@patch("cli.commands.develop.get_bridge")
def test_develop_mask_toggle_overlay(mock_get_bridge, runner):
    """lr develop mask toggle-overlay がオーバーレイ表示を切り替える"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "14", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "mask", "toggle-overlay"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.toggleOverlay", {}, timeout=30.0)
