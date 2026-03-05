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
