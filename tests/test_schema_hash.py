"""Tests for get_schema_hash()."""

from lightroom_sdk.schema import get_schema_hash


class TestSchemaHash:
    def test_returns_string(self):
        h = get_schema_hash()
        assert isinstance(h, str)

    def test_consistent_across_calls(self):
        h1 = get_schema_hash()
        h2 = get_schema_hash()
        assert h1 == h2

    def test_is_12_char_hex(self):
        h = get_schema_hash()
        assert len(h) == 12
        int(h, 16)  # should not raise
