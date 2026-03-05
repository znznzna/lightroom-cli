"""lr mcp サブコマンドのテスト。"""

import json
from unittest.mock import patch

from click.testing import CliRunner

from cli.main import cli


class TestMcpInstall:
    def test_install_creates_config_entry(self, tmp_path):
        """lr mcp install が設定ファイルにエントリを追加する"""
        config_file = tmp_path / "claude_desktop_config.json"
        config_file.write_text("{}")

        with patch("cli.commands.mcp._get_claude_config_path", return_value=config_file):
            with patch("cli.commands.mcp._check_fastmcp_installed", return_value=True):
                runner = CliRunner()
                result = runner.invoke(cli, ["mcp", "install"])
                assert result.exit_code == 0

                config = json.loads(config_file.read_text())
                assert "mcpServers" in config
                assert "lightroom-cli" in config["mcpServers"]
                assert config["mcpServers"]["lightroom-cli"]["command"] == "lr-mcp"

    def test_install_preserves_existing_servers(self, tmp_path):
        """既存の mcpServers エントリを保持する"""
        config_file = tmp_path / "claude_desktop_config.json"
        config_file.write_text(json.dumps({"mcpServers": {"other-server": {"command": "other"}}}))

        with patch("cli.commands.mcp._get_claude_config_path", return_value=config_file):
            with patch("cli.commands.mcp._check_fastmcp_installed", return_value=True):
                runner = CliRunner()
                result = runner.invoke(cli, ["mcp", "install"])
                assert result.exit_code == 0

                config = json.loads(config_file.read_text())
                assert "other-server" in config["mcpServers"]
                assert "lightroom-cli" in config["mcpServers"]

    def test_install_creates_config_file_if_missing(self, tmp_path):
        """設定ファイルが存在しない場合は新規作成"""
        config_file = tmp_path / "claude_desktop_config.json"

        with patch("cli.commands.mcp._get_claude_config_path", return_value=config_file):
            with patch("cli.commands.mcp._check_fastmcp_installed", return_value=True):
                runner = CliRunner()
                result = runner.invoke(cli, ["mcp", "install"])
                assert result.exit_code == 0
                assert config_file.exists()

    def test_install_checks_fastmcp_availability(self):
        """fastmcp がない場合はエラー"""
        with patch("cli.commands.mcp._check_fastmcp_installed", return_value=False):
            runner = CliRunner()
            result = runner.invoke(cli, ["mcp", "install"])
            assert result.exit_code != 0

    def test_install_warns_on_existing_entry_without_force(self, tmp_path):
        """I4: 既存エントリがある場合は --force なしで警告して上書きしない"""
        config_file = tmp_path / "claude_desktop_config.json"
        original_entry = {"command": "old-lr-mcp", "args": ["--old"]}
        config_file.write_text(json.dumps({"mcpServers": {"lightroom-cli": original_entry}}))

        with patch("cli.commands.mcp._get_claude_config_path", return_value=config_file):
            with patch("cli.commands.mcp._check_fastmcp_installed", return_value=True):
                runner = CliRunner()
                result = runner.invoke(cli, ["mcp", "install"])
                assert result.exit_code == 0
                assert "already installed" in result.output.lower()

                config = json.loads(config_file.read_text())
                assert config["mcpServers"]["lightroom-cli"]["command"] == "old-lr-mcp"

    def test_install_overwrites_with_force(self, tmp_path):
        """I4: --force フラグで既存エントリを上書き"""
        config_file = tmp_path / "claude_desktop_config.json"
        config_file.write_text(json.dumps({"mcpServers": {"lightroom-cli": {"command": "old-lr-mcp"}}}))

        with patch("cli.commands.mcp._get_claude_config_path", return_value=config_file):
            with patch("cli.commands.mcp._check_fastmcp_installed", return_value=True):
                runner = CliRunner()
                result = runner.invoke(cli, ["mcp", "install", "--force"])
                assert result.exit_code == 0

                config = json.loads(config_file.read_text())
                assert config["mcpServers"]["lightroom-cli"]["command"] == "lr-mcp"


class TestMcpUninstall:
    def test_uninstall_removes_entry(self, tmp_path):
        """lr mcp uninstall がエントリを削除する"""
        config_file = tmp_path / "claude_desktop_config.json"
        config_file.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "lightroom-cli": {"command": "lr-mcp"},
                        "other": {"command": "other"},
                    }
                }
            )
        )

        with patch("cli.commands.mcp._get_claude_config_path", return_value=config_file):
            runner = CliRunner()
            result = runner.invoke(cli, ["mcp", "uninstall"])
            assert result.exit_code == 0

            config = json.loads(config_file.read_text())
            assert "lightroom-cli" not in config["mcpServers"]
            assert "other" in config["mcpServers"]

    def test_uninstall_when_not_installed(self, tmp_path):
        """インストールされていない場合は正常終了"""
        config_file = tmp_path / "claude_desktop_config.json"
        config_file.write_text("{}")

        with patch("cli.commands.mcp._get_claude_config_path", return_value=config_file):
            runner = CliRunner()
            result = runner.invoke(cli, ["mcp", "uninstall"])
            assert result.exit_code == 0


class TestMcpStatus:
    def test_status_installed(self, tmp_path):
        """インストール済みの場合"""
        config_file = tmp_path / "claude_desktop_config.json"
        config_file.write_text(json.dumps({"mcpServers": {"lightroom-cli": {"command": "lr-mcp"}}}))

        with patch("cli.commands.mcp._get_claude_config_path", return_value=config_file):
            runner = CliRunner()
            result = runner.invoke(cli, ["mcp", "status"])
            assert result.exit_code == 0
            assert "installed" in result.output.lower() or "Installed" in result.output

    def test_status_not_installed(self, tmp_path):
        """未インストールの場合"""
        config_file = tmp_path / "claude_desktop_config.json"
        config_file.write_text("{}")

        with patch("cli.commands.mcp._get_claude_config_path", return_value=config_file):
            runner = CliRunner()
            result = runner.invoke(cli, ["mcp", "status"])
            assert result.exit_code == 0
            assert "not installed" in result.output.lower() or "Not" in result.output


class TestMcpTest:
    def test_mcp_test_sends_ping(self):
        """I1: lr mcp test が実際に Lightroom に接続して ping を送信する"""
        from unittest.mock import AsyncMock

        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.ping = AsyncMock(return_value={"status": "ok"})

        with (
            patch("cli.commands.mcp._check_fastmcp_installed", return_value=True),
            patch("cli.commands.mcp._create_test_client", return_value=mock_client),
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["mcp", "test"])
            assert result.exit_code == 0, f"output: {result.output}"
            assert "ping" in result.output.lower() or "ok" in result.output.lower()
            mock_client.connect.assert_called_once()
            mock_client.ping.assert_called_once()

    def test_mcp_test_fails_without_lightroom(self):
        """I1: Lightroom が起動していない場合にエラー"""
        with (
            patch("cli.commands.mcp._check_fastmcp_installed", return_value=True),
            patch("cli.commands.mcp._get_port_file_for_test", return_value="/tmp/nonexistent_test.txt"),
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["mcp", "test"])
            assert result.exit_code != 0
