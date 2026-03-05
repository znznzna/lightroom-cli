"""Tests for output sanitization in OutputFormatter."""

import json

from cli.output import OutputFormatter


class TestOutputSanitize:
    def test_control_chars_stripped_from_string(self):
        result = OutputFormatter.format({"key": "hello\x00world\x07"}, "json")
        data = json.loads(result)
        assert data["key"] == "helloworld"

    def test_tab_newline_preserved(self):
        result = OutputFormatter.format({"key": "hello\tworld\n"}, "json")
        data = json.loads(result)
        assert "\t" in data["key"]
        assert "\n" in data["key"]

    def test_nested_dict_sanitized(self):
        result = OutputFormatter.format({"outer": {"inner": "val\x01ue"}}, "json")
        data = json.loads(result)
        assert data["outer"]["inner"] == "value"

    def test_list_sanitized(self):
        result = OutputFormatter.format([{"key": "a\x02b"}], "json")
        data = json.loads(result)
        assert data[0]["key"] == "ab"

    def test_overlong_string_truncated_in_json_mode(self):
        long_str = "a" * 60_000
        result = OutputFormatter.format({"key": long_str}, "json")
        data = json.loads(result)
        assert len(data["key"]) < 60_000
        assert "truncated" in data["key"]

    def test_overlong_string_not_truncated_in_text_mode(self):
        long_str = "a" * 60_000
        result = OutputFormatter.format({"key": long_str}, "text")
        assert "a" * 50_001 in result

    def test_non_string_values_unchanged(self):
        result = OutputFormatter.format({"num": 42, "flag": True}, "json")
        data = json.loads(result)
        assert data["num"] == 42
        assert data["flag"] is True

    def test_control_chars_stripped_in_text_mode(self):
        result = OutputFormatter.format({"key": "hello\x07world"}, "text")
        assert "helloworld" in result
