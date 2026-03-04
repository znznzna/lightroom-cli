import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.commands.develop.get_bridge")
def test_develop_mask_list(mock_get_bridge, runner):
    """lr develop mask list が全マスク一覧を返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"masks": []},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "mask", "list"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.getAllMasks", {}, timeout=30.0
    )


@patch("cli.commands.develop.get_bridge")
def test_develop_mask_selected(mock_get_bridge, runner):
    """lr develop mask selected が選択中マスクを返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "2", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "mask", "selected"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.getSelectedMask", {}, timeout=30.0)


@patch("cli.commands.develop.get_bridge")
def test_develop_mask_create(mock_get_bridge, runner):
    """lr develop mask create が新規マスクを作成する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "3", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "mask", "create"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.createNewMask", {}, timeout=30.0)


@patch("cli.commands.develop.get_bridge")
def test_develop_mask_select(mock_get_bridge, runner):
    """lr develop mask select <index> がマスクを選択する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "4", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "mask", "select", "2"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.selectMask", {"index": 2}, timeout=30.0)


@patch("cli.commands.develop.get_bridge")
def test_develop_mask_delete(mock_get_bridge, runner):
    """lr develop mask delete <index> がマスクを削除する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "5", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "mask", "delete", "1"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.deleteMask", {"index": 1}, timeout=30.0)


@patch("cli.commands.develop.get_bridge")
def test_develop_mask_tool_info(mock_get_bridge, runner):
    """lr develop mask tool-info が選択中マスクツール情報を返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "6", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "mask", "tool-info"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.getSelectedMaskTool", {}, timeout=30.0)


@patch("cli.commands.develop.get_bridge")
def test_develop_mask_select_tool(mock_get_bridge, runner):
    """lr develop mask select-tool <index> がマスクツールを選択する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "7", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "mask", "select-tool", "0"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.selectMaskTool", {"index": 0}, timeout=30.0)


@patch("cli.commands.develop.get_bridge")
def test_develop_mask_delete_tool(mock_get_bridge, runner):
    """lr develop mask delete-tool <index> がマスクツールを削除する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "8", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "mask", "delete-tool", "0"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.deleteMaskTool", {"index": 0}, timeout=30.0)


@patch("cli.commands.develop.get_bridge")
def test_develop_mask_add(mock_get_bridge, runner):
    """lr develop mask add <tool> が現在のマスクにツールを追加する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "9", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "mask", "add", "brush"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.addToCurrentMask", {"tool": "brush"}, timeout=30.0)


@patch("cli.commands.develop.get_bridge")
def test_develop_mask_intersect(mock_get_bridge, runner):
    """lr develop mask intersect <tool> が現在のマスクとインターセクトする"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "10", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "mask", "intersect", "luminance"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.intersectWithCurrentMask", {"tool": "luminance"}, timeout=30.0)


@patch("cli.commands.develop.get_bridge")
def test_develop_mask_subtract(mock_get_bridge, runner):
    """lr develop mask subtract <tool> が現在のマスクからサブトラクトする"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "11", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "mask", "subtract", "color"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.subtractFromCurrentMask", {"tool": "color"}, timeout=30.0)


@patch("cli.commands.develop.get_bridge")
def test_develop_mask_invert(mock_get_bridge, runner):
    """lr develop mask invert がマスクを反転する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "12", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "mask", "invert"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.invertMask", {}, timeout=30.0)


@patch("cli.commands.develop.get_bridge")
def test_develop_mask_go_to(mock_get_bridge, runner):
    """lr develop mask go-to がマスキング画面に遷移する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "13", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "mask", "go-to"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.goToMasking", {}, timeout=30.0)


@patch("cli.commands.develop.get_bridge")
def test_develop_mask_toggle_overlay(mock_get_bridge, runner):
    """lr develop mask toggle-overlay がオーバーレイ表示を切り替える"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "14", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "mask", "toggle-overlay"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.toggleOverlay", {}, timeout=30.0)


@patch("cli.commands.develop.get_bridge")
def test_develop_mask_activate(mock_get_bridge, runner):
    """lr develop mask activate がマスキングモードを有効化する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "15", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "mask", "activate"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("develop.activateMaskingMode", {}, timeout=30.0)
