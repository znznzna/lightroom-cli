"""CLI と MCP でバリデーション結果が一致することを確認。"""

import pytest

from lightroom_sdk.validation import ValidationError, validate_params


class TestValidationEquivalence:
    """CLI と MCP は同一の validate_params を使うため、結果は同一であること。"""

    def test_valid_params_pass(self):
        """正常パラメータが通ること"""
        result = validate_params("catalog.setRating", {"photoId": "1", "rating": 3})
        assert result["photoId"] == "1"
        assert result["rating"] == 3

    def test_unknown_param_raises(self):
        """不明パラメータでエラー"""
        with pytest.raises(ValidationError) as exc_info:
            validate_params("catalog.setRating", {"photoId": "1", "rating": 3, "bad": "x"})
        assert "bad" in str(exc_info.value)

    def test_missing_required_raises(self):
        """必須パラメータ欠落でエラー"""
        with pytest.raises(ValidationError):
            validate_params("catalog.setRating", {"photoId": "1"})

    def test_type_coercion(self):
        """文字列 -> 数値の型変換"""
        result = validate_params("catalog.setRating", {"photoId": "1", "rating": "3"})
        assert result["rating"] == 3

    def test_range_validation(self):
        """範囲外でエラー"""
        with pytest.raises(ValidationError):
            validate_params("catalog.setRating", {"photoId": "1", "rating": 10})

    def test_enum_validation(self):
        """ENUM のバリデーション"""
        result = validate_params("catalog.setColorLabel", {"photoId": "1", "label": "red"})
        assert result["label"] == "red"

        with pytest.raises(ValidationError):
            validate_params("catalog.setColorLabel", {"photoId": "1", "label": "orange"})

    def test_unknown_command_passes_through(self):
        """スキーマ未定義のコマンドはバリデーションスキップ"""
        result = validate_params("unknown.command", {"any": "param"})
        assert result == {"any": "param"}

    def test_validation_source_is_sdk(self):
        """バリデーションが lightroom_sdk.validation から来ていること"""
        import lightroom_sdk.validation as sdk_val

        assert validate_params is sdk_val.validate_params
