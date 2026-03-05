"""Tests for lr schema CLI command."""
import json
import pytest
from click.testing import CliRunner
from cli.main import cli


class TestSchemaCommand:
    """lr schema コマンドのテスト"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_schema_list_groups(self, runner):
        result = runner.invoke(cli, ["-o", "json", "schema"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        group_names = [g["name"] for g in data]
        assert "develop" in group_names
        assert "catalog" in group_names

    def test_schema_group_commands(self, runner):
        result = runner.invoke(cli, ["-o", "json", "schema", "develop"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "command" in data[0]
        assert "description" in data[0]

    def test_schema_command_detail(self, runner):
        result = runner.invoke(cli, ["-o", "json", "schema", "develop.set"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "command" in data
        assert "params" in data
        assert isinstance(data["params"], list)

    def test_schema_unknown_group(self, runner):
        result = runner.invoke(cli, ["-o", "json", "schema", "nonexistent"])
        assert result.exit_code == 0
        assert "error" in result.output.lower() or "unknown" in result.output.lower()

    def test_schema_unknown_command(self, runner):
        result = runner.invoke(cli, ["-o", "json", "schema", "develop.nonexistent"])
        assert result.exit_code == 0
        assert "error" in result.output.lower() or "unknown" in result.output.lower()
