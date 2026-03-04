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


@patch("cli.commands.selection.get_bridge")
def test_selection_increase_rating(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "10", "success": True, "result": {"message": "Rating increased"}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["selection", "increase-rating"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("selection.increaseRating", {}, timeout=30.0)


@patch("cli.commands.selection.get_bridge")
def test_selection_decrease_rating(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "11", "success": True, "result": {"message": "Rating decreased"}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["selection", "decrease-rating"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("selection.decreaseRating", {}, timeout=30.0)


@patch("cli.commands.selection.get_bridge")
def test_selection_toggle_label_red(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "12", "success": True, "result": {"message": "Red label toggled"}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["selection", "toggle-label", "red"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("selection.toggleRedLabel", {}, timeout=30.0)


@patch("cli.commands.selection.get_bridge")
def test_selection_toggle_label_blue(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "13", "success": True, "result": {"message": "Blue label toggled"}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["selection", "toggle-label", "blue"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("selection.toggleBlueLabel", {}, timeout=30.0)


@patch("cli.commands.selection.get_bridge")
def test_selection_extend(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "14", "success": True, "result": {"message": "Selection extended"}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["selection", "extend", "--direction", "right", "--amount", "2"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("selection.extendSelection", {"direction": "right", "amount": 2}, timeout=30.0)


@patch("cli.commands.selection.get_bridge")
def test_selection_deselect_active(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "15", "success": True, "result": {"message": "Deselected"}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["selection", "deselect-active"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("selection.deselectActive", {}, timeout=30.0)


@patch("cli.commands.selection.get_bridge")
def test_selection_deselect_others(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "16", "success": True, "result": {"message": "Others deselected"}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["selection", "deselect-others"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("selection.deselectOthers", {}, timeout=30.0)
