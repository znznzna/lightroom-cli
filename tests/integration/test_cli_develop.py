from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.helpers.get_bridge")
def test_develop_get_settings(mock_get_bridge, runner):
    """lr develop get-settings が現在の設定を返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1",
        "success": True,
        "result": {"Exposure": 0.5, "Contrast": 25},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "get-settings", "photo-123"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.getSettings", {"photoId": "photo-123"}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_set_single_param(mock_get_bridge, runner):
    """lr develop set Exposure 1.5 が単一パラメータを設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "2",
        "success": True,
        "result": {"Exposure": 1.5},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "set", "Exposure", "1.5"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.setValue", {"param": "Exposure", "value": 1.5}, timeout=30.0
    )


@patch("cli.helpers.get_bridge")
def test_develop_set_multiple_params(mock_get_bridge, runner):
    """lr develop set Exposure 1.5 Contrast 25 が個別にsetValueを呼ぶ"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "3",
        "success": True,
        "result": {},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "set", "Exposure", "1.5", "Contrast", "25"])
    assert result.exit_code == 0
    assert mock_bridge.send_command.call_count == 2
    calls = mock_bridge.send_command.call_args_list
    assert calls[0].args == ("develop.setValue", {"param": "Exposure", "value": 1.5})
    assert calls[1].args == ("develop.setValue", {"param": "Contrast", "value": 25.0})


@patch("cli.helpers.get_bridge")
def test_develop_auto_tone(mock_get_bridge, runner):
    """lr develop auto-tone がautoToneを実行する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "4",
        "success": True,
        "result": {"applied": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "auto-tone"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.setAutoTone", {}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_get_value(mock_get_bridge, runner):
    """lr develop get Exposure が単一パラメータ値を取得する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "5",
        "success": True,
        "result": {"parameter": "Exposure", "value": 0.5},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "get", "Exposure"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.getValue", {"param": "Exposure"}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_apply(mock_get_bridge, runner):
    """lr develop apply がJSON設定を適用する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "6",
        "success": True,
        "result": {"applied": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "apply", "--settings", '{"Exposure": 1.0}'])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.applySettings", {"settings": {"Exposure": 1.0}}, timeout=30.0
    )


