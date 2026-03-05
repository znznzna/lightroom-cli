import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.helpers.get_bridge")
def test_develop_local_get(mock_get_bridge, runner):
    """lr develop local get <param> がローカル調整値を取得する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"parameter": "Exposure", "value": 0.5},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "local", "get", "Exposure"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.getLocalValue", {"parameter": "Exposure"}, timeout=30.0
    )


@patch("cli.helpers.get_bridge")
def test_develop_local_set(mock_get_bridge, runner):
    """lr develop local set <param> <value> がローカル調整値を設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "2", "success": True,
        "result": {"applied": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "local", "set", "Exposure", "0.5"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.setLocalValue", {"parameter": "Exposure", "value": 0.5}, timeout=30.0
    )


@patch("cli.helpers.get_bridge")
def test_develop_local_apply(mock_get_bridge, runner):
    """lr develop local apply --settings '{...}' が複数のローカル調整を適用する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "3", "success": True,
        "result": {"applied": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "local", "apply", "--settings", '{"Exposure": 0.5, "Contrast": 25}'])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.applyLocalSettings", {"settings": {"Exposure": 0.5, "Contrast": 25}}, timeout=30.0
    )


@patch("cli.helpers.get_bridge")
def test_develop_local_params(mock_get_bridge, runner):
    """lr develop local params が利用可能なローカルパラメータ一覧を返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "4", "success": True,
        "result": {"parameters": ["Exposure", "Contrast", "Saturation"]},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "local", "params"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.getAvailableLocalParameters", {}, timeout=30.0
    )
