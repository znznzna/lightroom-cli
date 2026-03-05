"""Tests for CLI decorators."""
import json
import pytest
from click.testing import CliRunner
import click


class TestDryRunSupport:
    """@dry_run_support デコレータのテスト"""

    def test_dry_run_returns_preview(self):
        @click.group()
        @click.pass_context
        def test_group(ctx):
            ctx.ensure_object(dict)
            ctx.obj["output"] = "json"

        @test_group.command("test-cmd")
        @click.option("--dry-run", is_flag=True, default=False)
        @click.argument("param")
        @click.pass_context
        def test_cmd(ctx, dry_run, param):
            from cli.decorators import dry_run_guard
            preview = dry_run_guard(ctx, command="test.command", params={"param": param})
            if preview:
                return
            click.echo("executed")

        runner = CliRunner()
        result = runner.invoke(test_group, ["test-cmd", "--dry-run", "value"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["dry_run"] is True
        assert "executed" not in result.output

    def test_no_dry_run_executes_normally(self):
        @click.group()
        @click.pass_context
        def test_group(ctx):
            ctx.ensure_object(dict)
            ctx.obj["output"] = "text"

        @test_group.command("test-cmd")
        @click.option("--dry-run", is_flag=True, default=False)
        @click.argument("param")
        @click.pass_context
        def test_cmd(ctx, dry_run, param):
            from cli.decorators import dry_run_guard
            preview = dry_run_guard(ctx, command="test.command", params={"param": param})
            if preview:
                return
            click.echo("executed")

        runner = CliRunner()
        result = runner.invoke(test_group, ["test-cmd", "value"])
        assert "executed" in result.output


class TestJsonInput:
    """--json / --json-stdin 入力テスト"""

    def test_json_option_parses_dict(self):
        from cli.decorators import parse_json_input

        result = parse_json_input('{"parameter": "Exposure", "value": 0.5}', None)
        assert result == {"parameter": "Exposure", "value": 0.5}

    def test_json_option_invalid_json_raises(self):
        from cli.decorators import parse_json_input
        with pytest.raises(click.BadParameter, match="Invalid JSON"):
            parse_json_input("{invalid", None)

    def test_json_option_non_dict_raises(self):
        from cli.decorators import parse_json_input
        with pytest.raises(click.BadParameter, match="must be a JSON object"):
            parse_json_input("[1, 2, 3]", None)

    def test_json_stdin_reads_from_stdin(self):
        from cli.decorators import parse_json_input
        import io
        stdin = io.StringIO('{"key": "value"}')
        result = parse_json_input(None, stdin)
        assert result == {"key": "value"}

    def test_no_json_returns_none(self):
        from cli.decorators import parse_json_input
        result = parse_json_input(None, None)
        assert result is None

    def test_both_json_and_stdin_raises(self):
        from cli.decorators import parse_json_input
        import io
        with pytest.raises(click.BadParameter, match="Cannot use both"):
            parse_json_input('{"a": 1}', io.StringIO('{"b": 2}'))
