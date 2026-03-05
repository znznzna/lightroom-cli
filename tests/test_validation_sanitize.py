"""Tests for string input sanitization in _coerce_type()."""

import pytest

from cli.validation import ValidationError, validate_params


class TestStringSanitization:
    def test_null_character_rejected(self):
        with pytest.raises(ValidationError, match="null character"):
            validate_params("develop.setValue", {"parameter": "Exp\x00sure", "value": 0.5})

    def test_control_character_rejected(self):
        with pytest.raises(ValidationError, match="control character"):
            validate_params("develop.setValue", {"parameter": "Exp\x01sure", "value": 0.5})

    def test_bell_character_rejected(self):
        with pytest.raises(ValidationError, match="control character"):
            validate_params("develop.setValue", {"parameter": "Exp\x07sure", "value": 0.5})

    def test_tab_allowed(self):
        result = validate_params("develop.setValue", {"parameter": "Exposure\t", "value": 0.5})
        assert "\t" in result["parameter"]

    def test_newline_allowed(self):
        result = validate_params("catalog.setTitle", {"photoId": "123", "title": "line1\nline2"})
        assert "\n" in result["title"]

    def test_overlong_string_rejected(self):
        long_str = "a" * 10_001
        with pytest.raises(ValidationError, match="exceeds maximum length"):
            validate_params("develop.setValue", {"parameter": long_str, "value": 0.5})

    def test_max_length_string_passes(self):
        exact_str = "a" * 10_000
        result = validate_params("develop.setValue", {"parameter": exact_str, "value": 0.5})
        assert len(result["parameter"]) == 10_000

    def test_normal_string_passes(self):
        result = validate_params("develop.setValue", {"parameter": "Exposure", "value": 0.5})
        assert result["parameter"] == "Exposure"