@patch("cli.helpers.get_bridge")
def test_develop_auto_wb(mock_get_bridge, runner):
    """lr develop auto-wb がオートホワイトバランスを適用する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "7",
        "success": True,
        "result": {"applied": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "auto-wb"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.setAutoWhiteBalance", {}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_tool(mock_get_bridge, runner):
    """lr develop tool crop がツールを選択する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "8",
        "success": True,
        "result": {"tool": "crop"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "tool", "crop"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.selectTool", {"tool": "crop"}, timeout=30.0)


def test_develop_apply_invalid_json(runner):
    """lr develop apply --settings '{bad}' が非ゼロ終了する"""
    result = runner.invoke(cli, ["develop", "apply", "--settings", "{bad json}"])
    assert result.exit_code != 0
    assert "Invalid JSON" in result.output


@patch("cli.helpers.get_bridge")
def test_develop_preset(mock_get_bridge, runner):
    """lr develop preset がプリセット適用コマンドを送信する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "9",
        "success": True,
        "result": {"preset": "Adobe Color", "applied": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "preset", "Adobe Color"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.applyDevelopPreset", {"presetName": "Adobe Color"}, timeout=30.0
    )


@patch("cli.helpers.get_bridge")
def test_develop_snapshot(mock_get_bridge, runner):
    """lr develop snapshot がスナップショット作成コマンドを送信する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "10",
        "success": True,
        "result": {"name": "Before grading", "created": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "snapshot", "Before grading"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.createDevelopSnapshot", {"name": "Before grading"}, timeout=30.0
    )


@patch("cli.helpers.get_bridge")
def test_develop_copy_settings(mock_get_bridge, runner):
    """lr develop copy-settings が設定コピーコマンドを送信する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "11",
        "success": True,
        "result": {"copied": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "copy-settings"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("catalog.copySettings", {}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_paste_settings(mock_get_bridge, runner):
    """lr develop paste-settings が設定ペーストコマンドを送信する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "12",
        "success": True,
        "result": {"pasted": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "paste-settings"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("catalog.pasteSettings", {}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_range(mock_get_bridge, runner):
    """lr develop range Exposure がパラメータ範囲を返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "13",
        "success": True,
        "result": {"param": "Exposure", "min": -5.0, "max": 5.0},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "range", "Exposure"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.getRange", {"param": "Exposure"}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_reset_param(mock_get_bridge, runner):
    """lr develop reset-param Exposure がパラメータをデフォルトにリセットする"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "14",
        "success": True,
        "result": {"param": "Exposure", "reset": True, "newValue": 0.0},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "reset-param", "Exposure"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.resetToDefault", {"param": "Exposure"}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_process_version(mock_get_bridge, runner):
    """lr develop process-version がプロセスバージョンを返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "15",
        "success": True,
        "result": {"processVersion": "Version 5"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "process-version"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.getProcessVersion", {}, timeout=30.0)


@patch("cli.helpers.get_bridge")
def test_develop_set_process_version(mock_get_bridge, runner):
    """lr develop set-process-version がプロセスバージョンを設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "16",
        "success": True,
        "result": {"processVersion": "Version 6", "applied": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "set-process-version", "Version 6"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.setProcessVersion", {"version": "Version 6"}, timeout=30.0
    )


class TestParsePairsErrorHandling:
    """_parse_pairs() のエラーハンドリングテスト"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_invalid_numeric_value_shows_structured_error(self, runner):
        """lr develop set Exposure abc が構造化エラーを返す（traceback なし）"""
        result = runner.invoke(cli, ["-o", "json", "develop", "set", "Exposure", "abc"])
        assert result.exit_code == 2
        assert "Traceback" not in result.output
        error_output = result.output if result.output else ""
        stderr_output = result.stderr if hasattr(result, "stderr") else ""
        combined = error_output + stderr_output
        assert "VALIDATION_ERROR" in combined or "Invalid numeric value" in combined

    def test_odd_number_of_args_shows_error(self, runner):
        """lr develop set Exposure が構造化エラーを返す"""
        result = runner.invoke(cli, ["-o", "json", "develop", "set", "Exposure"])
        assert result.exit_code == 2
        assert "Traceback" not in result.output

    def test_special_chars_in_value_show_error(self, runner):
        """特殊文字が値の場合のエラーハンドリング"""
        result = runner.invoke(cli, ["-o", "json", "develop", "set", "Exposure", "!@#"])
        assert result.exit_code == 2
        assert "Traceback" not in result.output


class TestJsonInput:
    """--json 入力テスト"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @patch("cli.helpers.get_bridge")
    def test_develop_get_settings_via_json(self, mock_get_bridge, runner):
        """get-settings でも --json オプションが存在する"""
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {
            "id": "1",
            "success": True,
            "result": {},
        }
        mock_get_bridge.return_value = mock_bridge
        result = runner.invoke(cli, ["develop", "get-settings", "photo-1", "--json", '{"photoId": "photo-1"}'])
        assert result.exit_code == 0

    @patch("cli.helpers.get_bridge")
    def test_empty_json_shows_error(self, mock_get_bridge, runner):
        """空の --json がエラーになる"""
        mock_bridge = AsyncMock()
        mock_get_bridge.return_value = mock_bridge
        result = runner.invoke(cli, ["develop", "get-settings", "photo-1", "--json", "  "])
        assert result.exit_code == 2


@patch("cli.helpers.get_bridge")
def test_cli_develop_batch_set(mock_get_bridge, runner):
    """lr develop batch-set --photo-ids 1,2,3 Exposure 0.5 の CLI テスト"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "batch-1",
        "success": True,
        "result": {
            "processed": 3,
            "succeeded": 3,
            "results": [
                {"photoId": 1, "success": True},
                {"photoId": 2, "success": True},
                {"photoId": 3, "success": True},
            ],
        },
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "batch-set", "--photo-ids", "1,2,3", "Exposure", "0.5"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.batchSetValue",
        {"photoIds": [1, 2, 3], "param": "Exposure", "value": 0.5},
        timeout=30.0,  # 3 photos → max(30, 10+2*3) = 30
    )


def test_cli_develop_batch_set_exceeds_limit(runner):
    """51枚指定時のバリデーションエラー"""
    ids = ",".join(str(i) for i in range(1, 52))
    result = runner.invoke(cli, ["develop", "batch-set", "--photo-ids", ids, "Exposure", "0.5"])
    assert result.exit_code != 0
