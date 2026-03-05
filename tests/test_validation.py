"""Tests for input validation."""
import pytest


class TestValidateParams:
    """validate_params() のテスト"""

    def test_valid_params_pass_through(self):
        from cli.validation import validate_params
        result = validate_params(
            "develop.setValue",
            {"parameter": "Exposure", "value": 0.5}
        )
        assert result["parameter"] == "Exposure"
        assert result["value"] == 0.5

    def test_unknown_param_raises(self):
        from cli.validation import validate_params, ValidationError
        with pytest.raises(ValidationError, match="Unknown parameter"):
            validate_params("develop.setValue", {"Exposre": 0.5})

    def test_missing_required_param_raises(self):
        from cli.validation import validate_params, ValidationError
        with pytest.raises(ValidationError, match="Required parameter"):
            validate_params("develop.setValue", {"parameter": "Exposure"})

    def test_type_coercion_string_to_float(self):
        from cli.validation import validate_params
        result = validate_params(
            "develop.setValue",
            {"parameter": "Exposure", "value": "0.5"}
        )
        assert result["value"] == 0.5
        assert isinstance(result["value"], float)

    def test_invalid_type_raises(self):
        from cli.validation import validate_params, ValidationError
        with pytest.raises(ValidationError, match="Invalid type"):
            validate_params(
                "develop.setValue",
                {"parameter": "Exposure", "value": "not_a_number"}
            )

    def test_unknown_command_skips_validation(self):
        from cli.validation import validate_params
        result = validate_params(
            "unknown.command",
            {"any_param": "any_value"}
        )
        assert result == {"any_param": "any_value"}

    def test_enum_valid_value(self):
        from cli.validation import validate_params
        result = validate_params(
            "develop.selectTool",
            {"tool": "crop"}
        )
        assert result["tool"] == "crop"

    def test_enum_invalid_value_raises(self):
        from cli.validation import validate_params, ValidationError
        with pytest.raises(ValidationError, match="Invalid value"):
            validate_params(
                "develop.selectTool",
                {"tool": "invalid_tool"}
            )


class TestFindSimilar:
    """類似パラメータ名提案のテスト"""

    def test_finds_similar_by_substring(self):
        from cli.validation import _find_similar
        suggestions = _find_similar("Exposre", {"Exposure", "Contrast", "Highlights"})
        assert "Exposure" in suggestions

    def test_returns_empty_for_no_match(self):
        from cli.validation import _find_similar
        suggestions = _find_similar("zzzzz", {"Exposure", "Contrast"})
        assert suggestions == []
