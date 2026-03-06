"""全コマンドの --help が正常動作することを検証するパラメトリックテスト"""

import pytest
from click.testing import CliRunner

from cli.main import cli


def _collect_commands(group, prefix=""):
    """Click グループから全コマンドパスを再帰的に収集"""
    commands = []
    for name in group.list_commands(None):
        cmd = group.get_command(None, name)
        full = f"{prefix} {name}".strip() if prefix else name
        if hasattr(cmd, "list_commands"):
            commands.extend(_collect_commands(cmd, full))
        else:
            commands.append(full)
    return commands


ALL_COMMANDS = _collect_commands(cli)


@pytest.mark.parametrize("cmd_path", ALL_COMMANDS, ids=ALL_COMMANDS)
def test_help_succeeds(cmd_path):
    """各コマンドの --help が exit code 0 で動作する"""
    runner = CliRunner()
    args = cmd_path.split() + ["--help"]
    result = runner.invoke(cli, args)
    assert result.exit_code == 0, f"--help failed for '{cmd_path}': {result.output}"


@pytest.mark.parametrize("cmd_path", ALL_COMMANDS, ids=ALL_COMMANDS)
def test_help_contains_json_option(cmd_path):
    """execute_command を使う全コマンドに --json オプションが存在する"""
    runner = CliRunner()
    args = cmd_path.split() + ["--help"]
    result = runner.invoke(cli, args)
    # plugin, schema, mcp コマンドは execute_command を使わないので除外
    if cmd_path.startswith("plugin") or cmd_path.startswith("mcp") or cmd_path == "schema":
        pytest.skip("Non-bridge command")
    # グループ help（サブコマンド持ち）も除外
    if "Commands:" in result.output:
        pytest.skip("Group command")
    # ai presets は execute_command を使わないので除外
    if cmd_path == "develop ai presets":
        pytest.skip("Non-bridge command (uses OutputFormatter directly)")
    # reconnect, check-connection は execute_command を使わない独自実装
    if cmd_path in ("system reconnect", "system check-connection"):
        pytest.skip("Non-bridge command (custom implementation)")
    assert "--json" in result.output, f"--json option missing for '{cmd_path}'"
