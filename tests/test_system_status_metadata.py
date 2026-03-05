"""Tests for schema_hash and cli_version in system status output."""

import json
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from cli.main import cli


class TestSystemStatusMetadata:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("cli.helpers.get_bridge")
    def test_status_includes_schema_hash(self, mock_get_bridge):
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {"result": {"status": "ok", "uptime": 100}}
        mock_get_bridge.return_value = mock_bridge

        result = self.runner.invoke(cli, ["-o", "json", "system", "status"])
        data = json.loads(result.output)
        assert "schema_hash" in data
        assert len(data["schema_hash"]) == 12

    @patch("cli.helpers.get_bridge")
    def test_status_includes_cli_version(self, mock_get_bridge):
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {"result": {"status": "ok"}}
        mock_get_bridge.return_value = mock_bridge

        result = self.runner.invoke(cli, ["-o", "json", "system", "status"])
        data = json.loads(result.output)
        assert "cli_version" in data

    @patch("cli.helpers.get_bridge")
    def test_status_preserves_bridge_response(self, mock_get_bridge):
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {"result": {"status": "ok", "uptime": 42, "version": "1.0"}}
        mock_get_bridge.return_value = mock_bridge

        result = self.runner.invoke(cli, ["-o", "json", "system", "status"])
        data = json.loads(result.output)
        assert data["status"] == "ok"
        assert data["uptime"] == 42
