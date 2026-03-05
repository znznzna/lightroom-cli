"""_filter_fields ドット記法サポートのテスト"""
import json
from cli.output import OutputFormatter


class TestDotNotationFilter:
    def test_dot_notation_extracts_from_list(self):
        data = {
            "photos": [
                {"id": "1", "name": "a.jpg", "rating": 5},
                {"id": "2", "name": "b.jpg", "rating": 3},
            ],
            "total": 2,
        }
        result = OutputFormatter._filter_fields(data, ["photos.id", "total"])
        assert result == {"photos": [{"id": "1"}, {"id": "2"}], "total": 2}

    def test_dot_notation_extracts_multiple_subfields(self):
        data = {"photos": [{"id": "1", "name": "a.jpg", "rating": 5}]}
        result = OutputFormatter._filter_fields(data, ["photos.id", "photos.name"])
        assert result == {"photos": [{"id": "1", "name": "a.jpg"}]}

    def test_dot_notation_nonexistent_subfield(self):
        data = {"photos": [{"id": "1", "name": "a.jpg"}]}
        result = OutputFormatter._filter_fields(data, ["photos.nonexistent"])
        assert result == {"photos": [{}]}

    def test_dot_notation_nonexistent_top_level(self):
        data = {"photos": [{"id": "1"}], "total": 2}
        result = OutputFormatter._filter_fields(data, ["nonexistent.id"])
        assert result == {}

    def test_dot_notation_on_dict_value(self):
        data = {"metadata": {"width": 1920, "height": 1080}, "name": "photo.jpg"}
        result = OutputFormatter._filter_fields(data, ["metadata.width"])
        assert result == {"metadata": {"width": 1920}}

    def test_mixed_dot_and_plain_fields(self):
        data = {
            "photos": [{"id": "1", "name": "a.jpg"}],
            "total": 2,
            "query": "sunset",
        }
        result = OutputFormatter._filter_fields(data, ["photos.id", "total"])
        assert result == {"photos": [{"id": "1"}], "total": 2}

    def test_top_level_only_backward_compat(self):
        data = {"name": "photo.jpg", "rating": 5, "size": 1024}
        result = OutputFormatter._filter_fields(data, ["name", "rating"])
        assert result == {"name": "photo.jpg", "rating": 5}

    def test_dot_notation_on_scalar_ignored(self):
        """スカラー値に対するドット記法はスキップされる（Codex P2 fix）"""
        data = {"total": 2, "photos": [{"id": "1"}]}
        result = OutputFormatter._filter_fields(data, ["total.id"])
        assert result == {}

    def test_format_with_dot_notation(self):
        data = {"photos": [{"id": "1", "name": "a.jpg"}], "total": 1}
        output = OutputFormatter.format(data, "json", fields=["photos.id", "total"])
        parsed = json.loads(output)
        assert parsed == {"photos": [{"id": "1"}], "total": 1}
