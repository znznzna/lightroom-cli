import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.commands.selection.get_bridge")
def test_selection_flag(mock_get_bridge, runner):
    """lr selection flag が選択写真にPickフラグを設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"message": "Flag set to pick"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["selection", "flag"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "selection.flagAsPick", {}, timeout=30.0
    )


@patch("cli.commands.selection.get_bridge")
def test_selection_reject(mock_get_bridge, runner):
    """lr selection reject が選択写真にRejectフラグを設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "2", "success": True,
        "result": {"message": "Flag set to reject"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["selection", "reject"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "selection.flagAsReject", {}, timeout=30.0
    )


@patch("cli.commands.selection.get_bridge")
def test_selection_unflag(mock_get_bridge, runner):
    """lr selection unflag がフラグを解除する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "3", "success": True,
        "result": {"message": "Flag removed"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["selection", "unflag"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "selection.removeFlag", {}, timeout=30.0
    )


@patch("cli.commands.selection.get_bridge")
def test_selection_next(mock_get_bridge, runner):
    """lr selection next が次の写真へ移動する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "4", "success": True,
        "result": {"message": "Moved to next photo"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["selection", "next"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "selection.nextPhoto", {}, timeout=30.0
    )


@patch("cli.commands.selection.get_bridge")
def test_selection_previous(mock_get_bridge, runner):
    """lr selection previous が前の写真へ移動する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "5", "success": True,
        "result": {"message": "Moved to previous photo"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["selection", "previous"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "selection.previousPhoto", {}, timeout=30.0
    )


@patch("cli.commands.selection.get_bridge")
def test_selection_color_label(mock_get_bridge, runner):
    """lr selection color-label red がカラーラベルを設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "6", "success": True,
        "result": {"message": "Color label set to red"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["selection", "color-label", "red"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "selection.setColorLabel", {"label": "red"}, timeout=30.0
    )


@patch("cli.commands.selection.get_bridge")
def test_selection_select_all(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "7", "success": True, "result": {"message": "All selected"}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["selection", "select-all"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("selection.selectAll", {}, timeout=30.0)


@patch("cli.commands.selection.get_bridge")
def test_selection_select_none(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "8", "success": True, "result": {"message": "None selected"}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["selection", "select-none"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("selection.selectNone", {}, timeout=30.0)


@patch("cli.commands.selection.get_bridge")
def test_selection_select_inverse(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "9", "success": True, "result": {"message": "Selection inverted"}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["selection", "select-inverse"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("selection.selectInverse", {}, timeout=30.0)
