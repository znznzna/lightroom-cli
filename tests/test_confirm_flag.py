"""破壊的操作の --confirm フラグテスト"""

from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestRemoveFromCatalogConfirm:
    def test_without_confirm_fails(self, runner):
        """--confirm なしで exit_code=2"""
        result = runner.invoke(cli, ["-o", "json", "catalog", "remove-from-catalog", "123"])
        assert result.exit_code == 2
        assert "CONFIRMATION_REQUIRED" in result.output

    def test_without_confirm_has_suggestions(self, runner):
        """--confirm なしで suggestions が出る"""
        result = runner.invoke(cli, ["-o", "json", "catalog", "remove-from-catalog", "123"])
        assert "--confirm" in result.output

    @patch("cli.helpers.get_bridge")
    def test_with_confirm_succeeds(self, mock_get_bridge, runner):
        """--confirm 付きで実行される"""
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {
            "id": "1",
            "success": True,
            "result": {"status": "removed"},
        }
        mock_get_bridge.return_value = mock_bridge
        result = runner.invoke(cli, ["-o", "json", "catalog", "remove-from-catalog", "123", "--confirm"])
        assert result.exit_code == 0
        mock_bridge.send_command.assert_called_once()

    def test_dry_run_bypasses_confirm(self, runner):
        """--dry-run は --confirm なしでもプレビュー可能"""
        result = runner.invoke(cli, ["-o", "json", "catalog", "remove-from-catalog", "123", "--dry-run"])
        assert result.exit_code == 0
        assert "dry_run" in result.output


class TestAiResetConfirm:
    def test_without_confirm_fails(self, runner):
        """--confirm なしで exit_code=2"""
        result = runner.invoke(cli, ["-o", "json", "develop", "ai", "reset"])
        assert result.exit_code == 2
        assert "CONFIRMATION_REQUIRED" in result.output

    @patch("cli.helpers.get_bridge")
    def test_with_confirm_succeeds(self, mock_get_bridge, runner):
        """--confirm 付きで実行される"""
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {
            "id": "1",
            "success": True,
            "result": {"status": "reset"},
        }
        mock_get_bridge.return_value = mock_bridge
        result = runner.invoke(cli, ["-o", "json", "develop", "ai", "reset", "--confirm"])
        assert result.exit_code == 0
        mock_bridge.send_command.assert_called_once()

    def test_dry_run_bypasses_confirm(self, runner):
        """--dry-run は --confirm なしでもプレビュー可能"""
        result = runner.invoke(cli, ["-o", "json", "develop", "ai", "reset", "--dry-run"])
        assert result.exit_code == 0
        assert "dry_run" in result.output
