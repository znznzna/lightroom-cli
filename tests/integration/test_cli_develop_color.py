from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.helpers.get_bridge")
def test_develop_color_green_swatch(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "1", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "color", "green-swatch"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.createGreenSwatch", {}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_color_cyan_swatch(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "2", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "color", "cyan-swatch"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.createCyanSwatch", {}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_color_enhance(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "3", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "color", "enhance", "--preset", "vivid"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.enhanceColors", {"preset": "vivid"}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_reset_gradient(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "4", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "reset-gradient"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.resetGradient", {}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_reset_circular(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "5", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "reset-circular"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.resetCircularGradient", {}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_reset_brush(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "6", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "reset-brush"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.resetBrushing", {}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_reset_masking(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "7", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "reset-masking"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.resetMasking", {}, timeout=30.0)
