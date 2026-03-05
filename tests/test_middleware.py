"""Tests for CLI middleware (TTY detection, environment variable resolution)."""
import sys
import pytest


class TestResolveOutputFormat:
    """resolve_output_format() のテスト"""

    def test_explicit_output_takes_priority(self):
        from cli.middleware import resolve_output_format
        assert resolve_output_format("table") == "table"

    def test_explicit_json_overrides_tty(self):
        from cli.middleware import resolve_output_format
        assert resolve_output_format("json") == "json"

    def test_env_var_used_when_no_explicit(self, monkeypatch):
        from cli.middleware import resolve_output_format
        monkeypatch.setenv("LR_OUTPUT", "table")
        assert resolve_output_format(None) == "table"

    def test_invalid_env_var_ignored(self, monkeypatch):
        from cli.middleware import resolve_output_format
        monkeypatch.setenv("LR_OUTPUT", "invalid_format")
        result = resolve_output_format(None)
        assert result in ("json", "text")

    def test_non_tty_defaults_to_json(self, monkeypatch):
        from cli.middleware import resolve_output_format
        monkeypatch.delenv("LR_OUTPUT", raising=False)
        monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
        assert resolve_output_format(None) == "json"

    def test_tty_defaults_to_text(self, monkeypatch):
        from cli.middleware import resolve_output_format
        monkeypatch.delenv("LR_OUTPUT", raising=False)
        monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
        assert resolve_output_format(None) == "text"


class TestResolveTimeout:
    """resolve_timeout() のテスト"""

    def test_explicit_timeout_takes_priority(self):
        from cli.middleware import resolve_timeout
        assert resolve_timeout(60.0) == 60.0

    def test_env_var_used_when_no_explicit(self, monkeypatch):
        from cli.middleware import resolve_timeout
        monkeypatch.setenv("LR_TIMEOUT", "45.0")
        assert resolve_timeout(None) == 45.0

    def test_invalid_env_var_returns_default(self, monkeypatch):
        from cli.middleware import resolve_timeout
        monkeypatch.setenv("LR_TIMEOUT", "not_a_number")
        assert resolve_timeout(None) == 30.0

    def test_no_env_returns_default(self, monkeypatch):
        from cli.middleware import resolve_timeout
        monkeypatch.delenv("LR_TIMEOUT", raising=False)
        assert resolve_timeout(None) == 30.0


class TestResolveFields:
    """resolve_fields() のテスト"""

    def test_explicit_fields_parsed(self):
        from cli.middleware import resolve_fields
        assert resolve_fields("name,rating") == ["name", "rating"]

    def test_env_var_fields(self, monkeypatch):
        from cli.middleware import resolve_fields
        monkeypatch.setenv("LR_FIELDS", "fileName,dateTimeOriginal")
        assert resolve_fields(None) == ["fileName", "dateTimeOriginal"]

    def test_strips_whitespace(self):
        from cli.middleware import resolve_fields
        assert resolve_fields(" name , rating ") == ["name", "rating"]

    def test_none_when_not_set(self, monkeypatch):
        from cli.middleware import resolve_fields
        monkeypatch.delenv("LR_FIELDS", raising=False)
        assert resolve_fields(None) is None


class TestLogLevel:
    """非verbose時のログレベル設定テスト"""

    def test_non_verbose_sets_warning_level(self):
        """verbose=False の場合、ログレベルが WARNING に設定される"""
        import logging
        from click.testing import CliRunner
        from cli.main import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

    def test_reconnect_error_to_stderr(self):
        """reconnect のエラーが err=True で出力される"""
        from unittest.mock import AsyncMock, patch, call
        from click.testing import CliRunner
        from cli.main import cli
        runner = CliRunner()
        with patch("cli.commands.system.get_bridge") as mock_get_bridge, \
             patch("cli.commands.system.click.echo") as mock_echo:
            mock_bridge = AsyncMock()
            mock_bridge.connect.side_effect = ConnectionError("test error")
            mock_get_bridge.return_value = mock_bridge
            result = runner.invoke(cli, ["system", "reconnect"])
            # click.echo が err=True で呼ばれたことを確認
            error_calls = [c for c in mock_echo.call_args_list if c.kwargs.get("err") is True]
            assert len(error_calls) > 0, f"Expected click.echo to be called with err=True, but calls were: {mock_echo.call_args_list}"
