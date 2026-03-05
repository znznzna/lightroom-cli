"""Tests for 3-model review fixes: #13 risk_level, #14 _truncated flag, #15 JSON sanitize."""

import json

import pytest
from click.testing import CliRunner

from cli.main import cli
from cli.output import OutputFormatter
from cli.validation import ValidationError, validate_params


class TestResetMaskingRiskLevel:
    """#13: develop.resetMasking should have risk_level=destructive."""

    def test_reset_masking_requires_confirm(self):
        from lightroom_sdk.schema import get_schema

        schema = get_schema("develop.resetMasking")
        assert schema is not None
        assert schema.requires_confirm is True
        assert schema.risk_level == "destructive"

    def test_reset_masking_dry_run_shows_destructive(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["-o", "json", "develop", "reset-masking", "--dry-run"])
        # Skip deprecation warning line
        # Parse full JSON block from first { onward
        json_start = result.output.index("{")
        data = json.loads(result.output[json_start:])
        assert data["risk_level"] == "destructive"


class TestTruncatedFlag:
    """#14: JSON truncation should set _truncated flag."""

    def test_truncated_flag_added_when_truncation_occurs(self):
        long_value = "x" * 60_000
        data = {"key": long_value}
        result = OutputFormatter.format(data, "json")
        parsed = json.loads(result)
        assert parsed["_truncated"] is True
        assert "truncated" in parsed["key"]

    def test_no_truncated_flag_when_no_truncation(self):
        data = {"key": "short value"}
        result = OutputFormatter.format(data, "json")
        parsed = json.loads(result)
        assert "_truncated" not in parsed

    def test_no_truncated_flag_in_text_mode(self):
        long_value = "x" * 60_000
        data = {"key": long_value}
        result = OutputFormatter.format(data, "text")
        assert "_truncated" not in result

    def test_truncated_flag_with_list_data(self):
        """List top-level: no _truncated flag (only added to dict)."""
        long_value = "x" * 60_000
        data = [{"key": long_value}]
        result = OutputFormatter.format(data, "json")
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert "truncated" in parsed[0]["key"]


class TestJsonSanitizeRecursive:
    """#15: JSON_OBJECT/JSON_ARRAY strings should be sanitized."""

    def test_json_object_with_null_char_rejected(self):
        with pytest.raises(ValidationError, match="null character"):
            validate_params("develop.applySettings", {"settings": {"Exposure": "val\x00ue"}})

    def test_json_object_with_control_char_rejected(self):
        with pytest.raises(ValidationError, match="control characters"):
            validate_params("develop.applySettings", {"settings": {"Exposure": "val\x07ue"}})

    def test_json_object_with_overlong_string_rejected(self):
        with pytest.raises(ValidationError, match="exceeds maximum length"):
            validate_params("develop.applySettings", {"settings": {"key": "x" * 11_000}})

    def test_json_object_with_normal_strings_passes(self):
        result = validate_params("develop.applySettings", {"settings": {"Exposure": 1.0}})
        assert result["settings"]["Exposure"] == 1.0

    def test_json_object_nested_dict_sanitized(self):
        with pytest.raises(ValidationError, match="null character"):
            validate_params("develop.applySettings", {"settings": {"nested": {"key": "a\x00b"}}})

    def test_json_array_with_null_char_rejected(self):
        with pytest.raises(ValidationError, match="null character"):
            validate_params("catalog.addKeywords", {"photoId": "123", "keywords": ["good\x00bad"]})
