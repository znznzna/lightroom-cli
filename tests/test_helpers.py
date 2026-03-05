"""Tests for CLI command execution helper."""

from unittest.mock import AsyncMock, MagicMock, patch


class TestExecuteCommand:
    """execute_command() のテスト"""

    def _make_ctx(self, **overrides):
        ctx = MagicMock()
        ctx.obj = {"output": "json", "timeout": 30.0, "fields": None}
        ctx.params = {}
        for k, v in overrides.items():
            if k == "obj":
                ctx.obj = v
            elif k == "params":
                ctx.params = v
            else:
                setattr(ctx, k, v)
        return ctx

    def test_successful_command(self):
        from cli.helpers import execute_command

        mock_ctx = self._make_ctx()
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {"result": {"status": "ok"}}

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "system.ping", {})

        mock_bridge.send_command.assert_called_once_with("system.ping", {}, timeout=30.0)

    def test_fields_filtering_applied(self):
        from cli.helpers import execute_command

        mock_ctx = self._make_ctx(obj={"output": "json", "timeout": 30.0, "fields": ["status"]})
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {"result": {"status": "ok", "extra": "data"}}

        with (
            patch("cli.helpers.get_bridge", return_value=mock_bridge),
            patch("click.echo") as mock_echo,
        ):
            execute_command(mock_ctx, "system.ping", {})

        import json

        output = mock_echo.call_args[0][0]
        parsed = json.loads(output)
        assert parsed == {"status": "ok"}
        assert "extra" not in parsed

    def test_connection_error_exit_code_3(self):
        from cli.helpers import execute_command

        mock_ctx = self._make_ctx()
        mock_bridge = AsyncMock()
        mock_bridge.send_command.side_effect = ConnectionError("refused")

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "system.ping", {})

        mock_ctx.exit.assert_called_with(3)

    def test_timeout_error_exit_code_4(self):
        from cli.helpers import execute_command

        mock_ctx = self._make_ctx()
        mock_bridge = AsyncMock()
        mock_bridge.send_command.side_effect = TimeoutError("timed out")

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "system.ping", {})

        mock_ctx.exit.assert_called_with(4)

    def test_general_error_exit_code_1(self):
        from cli.helpers import execute_command

        mock_ctx = self._make_ctx()
        mock_bridge = AsyncMock()
        mock_bridge.send_command.side_effect = RuntimeError("unexpected")

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "system.ping", {})

        mock_ctx.exit.assert_called_with(1)

    def test_custom_timeout_overrides_ctx(self):
        from cli.helpers import execute_command

        mock_ctx = self._make_ctx()
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {"result": {}}

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "preview.generatePreview", {}, timeout=120.0)

        mock_bridge.send_command.assert_called_once_with("preview.generatePreview", {}, timeout=120.0)

    def test_validation_error_exit_code_2(self):
        from cli.helpers import execute_command

        mock_ctx = self._make_ctx()

        with patch("cli.helpers.get_bridge") as mock_get:
            mock_bridge = AsyncMock()
            mock_get.return_value = mock_bridge
            execute_command(mock_ctx, "develop.setValue", {"Exposre": 0.5})

        mock_ctx.exit.assert_called_with(2)
        mock_bridge.send_command.assert_not_called()

    def test_valid_params_pass_to_bridge(self):
        from cli.helpers import execute_command

        mock_ctx = self._make_ctx()
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {"result": {"status": "ok"}}

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "develop.setValue", {"parameter": "Exposure", "value": 0.5})

        mock_bridge.send_command.assert_called_once()

    def test_dry_run_skips_execution(self):
        from cli.helpers import execute_command

        mock_ctx = self._make_ctx(params={"dry_run": True})
        mock_bridge = AsyncMock()

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "develop.setValue", {"parameter": "Exposure", "value": 0.5})

        mock_bridge.send_command.assert_not_called()

    def test_no_dry_run_executes(self):
        from cli.helpers import execute_command

        mock_ctx = self._make_ctx()
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {"result": {"ok": True}}

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "develop.setValue", {"parameter": "Exposure", "value": 0.5})

        mock_bridge.send_command.assert_called_once()

    def test_json_input_overrides_params(self):
        from cli.helpers import execute_command

        mock_ctx = self._make_ctx(params={"json_str": '{"parameter": "Contrast", "value": 50}'})
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {"result": {"ok": True}}

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "develop.setValue", {"parameter": "Exposure", "value": 0.5})

        call_args = mock_bridge.send_command.call_args
        assert call_args[0][1]["parameter"] == "Contrast"
        assert call_args[0][1]["value"] == 50

    def test_empty_json_string_rejected(self):
        from cli.helpers import execute_command

        mock_ctx = self._make_ctx(params={"json_str": ""})
        mock_bridge = AsyncMock()

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "system.ping", {})

        # Empty JSON should not execute the bridge command
        mock_bridge.send_command.assert_not_called()
        mock_ctx.exit.assert_called_with(2)

    def test_command_timeout_uses_max_of_global_and_command(self):
        from cli.helpers import execute_command

        mock_ctx = self._make_ctx(obj={"output": "json", "timeout": 120.0, "fields": None})
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {"result": {}}

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "system.ping", {}, timeout=60.0)

        # max(60.0, 120.0) = 120.0 — user's global timeout wins
        mock_bridge.send_command.assert_called_once_with("system.ping", {}, timeout=120.0)

    def test_sdk_connection_error_exit_code_3(self):
        """SDK ConnectionError もビルトインと同じく exit code 3"""
        from cli.helpers import execute_command
        from lightroom_sdk.exceptions import ConnectionError as SDKConnectionError

        mock_ctx = self._make_ctx()
        mock_bridge = AsyncMock()
        mock_bridge.send_command.side_effect = SDKConnectionError("refused")

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "system.ping", {})

        mock_ctx.exit.assert_called_with(3)

    def test_sdk_timeout_error_exit_code_4(self):
        """SDK TimeoutError もビルトインと同じく exit code 4"""
        from cli.helpers import execute_command
        from lightroom_sdk.exceptions import TimeoutError as SDKTimeoutError

        mock_ctx = self._make_ctx()
        mock_bridge = AsyncMock()
        mock_bridge.send_command.side_effect = SDKTimeoutError("timed out")

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "system.ping", {})

        mock_ctx.exit.assert_called_with(4)
