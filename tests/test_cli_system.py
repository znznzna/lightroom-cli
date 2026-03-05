import json
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.helpers.get_bridge")
def test_system_ping(mock_get_bridge, runner):
    """lr system ping がpingコマンドを送信する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1",
        "success": True,
        "result": {"status": "ok", "timestamp": 123},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["system", "ping"])
    assert result.exit_code == 0
    assert "ok" in result.output


@patch("cli.helpers.get_bridge")
def test_system_status(mock_get_bridge, runner):
    """lr system status がstatusコマンドを送信する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1",
        "success": True,
        "result": {"connected": True, "version": "1.0"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["system", "status"])
    assert result.exit_code == 0


def test_system_check_connection_no_port_file(runner):
    """ポートファイルがない場合にエラーメッセージ表示"""
    result = runner.invoke(cli, ["system", "check-connection", "--port-file", "/tmp/nonexistent_test.txt"])
    assert result.exit_code == 3
    # エラー出力は stderr に出る
    output = result.output + (result.stderr if hasattr(result, "stderr") and result.stderr else "")
    assert "unavailable" in output.lower() or "not found" in output.lower() or "port file" in output.lower()


class TestExitCodes:
    """system コマンドの exit code テスト"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @patch("cli.commands.system.get_bridge")
    def test_reconnect_connection_error_exit_3(self, mock_get_bridge, runner):
        mock_bridge = AsyncMock()
        mock_bridge.connect.side_effect = ConnectionError("refused")
        mock_get_bridge.return_value = mock_bridge
        result = runner.invoke(cli, ["system", "reconnect"])
        assert result.exit_code == 3

    @patch("cli.commands.system.get_bridge")
    def test_reconnect_timeout_error_exit_4(self, mock_get_bridge, runner):
        mock_bridge = AsyncMock()
        mock_bridge.connect.side_effect = TimeoutError("timed out")
        mock_get_bridge.return_value = mock_bridge
        result = runner.invoke(cli, ["system", "reconnect"])
        assert result.exit_code == 4

    @patch("cli.commands.system.get_bridge")
    def test_reconnect_generic_error_exit_1(self, mock_get_bridge, runner):
        mock_bridge = AsyncMock()
        mock_bridge.connect.side_effect = RuntimeError("unknown")
        mock_get_bridge.return_value = mock_bridge
        result = runner.invoke(cli, ["system", "reconnect"])
        assert result.exit_code == 1

    @patch("cli.commands.system.get_bridge")
    def test_check_connection_ok_structured_output(self, mock_get_bridge, runner):
        """check-connection 成功時に構造化 JSON を返す"""
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {
            "id": "1",
            "success": True,
            "result": {"status": "ok"},
        }
        mock_get_bridge.return_value = mock_bridge
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("49000\n49001\n")
            port_file = f.name
        try:
            result = runner.invoke(
                cli,
                ["-o", "json", "system", "check-connection", "--port-file", port_file],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["status"] == "ok"
        finally:
            os.unlink(port_file)

    def test_check_connection_no_port_file_structured(self, runner):
        """ポートファイルがない場合に構造化出力 + exit 3"""
        result = runner.invoke(
            cli,
            [
                "-o",
                "json",
                "system",
                "check-connection",
                "--port-file",
                "/tmp/nonexistent_lr_test.txt",
            ],
        )
        assert result.exit_code == 3
