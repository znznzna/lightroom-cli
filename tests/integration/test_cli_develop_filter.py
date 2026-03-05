import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.helpers.get_bridge")
def test_develop_filter_graduated(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "1", "success": True, "result": {"maskId": "m1", "maskType": "gradient"}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "filter", "graduated"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.createGraduatedFilter", {}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_filter_radial(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "2", "success": True, "result": {"maskId": "m2", "maskType": "radialGradient"}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "filter", "radial"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.createRadialFilter", {}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_filter_brush(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "3", "success": True, "result": {"maskId": "m3", "maskType": "brush"}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "filter", "brush"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.createAdjustmentBrush", {}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_filter_range(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "5", "success": True, "result": {"maskId": "m5"}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "filter", "range", "--type", "color"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.createRangeMask", {"rangeType": "color"}, timeout=30.0)
