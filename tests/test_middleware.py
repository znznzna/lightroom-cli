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
