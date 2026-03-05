# tests/integration/test_cli_ai_mask.py
import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.commands.ai_mask.get_bridge")
def test_ai_subject_creates_mask(mock_get_bridge, runner):
    """lr develop ai subject が develop.createAIMaskWithAdjustments を呼ぶ"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {
            "maskType": "aiSelection",
            "selectionType": "subject",
            "message": "Created AI subject mask",
        },
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "subject"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.createAIMaskWithAdjustments",
        {"selectionType": "subject"},
        timeout=60.0,
    )


@patch("cli.commands.ai_mask.get_bridge")
def test_ai_sky_creates_mask(mock_get_bridge, runner):
    """lr develop ai sky が正しい selectionType で呼ばれる"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"selectionType": "sky", "message": "Created AI sky mask"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "sky"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.createAIMaskWithAdjustments",
        {"selectionType": "sky"},
        timeout=60.0,
    )


@patch("cli.commands.ai_mask.get_bridge")
def test_ai_background_creates_mask(mock_get_bridge, runner):
    """lr develop ai background"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"selectionType": "background"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "background"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.createAIMaskWithAdjustments",
        {"selectionType": "background"},
        timeout=60.0,
    )


@patch("cli.commands.ai_mask.get_bridge")
def test_ai_objects_creates_mask(mock_get_bridge, runner):
    """lr develop ai objects"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"selectionType": "objects"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "objects"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.createAIMaskWithAdjustments",
        {"selectionType": "objects"},
        timeout=60.0,
    )
