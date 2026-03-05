"""StructuredErrorGroup -- Click 標準エラーの構造化テスト"""
import json
from click.testing import CliRunner
from cli.main import cli


class TestStructuredErrors:
    def test_no_such_command_json(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["-o", "json", "nonexistent"])
        assert result.exit_code == 2
        data = json.loads(result.output.strip())
        assert "error" in data
        assert data["error"]["code"] == "USAGE_ERROR"

    def test_missing_argument_json(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["-o", "json", "catalog", "get-info"])
        assert result.exit_code == 2
        data = json.loads(result.output.strip())
        assert "error" in data
        assert data["error"]["code"] == "USAGE_ERROR"

    def test_text_mode_unchanged(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["-o", "text", "nonexistent"])
        assert result.exit_code == 2
        # Click standard error format (not JSON)
        assert "no such command" in result.output.lower() or "error" in result.output.lower()

    def test_help_flag_not_affected(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

    def test_version_flag_not_affected(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.3.0" in result.output

    def test_no_such_subcommand_json(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["-o", "json", "develop", "nonexistent"])
        assert result.exit_code == 2
        data = json.loads(result.output.strip())
        assert "error" in data
        assert data["error"]["code"] == "USAGE_ERROR"
