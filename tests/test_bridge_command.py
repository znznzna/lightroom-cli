import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from click.testing import CliRunner
import click


# bridge_command のインポートテスト
def test_bridge_command_import():
    """bridge_command デコレータがインポートできる"""
    from cli.helpers import bridge_command
    assert callable(bridge_command)


def test_bridge_command_creates_click_command():
    """bridge_command が正しいClickコマンドを生成する"""
    from cli.helpers import bridge_command

    @click.group()
    @click.pass_context
    def test_group(ctx):
        ctx.ensure_object(dict)
        ctx.obj["output"] = "text"
        ctx.obj["timeout"] = 30.0

    @test_group.command("test-cmd")
    @click.argument("name")
    @bridge_command("test.command")
    def test_cmd(name):
        return {"name": name}

    runner = CliRunner()
    with patch("cli.helpers.get_bridge") as mock_get_bridge:
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {
            "id": "1", "success": True, "result": {"ok": True}
        }
        mock_get_bridge.return_value = mock_bridge

        result = runner.invoke(test_group, ["test-cmd", "hello"])
        assert result.exit_code == 0
        mock_bridge.send_command.assert_called_once_with(
            "test.command", {"name": "hello"}, timeout=30.0
        )
