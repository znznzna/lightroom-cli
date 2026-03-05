from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.helpers.get_bridge")
def test_develop_debug_dump(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1",
        "success": True,
        "result": {"functions": [], "properties": []},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "debug", "dump"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.dumpLrDevelopController", {}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_debug_gradient_params(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "2", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "debug", "gradient-params"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.discoverGradientParameters", {}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_debug_monitor(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "3", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "debug", "monitor", "--duration", "5"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.monitorParameterChanges", {"duration": 5}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_debug_probe(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "4", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "debug", "probe"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.probeAllDevelopParameters", {}, timeout=30.0)
