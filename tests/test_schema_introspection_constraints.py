"""Tests for cli_constraints in lr schema output."""
import json
from click.testing import CliRunner
from cli.main import cli


class TestSchemaIntrospectionConstraints:
    def setup_method(self):
        self.runner = CliRunner()

    def test_schema_detail_includes_supports_dry_run(self):
        result = self.runner.invoke(cli, ["-o", "json", "schema", "develop.set"])
        data = json.loads(result.output)
        assert "supports_dry_run" in data
        assert data["supports_dry_run"] is True

    def test_schema_detail_includes_requires_confirm(self):
        result = self.runner.invoke(cli, ["-o", "json", "schema", "catalog.remove-from-catalog"])
        data = json.loads(result.output)
        assert "requires_confirm" in data
        assert data["requires_confirm"] is True

    def test_schema_detail_includes_risk_level(self):
        result = self.runner.invoke(cli, ["-o", "json", "schema", "develop.get-settings"])
        data = json.loads(result.output)
        assert "risk_level" in data
        assert data["risk_level"] == "read"

    def test_write_risk_level(self):
        result = self.runner.invoke(cli, ["-o", "json", "schema", "develop.set"])
        data = json.loads(result.output)
        assert data["risk_level"] == "write"

    def test_destructive_risk_level(self):
        result = self.runner.invoke(cli, ["-o", "json", "schema", "catalog.remove-from-catalog"])
        data = json.loads(result.output)
        assert data["risk_level"] == "destructive"
