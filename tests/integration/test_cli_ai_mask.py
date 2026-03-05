# tests/integration/test_cli_ai_mask.py
import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.helpers.get_bridge")
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


@patch("cli.helpers.get_bridge")
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


@patch("cli.helpers.get_bridge")
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


@patch("cli.helpers.get_bridge")
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


@patch("cli.helpers.get_bridge")
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


@patch("cli.helpers.get_bridge")
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


@patch("cli.helpers.get_bridge")
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


@patch("cli.helpers.get_bridge")
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


@patch("cli.helpers.get_bridge")
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


@patch("cli.helpers.get_bridge")
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


@patch("cli.helpers.get_bridge")
def test_ai_reset_calls_reset_masking(mock_get_bridge, runner):
    """lr develop ai reset が develop.resetMasking を呼ぶ"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"message": "All masks reset"},
    }
    mock_get_bridge.return_value = mock_bridge
    # Without --confirm, should fail with exit code 2
    result_no_confirm = runner.invoke(cli, ["develop", "ai", "reset"])
    assert result_no_confirm.exit_code == 2
    assert "CONFIRMATION_REQUIRED" in result_no_confirm.output or "--confirm" in result_no_confirm.output

    # With --confirm, should succeed
    result = runner.invoke(cli, ["develop", "ai", "reset", "--confirm"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.resetMasking", {}, timeout=30.0,
    )


@patch("cli.helpers.get_bridge")
def test_ai_batch_all_selected(mock_get_bridge, runner):
    """lr develop ai batch sky --all-selected"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"total": 3, "succeeded": 3, "failed": 0, "results": []},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "batch", "sky", "--all-selected"])
    assert result.exit_code == 0
    call_args = mock_bridge.send_command.call_args
    assert call_args[0][0] == "develop.batchAIMask"
    assert call_args[0][1]["selectionType"] == "sky"
    assert call_args[0][1]["allSelected"] is True


@patch("cli.helpers.get_bridge")
def test_ai_batch_with_photos(mock_get_bridge, runner):
    """lr develop ai batch subject --photos 1,2,3"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"total": 3, "succeeded": 3, "failed": 0, "results": []},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "batch", "subject", "--photos", "1,2,3"])
    assert result.exit_code == 0
    call_args = mock_bridge.send_command.call_args
    assert call_args[0][1]["photoIds"] == ["1", "2", "3"]


@patch("cli.helpers.get_bridge")
def test_ai_batch_with_adjust_preset(mock_get_bridge, runner):
    """lr develop ai batch sky --all-selected --adjust-preset darken-sky"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"total": 2, "succeeded": 2, "failed": 0, "results": []},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, [
        "develop", "ai", "batch", "sky",
        "--all-selected", "--adjust-preset", "darken-sky",
    ])
    assert result.exit_code == 0
    call_args = mock_bridge.send_command.call_args
    assert call_args[0][1]["adjustments"] == {"Exposure": -0.7, "Highlights": -30, "Saturation": 15}


@patch("cli.helpers.get_bridge")
def test_ai_batch_dry_run(mock_get_bridge, runner):
    """lr develop ai batch sky --all-selected --dry-run は実行せず対象を表示"""
    mock_bridge = AsyncMock()
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "batch", "sky", "--all-selected", "--dry-run"])
    assert result.exit_code == 0
    assert "dry-run" in result.output.lower() or "Dry run" in result.output
    mock_bridge.send_command.assert_not_called()


def test_ai_batch_no_target(runner):
    """--photos も --all-selected もない場合エラー"""
    result = runner.invoke(cli, ["develop", "ai", "batch", "sky"])
    assert result.exit_code == 0
    assert "Specify --photos or --all-selected" in result.output


@patch("cli.helpers.get_bridge")
def test_deprecated_mask_list_shows_warning(mock_get_bridge, runner):
    """lr develop mask list が deprecated 警告を出す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"masks": []},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "mask", "list"])
    assert result.exit_code == 0
    assert "deprecated" in result.output.lower() or "lr develop ai list" in result.output


@patch("cli.helpers.get_bridge")
def test_deprecated_reset_masking_shows_warning(mock_get_bridge, runner):
    """lr develop reset-masking が deprecated 警告を出す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"message": "Reset"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "reset-masking"])
    assert result.exit_code == 0
    assert "deprecated" in result.output.lower() or "lr develop ai reset" in result.output
