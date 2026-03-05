"""Tests for CLI command execution helper."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestExecuteCommand:
    """execute_command() のテスト"""

    def test_successful_command(self):
        from cli.helpers import execute_command

        mock_ctx = MagicMock()
        mock_ctx.obj = {"output": "json", "timeout": 30.0, "fields": None}

        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {"result": {"status": "ok"}}

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "system.ping", {})

        mock_bridge.send_command.assert_called_once_with(
            "system.ping", {}, timeout=30.0
        )

    def test_fields_filtering_applied(self):
        from cli.helpers import execute_command

        mock_ctx = MagicMock()
        mock_ctx.obj = {"output": "json", "timeout": 30.0, "fields": ["status"]}

        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {
            "result": {"status": "ok", "extra": "data"}
        }

        with patch("cli.helpers.get_bridge", return_value=mock_bridge), \
             patch("click.echo") as mock_echo:
            execute_command(mock_ctx, "system.ping", {})

        # Verify output contains only filtered fields
        import json
        output = mock_echo.call_args[0][0]
        parsed = json.loads(output)
        assert parsed == {"status": "ok"}
        assert "extra" not in parsed

    def test_connection_error_exit_code_3(self):
        from cli.helpers import execute_command

        mock_ctx = MagicMock()
        mock_ctx.obj = {"output": "json", "timeout": 30.0, "fields": None}

        mock_bridge = AsyncMock()
        mock_bridge.send_command.side_effect = ConnectionError("refused")

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "system.ping", {})

        mock_ctx.exit.assert_called_with(3)

    def test_timeout_error_exit_code_4(self):
        from cli.helpers import execute_command

        mock_ctx = MagicMock()
        mock_ctx.obj = {"output": "json", "timeout": 30.0, "fields": None}

        mock_bridge = AsyncMock()
        mock_bridge.send_command.side_effect = TimeoutError("timed out")

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "system.ping", {})

        mock_ctx.exit.assert_called_with(4)

    def test_general_error_exit_code_1(self):
        from cli.helpers import execute_command

        mock_ctx = MagicMock()
        mock_ctx.obj = {"output": "json", "timeout": 30.0, "fields": None}

        mock_bridge = AsyncMock()
        mock_bridge.send_command.side_effect = RuntimeError("unexpected")

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "system.ping", {})

        mock_ctx.exit.assert_called_with(1)

    def test_custom_timeout_overrides_ctx(self):
        from cli.helpers import execute_command

        mock_ctx = MagicMock()
        mock_ctx.obj = {"output": "json", "timeout": 30.0, "fields": None}

        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {"result": {}}

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "preview.generatePreview", {}, timeout=120.0)

        mock_bridge.send_command.assert_called_once_with(
            "preview.generatePreview", {}, timeout=120.0
        )

    def test_zero_timeout_not_treated_as_falsy(self):
        from cli.helpers import execute_command

        mock_ctx = MagicMock()
        mock_ctx.obj = {"output": "json", "timeout": 30.0, "fields": None}

        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {"result": {}}

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "system.ping", {}, timeout=0.0)

        mock_bridge.send_command.assert_called_once_with(
            "system.ping", {}, timeout=0.0
        )
