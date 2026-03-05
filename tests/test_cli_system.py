import pytest
from unittest.mock import AsyncMock, patch
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
        "id": "1", "success": True, "result": {"status": "ok", "timestamp": 123}
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
        "id": "1", "success": True,
        "result": {"connected": True, "version": "1.0"}
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["system", "status"])
    assert result.exit_code == 0


def test_system_check_connection_no_port_file(runner):
    """ポートファイルがない場合にエラーメッセージ表示"""
    result = runner.invoke(cli, ["system", "check-connection",
                                  "--port-file", "/tmp/nonexistent_test.txt"])
    assert result.exit_code == 0 or result.exit_code == 1
    assert "not" in result.output.lower() or "error" in result.output.lower() \
        or "unavailable" in result.output.lower()
