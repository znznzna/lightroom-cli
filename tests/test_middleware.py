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
