"""develop.ai 個別タイプスキーマのテスト"""

import pytest

from lightroom_sdk.schema import get_all_schemas, get_schema


class TestDevelopAIIndividualSchemas:
    @pytest.mark.parametrize(
        "ai_type",
        [
            "subject",
            "sky",
            "background",
            "objects",
            "people",
            "landscape",
        ],
    )
    def test_ai_type_schema_exists(self, ai_type):
        schema = get_schema(f"develop.ai.{ai_type}")
        assert schema is not None, f"Schema not found for develop.ai.{ai_type}"
        assert schema.cli_path == f"develop.ai.{ai_type}"

    def test_ai_presets_schema_exists(self):
        schema = get_schema("develop.ai.presets")
        assert schema is not None

    def test_ai_reset_schema_exists(self):
        schema = get_schema("develop.ai.reset")
        assert schema is not None

    def test_ai_list_schema_exists(self):
        schema = get_schema("develop.ai.list")
        assert schema is not None

    def test_ai_batch_schema_exists(self):
        schema = get_schema("develop.ai.batch")
        assert schema is not None
        assert schema.cli_path == "develop.ai.batch"


class TestDevelopAIMaskSchemaRemoved:
    def test_ai_mask_cli_path_not_in_schemas(self):
        all_schemas = get_all_schemas()
        cli_paths = [s.cli_path for s in all_schemas.values()]
        assert "develop.ai.mask" not in cli_paths


class TestDualLookup:
    def test_lookup_by_cli_path(self):
        schema = get_schema("develop.set")
        assert schema is not None
        assert schema.cli_path == "develop.set"

    def test_lookup_by_bridge_command(self):
        schema = get_schema("develop.setValue")
        assert schema is not None
        assert schema.command == "develop.setValue"

    def test_lookup_by_cli_path_system(self):
        schema = get_schema("system.ping")
        assert schema is not None

    def test_lookup_unknown_returns_none(self):
        schema = get_schema("nonexistent.command")
        assert schema is None
