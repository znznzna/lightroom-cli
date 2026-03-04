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


@patch("cli.commands.develop.get_bridge")
def test_develop_get_value(mock_get_bridge, runner):
    """lr develop get Exposure が単一パラメータ値を取得する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "5", "success": True,
        "result": {"parameter": "Exposure", "value": 0.5},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "get", "Exposure"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.getValue", {"param": "Exposure"}, timeout=30.0
    )


@patch("cli.commands.develop.get_bridge")
def test_develop_apply(mock_get_bridge, runner):
    """lr develop apply がJSON設定を適用する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "6", "success": True,
        "result": {"applied": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "apply", "--settings", '{"Exposure": 1.0}'])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.applySettings", {"settings": {"Exposure": 1.0}}, timeout=30.0
    )


@patch("cli.commands.develop.get_bridge")
def test_develop_auto_wb(mock_get_bridge, runner):
    """lr develop auto-wb がオートホワイトバランスを適用する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "7", "success": True,
        "result": {"applied": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "auto-wb"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.setAutoWhiteBalance", {}, timeout=30.0
    )


@patch("cli.commands.develop.get_bridge")
def test_develop_tool(mock_get_bridge, runner):
    """lr develop tool crop がツールを選択する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "8", "success": True,
        "result": {"tool": "crop"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "tool", "crop"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.selectTool", {"tool": "crop"}, timeout=30.0
    )


def test_develop_apply_invalid_json(runner):
    """lr develop apply --settings '{bad}' が非ゼロ終了する"""
    result = runner.invoke(cli, ["develop", "apply", "--settings", "{bad json}"])
    assert result.exit_code != 0
    assert "Invalid JSON" in result.output


@patch("cli.commands.develop.get_bridge")
def test_develop_preset(mock_get_bridge, runner):
    """lr develop preset がプリセット適用コマンドを送信する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "9", "success": True,
        "result": {"preset": "Adobe Color", "applied": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "preset", "Adobe Color"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.applyDevelopPreset", {"presetName": "Adobe Color"}, timeout=30.0
    )


@patch("cli.commands.develop.get_bridge")
def test_develop_snapshot(mock_get_bridge, runner):
    """lr develop snapshot がスナップショット作成コマンドを送信する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "10", "success": True,
        "result": {"name": "Before grading", "created": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "snapshot", "Before grading"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.createDevelopSnapshot", {"name": "Before grading"}, timeout=30.0
    )


@patch("cli.commands.develop.get_bridge")
def test_develop_copy_settings(mock_get_bridge, runner):
    """lr develop copy-settings が設定コピーコマンドを送信する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "11", "success": True,
        "result": {"copied": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "copy-settings"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.copySettings", {}, timeout=30.0
    )


@patch("cli.commands.develop.get_bridge")
def test_develop_paste_settings(mock_get_bridge, runner):
    """lr develop paste-settings が設定ペーストコマンドを送信する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "12", "success": True,
        "result": {"pasted": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "paste-settings"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.pasteSettings", {}, timeout=30.0
    )


@patch("cli.commands.develop.get_bridge")
def test_develop_range(mock_get_bridge, runner):
    """lr develop range Exposure がパラメータ範囲を返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "13", "success": True,
        "result": {"param": "Exposure", "min": -5.0, "max": 5.0},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "range", "Exposure"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.getRange", {"param": "Exposure"}, timeout=30.0
    )


@patch("cli.commands.develop.get_bridge")
def test_develop_reset_param(mock_get_bridge, runner):
    """lr develop reset-param Exposure がパラメータをデフォルトにリセットする"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "14", "success": True,
        "result": {"param": "Exposure", "reset": True, "newValue": 0.0},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "reset-param", "Exposure"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.resetToDefault", {"param": "Exposure"}, timeout=30.0
    )


@patch("cli.commands.develop.get_bridge")
def test_develop_process_version(mock_get_bridge, runner):
    """lr develop process-version がプロセスバージョンを返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "15", "success": True,
        "result": {"processVersion": "Version 5"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "process-version"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.getProcessVersion", {}, timeout=30.0
    )


@patch("cli.commands.develop.get_bridge")
def test_develop_set_process_version(mock_get_bridge, runner):
    """lr develop set-process-version がプロセスバージョンを設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "16", "success": True,
        "result": {"processVersion": "Version 6", "applied": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "set-process-version", "Version 6"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.setProcessVersion", {"version": "Version 6"}, timeout=30.0
    )
