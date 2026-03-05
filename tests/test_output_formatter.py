import json
import pytest
from cli.output import OutputFormatter


def test_json_output():
    data = {"status": "ok", "version": "1.0"}
    result = OutputFormatter.format(data, "json")
    parsed = json.loads(result)
    assert parsed["status"] == "ok"


def test_text_output_flat():
    data = {"name": "photo.jpg", "rating": 5}
    result = OutputFormatter.format(data, "text")
    assert "name" in result
    assert "photo.jpg" in result


def test_table_output_list():
    data = [
        {"name": "a.jpg", "rating": 3},
        {"name": "b.jpg", "rating": 5},
    ]
    result = OutputFormatter.format(data, "table")
    assert "a.jpg" in result
    assert "b.jpg" in result


def test_text_output_nested():
    data = {"settings": {"exposure": 1.5, "contrast": 10}}
    result = OutputFormatter.format(data, "text")
    assert "exposure" in result


def test_format_error():
    result = OutputFormatter.format_error("Something went wrong", "text")
    assert "Error" in result or "error" in result.lower()


class TestFieldsFiltering:
    """--fields によるレスポンスフィールド制限テスト"""

    def test_filter_dict_fields(self):
        data = {"name": "photo.jpg", "rating": 5, "size": 1024}
        result = OutputFormatter.format(data, "json", fields=["name", "rating"])
        parsed = json.loads(result)
        assert parsed == {"name": "photo.jpg", "rating": 5}
        assert "size" not in parsed

    def test_filter_list_of_dicts(self):
        data = [
            {"name": "a.jpg", "rating": 3, "size": 100},
            {"name": "b.jpg", "rating": 5, "size": 200},
        ]
        result = OutputFormatter.format(data, "json", fields=["name"])
        parsed = json.loads(result)
        assert parsed == [{"name": "a.jpg"}, {"name": "b.jpg"}]

    def test_no_fields_returns_all(self):
        data = {"name": "photo.jpg", "rating": 5}
        result = OutputFormatter.format(data, "json", fields=None)
        parsed = json.loads(result)
        assert parsed == {"name": "photo.jpg", "rating": 5}

    def test_filter_non_dict_returns_as_is(self):
        result = OutputFormatter.format("hello", "text", fields=["name"])
        assert result == "hello"

    def test_empty_fields_list_returns_empty_dict(self):
        data = {"name": "photo.jpg", "rating": 5}
        result = OutputFormatter.format(data, "json", fields=[])
        parsed = json.loads(result)
        assert parsed == {}


class TestStructuredError:
    """構造化エラー出力のテスト"""

    def test_json_error_is_structured(self):
        result = OutputFormatter.format_error("Something went wrong", mode="json")
        parsed = json.loads(result)
        assert "error" in parsed
        assert parsed["error"]["message"] == "Something went wrong"

    def test_json_error_with_code(self):
        result = OutputFormatter.format_error(
            "Unknown param", mode="json", code="VALIDATION_ERROR"
        )
        parsed = json.loads(result)
        assert parsed["error"]["code"] == "VALIDATION_ERROR"

    def test_json_error_with_suggestions(self):
        result = OutputFormatter.format_error(
            "Unknown param 'Exposre'", mode="json",
            code="VALIDATION_ERROR", suggestions=["Exposure"]
        )
        parsed = json.loads(result)
        assert parsed["error"]["suggestions"] == ["Exposure"]

    def test_text_error_unchanged(self):
        result = OutputFormatter.format_error("Something went wrong", mode="text")
        assert result == "Error: Something went wrong"

    def test_json_error_backward_compat(self):
        """既存呼び出し (mode 未指定) が壊れないことを確認"""
        result = OutputFormatter.format_error("fail")
        assert "fail" in result


class TestFilterFieldsNested:
    """_filter_fields のネストされたレスポンス対応テスト"""

    def test_filter_top_level(self):
        """トップレベルのフィールドフィルタ"""
        data = {"Exposure": 0.5, "Contrast": 25, "Highlights": -10}
        result = OutputFormatter._filter_fields(data, ["Exposure", "Contrast"])
        assert result == {"Exposure": 0.5, "Contrast": 25}

    def test_filter_empty_result_warning(self):
        """フィルタ結果が空の場合の動作"""
        data = {"Exposure2012": 0.5}
        result = OutputFormatter._filter_fields(data, ["Exposure"])
        assert result == {}

    def test_filter_nested_result_key(self):
        """result キーの中にデータがある場合"""
        data = {"result": {"Exposure": 0.5, "Contrast": 25}}
        result = OutputFormatter._filter_fields(data, ["Exposure"])
        assert result == {}

    def test_filter_fields_case_sensitive(self):
        """フィールド名は大文字小文字を区別する"""
        data = {"Exposure": 0.5, "exposure": 1.0}
        result = OutputFormatter._filter_fields(data, ["Exposure"])
        assert result == {"Exposure": 0.5}


class TestFieldsWarning:
    """--fields でフィールドが見つからない場合の警告テスト"""

    def test_format_with_empty_fields_result_includes_warning(self):
        """フィルタ結果が空 dict の場合、_warning が含まれる"""
        data = {"Exposure2012": 0.5}
        result = OutputFormatter.format(data, "json", fields=["Exposure"])
        parsed = json.loads(result)
        assert "_warning" in parsed
        assert "Exposure" in parsed["_warning"]
        assert "Exposure2012" in parsed["_warning"]
