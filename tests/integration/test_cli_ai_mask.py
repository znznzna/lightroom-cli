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


@patch("cli.commands.ai_mask.get_bridge")
def test_ai_people_with_part(mock_get_bridge, runner):
    """lr develop ai people --part eyes がパラメータに part を含む"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"selectionType": "people", "part": "eyes"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "people", "--part", "eyes"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.createAIMaskWithAdjustments",
        {"selectionType": "people", "part": "eyes"},
        timeout=60.0,
    )


@patch("cli.commands.ai_mask.get_bridge")
def test_ai_people_without_part(mock_get_bridge, runner):
    """lr develop ai people (part なし) は part をパラメータに含まない"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"selectionType": "people"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "people"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.createAIMaskWithAdjustments",
        {"selectionType": "people"},
        timeout=60.0,
    )


@patch("cli.commands.ai_mask.get_bridge")
def test_ai_landscape_with_part(mock_get_bridge, runner):
    """lr develop ai landscape --part water"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"selectionType": "landscape", "part": "water"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "landscape", "--part", "water"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.createAIMaskWithAdjustments",
        {"selectionType": "landscape", "part": "water"},
        timeout=60.0,
    )


@patch("cli.commands.ai_mask.get_bridge")
def test_ai_sky_with_adjust_json(mock_get_bridge, runner):
    """lr develop ai sky --adjust '{"Exposure": -0.5}' が adjustments を含む"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"selectionType": "sky", "adjustments": {"Exposure": -0.5}},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "sky", "--adjust", '{"Exposure": -0.5}'])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.createAIMaskWithAdjustments",
        {"selectionType": "sky", "adjustments": {"Exposure": -0.5}},
        timeout=60.0,
    )


@patch("cli.commands.ai_mask.get_bridge")
def test_ai_subject_with_adjust_preset(mock_get_bridge, runner):
    """lr develop ai subject --adjust-preset brighten-subject がプリセットを展開する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"selectionType": "subject"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "subject", "--adjust-preset", "brighten-subject"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.createAIMaskWithAdjustments",
        {
            "selectionType": "subject",
            "adjustments": {"Exposure": 0.5, "Shadows": 20, "Clarity": 10},
        },
        timeout=60.0,
    )


def test_ai_adjust_invalid_json(runner):
    """--adjust に不正な JSON を渡すとエラーメッセージが出る"""
    result = runner.invoke(cli, ["develop", "ai", "sky", "--adjust", "not-json"])
    assert result.exit_code == 0
    assert "Invalid JSON" in result.output


def test_ai_adjust_unknown_preset(runner):
    """--adjust-preset に存在しないプリセット名でエラー"""
    result = runner.invoke(cli, ["develop", "ai", "sky", "--adjust-preset", "nonexistent"])
    assert result.exit_code == 0
    assert "Unknown preset" in result.output


def test_ai_adjust_and_preset_conflict(runner):
    """--adjust と --adjust-preset の同時指定でエラー"""
    result = runner.invoke(cli, [
        "develop", "ai", "sky",
        "--adjust", '{"Exposure": 1}',
        "--adjust-preset", "darken-sky",
    ])
    assert result.exit_code == 0
    assert "Cannot use both" in result.output


def test_ai_presets_lists_all(runner):
    """lr develop ai presets が全プリセット名を出力する"""
    result = runner.invoke(cli, ["develop", "ai", "presets"])
    assert result.exit_code == 0
    assert "darken-sky" in result.output
    assert "brighten-subject" in result.output
    assert "blur-background" in result.output
    assert "warm-skin" in result.output
    assert "enhance-landscape" in result.output


def test_ai_presets_json_format(runner):
    """lr develop ai presets -o json が JSON 形式で出力する"""
    result = runner.invoke(cli, ["-o", "json", "develop", "ai", "presets"])
    assert result.exit_code == 0
    import json
    data = json.loads(result.output)
    assert "darken-sky" in data


@patch("cli.commands.ai_mask.get_bridge")
def test_ai_list_calls_get_all_masks(mock_get_bridge, runner):
    """lr develop ai list が develop.getAllMasks を呼ぶ"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"masks": [{"type": "aiSelection", "subtype": "sky"}]},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "list"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.getAllMasks", {}, timeout=30.0,
    )


@patch("cli.commands.ai_mask.get_bridge")
def test_ai_reset_calls_reset_masking(mock_get_bridge, runner):
    """lr develop ai reset が develop.resetMasking を呼ぶ"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"message": "All masks reset"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "reset"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.resetMasking", {}, timeout=30.0,
    )
