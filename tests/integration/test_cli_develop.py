import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.commands.develop.get_bridge")
def test_develop_get_settings(mock_get_bridge, runner):
    """lr develop get-settings が現在の設定を返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"Exposure": 0.5, "Contrast": 25},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "get-settings"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.getSettings", {}, timeout=30.0
    )


@patch("cli.commands.develop.get_bridge")
def test_develop_set_single_param(mock_get_bridge, runner):
    """lr develop set Exposure 1.5 が単一パラメータを設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "2", "success": True, "result": {"Exposure": 1.5},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "set", "Exposure", "1.5"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.setValue", {"parameter": "Exposure", "value": 1.5}, timeout=30.0
    )


@patch("cli.commands.develop.get_bridge")
def test_develop_set_multiple_params(mock_get_bridge, runner):
    """lr develop set Exposure 1.5 Contrast 25 が複数パラメータを一括設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "3", "success": True, "result": {},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "set", "Exposure", "1.5", "Contrast", "25"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.batchApplySettings",
        {"settings": {"Exposure": 1.5, "Contrast": 25.0}},
        timeout=30.0,
    )


@patch("cli.commands.develop.get_bridge")
def test_develop_auto_tone(mock_get_bridge, runner):
    """lr develop auto-tone がautoToneを実行する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "4", "success": True, "result": {"applied": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "auto-tone"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.setAutoTone", {}, timeout=30.0
    )
