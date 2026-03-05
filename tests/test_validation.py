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

    def test_boolean_true_values(self):
        from cli.validation import validate_params
        for val in [True, "true", "1", "yes", "True", "YES"]:
            result = validate_params(
                "catalog.getFolders",
                {"includeSubfolders": val}
            )
            assert result["includeSubfolders"] is True

    def test_boolean_false_values(self):
        from cli.validation import validate_params
        for val in [False, "false", "0", "no", "False", "NO"]:
            result = validate_params(
                "catalog.getFolders",
                {"includeSubfolders": val}
            )
            assert result["includeSubfolders"] is False

    def test_boolean_invalid_string_raises(self):
        from cli.validation import validate_params, ValidationError
        with pytest.raises(ValidationError, match="expected boolean"):
            validate_params(
                "catalog.getFolders",
                {"includeSubfolders": "flase"}
            )

    def test_json_object_valid(self):
        from cli.validation import validate_params
        result = validate_params(
            "develop.applySettings",
            {"settings": {"Exposure": 0.5}}
        )
        assert result["settings"] == {"Exposure": 0.5}

    def test_json_object_invalid_raises(self):
        from cli.validation import validate_params, ValidationError
        with pytest.raises(ValidationError, match="expected JSON object"):
            validate_params(
                "develop.applySettings",
                {"settings": "not_a_dict"}
            )

    def test_json_array_valid(self):
        from cli.validation import validate_params
        result = validate_params(
            "catalog.addKeywords",
            {"photoId": "123", "keywords": ["sunset", "beach"]}
        )
        assert result["keywords"] == ["sunset", "beach"]

    def test_json_array_invalid_raises(self):
        from cli.validation import validate_params, ValidationError
        with pytest.raises(ValidationError, match="expected JSON array"):
            validate_params(
                "catalog.addKeywords",
                {"photoId": "123", "keywords": "not_a_list"}
            )

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


class TestSuggestions:
    """suggestions フィールドの発火テスト"""

    def test_unknown_param_has_suggestions(self):
        from cli.validation import validate_params, ValidationError
        with pytest.raises(ValidationError) as exc_info:
            validate_params("develop.setValue", {"Exposre": 0.5})
        assert len(exc_info.value.suggestions) > 0
        assert "Exposure" in exc_info.value.suggestions[0] or "parameter" in exc_info.value.suggestions[0]

    def test_enum_error_has_suggestions(self):
        """enum バリデーションエラー時に有効な値の一覧が suggestions に含まれる"""
        from cli.validation import validate_params, ValidationError
        with pytest.raises(ValidationError) as exc_info:
            validate_params("develop.selectTool", {"tool": "invalid_tool"})
        assert len(exc_info.value.suggestions) > 0
        all_suggestions = " ".join(exc_info.value.suggestions)
        assert "crop" in all_suggestions or "loupe" in all_suggestions

    def test_type_error_has_suggestions(self):
        """型変換エラー時に期待される型の例が suggestions に含まれる"""
        from cli.validation import validate_params, ValidationError
        with pytest.raises(ValidationError) as exc_info:
            validate_params("develop.setValue", {"parameter": "Exposure", "value": "not_a_number"})
        assert len(exc_info.value.suggestions) > 0

    def test_format_error_json_includes_suggestions(self):
        """format_error JSON モードで suggestions が実際に出力される"""
        from cli.output import OutputFormatter
        import json
        result = OutputFormatter.format_error(
            "test error", "json",
            code="VALIDATION_ERROR",
            suggestions=["try Exposure", "try Contrast"],
        )
        parsed = json.loads(result)
        assert "suggestions" in parsed["error"]
        assert len(parsed["error"]["suggestions"]) == 2
