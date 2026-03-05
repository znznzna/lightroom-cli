"""Tests for risk_level field in dry-run output."""

import json

from click.testing import CliRunner

from cli.main import cli


class TestDryRunRiskLevel:
    def setup_method(self):
        self.runner = CliRunner()

    def test_write_command_dry_run_has_risk_level(self):
        result = self.runner.invoke(cli, ["-o", "json", "develop", "set", "Exposure", "0.5", "--dry-run"])
        data = json.loads(result.output)
        assert data["dry_run"] is True
        assert data["risk_level"] == "write"

    def test_destructive_command_dry_run_has_risk_level(self):
        result = self.runner.invoke(cli, ["-o", "json", "catalog", "remove-from-catalog", "123", "--dry-run"])
        data = json.loads(result.output)
        assert data["dry_run"] is True
        assert data["risk_level"] == "destructive"

    def test_catalog_set_rating_dry_run_risk_level(self):
        result = self.runner.invoke(cli, ["-o", "json", "catalog", "set-rating", "123", "5", "--dry-run"])
        data = json.loads(result.output)
        assert data["risk_level"] == "write"
