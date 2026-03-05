from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.helpers.get_bridge")
def test_develop_reset_crop(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1",
        "success": True,
        "result": {"message": "Crop reset"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "reset-crop"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.resetCrop", {}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_reset_transforms(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "2",
        "success": True,
        "result": {"message": "Transforms reset"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "reset-transforms"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.resetTransforms", {}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_reset_spot(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "3",
        "success": True,
        "result": {"message": "Spot removal reset"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "reset-spot"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.resetSpotRemoval", {}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_reset_redeye(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "4",
        "success": True,
        "result": {"message": "Red eye reset"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "reset-redeye"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.resetRedeye", {}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_reset_healing(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "5",
        "success": True,
        "result": {"message": "Healing reset"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "reset-healing"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.resetHealing", {}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_edit_in_photoshop(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "6",
        "success": True,
        "result": {"message": "Opened in Photoshop"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "edit-in-photoshop"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.editInPhotoshop", {}, timeout=30.0)
