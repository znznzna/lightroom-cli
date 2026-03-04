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
