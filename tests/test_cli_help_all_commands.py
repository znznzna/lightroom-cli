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

# Commands that run locally instead of going through execute_command, so they have no --json
NON_BRIDGE_COMMANDS = {
    "plugin install",
    "plugin uninstall",
    "plugin status",
    "schema",
    "develop ai presets",
    "system reconnect",
    "system check-connection",
}
BRIDGE_COMMANDS = [c for c in ALL_COMMANDS if c not in NON_BRIDGE_COMMANDS and not c.startswith("mcp ")]


@pytest.mark.parametrize("cmd_path", ALL_COMMANDS, ids=ALL_COMMANDS)
def test_help_succeeds(cmd_path):
    """各コマンドの --help が exit code 0 で動作する"""
    runner = CliRunner()
    args = cmd_path.split() + ["--help"]
    result = runner.invoke(cli, args)
    assert result.exit_code == 0, f"--help failed for '{cmd_path}': {result.output}"


@pytest.mark.parametrize("cmd_path", BRIDGE_COMMANDS, ids=BRIDGE_COMMANDS)
def test_help_contains_json_option(cmd_path):
    """execute_command を使う全コマンドに --json オプションが存在する"""
    runner = CliRunner()
    result = runner.invoke(cli, cmd_path.split() + ["--help"])
    assert "--json" in result.output, f"--json option missing for '{cmd_path}'"


def test_non_bridge_list_matches_real_commands():
    """The exclusion list must not hide a typo or a command that no longer exists"""
    assert NON_BRIDGE_COMMANDS <= set(ALL_COMMANDS)
    assert len(ALL_COMMANDS) - len(BRIDGE_COMMANDS) == len(NON_BRIDGE_COMMANDS) + sum(
        c.startswith("mcp ") for c in ALL_COMMANDS
    )
