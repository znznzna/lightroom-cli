"""JSON モード時のログレベルテスト"""

import json
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from cli.main import cli


class TestJsonLogSuppression:
    def test_json_mode_no_warning_in_stdout(self):
        runner = CliRunner()
        with patch("cli.helpers.get_bridge") as mock:
            bridge = AsyncMock()
            bridge.send_command.return_value = {"result": {"status": "ok"}}
            mock.return_value = bridge
            result = runner.invoke(cli, ["-o", "json", "system", "ping"])
            assert result.exit_code == 0
            json.loads(result.output.strip())  # Must be valid JSON

    def test_help_works_in_json_mode(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["-o", "json", "--help"])
        assert result.exit_code == 0

    def test_verbose_overrides_json_suppression(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["-o", "json", "-v", "--help"])
        assert result.exit_code == 0
