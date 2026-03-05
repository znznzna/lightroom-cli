import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.commands.develop.get_bridge")
def test_develop_local_create_mask(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "3", "success": True, "result": {"maskId": "m3"}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "local", "create-mask", "--tool", "gradient", "--settings", '{"Exposure": 0.5}'])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.createMaskWithLocalAdjustments",
        {"maskType": "gradient", "localSettings": {"Exposure": 0.5}},
        timeout=30.0
    )


@patch("cli.commands.develop.get_bridge")
def test_develop_local_create_mask_default(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "4", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "local", "create-mask"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.createMaskWithLocalAdjustments", {}, timeout=30.0
    )
