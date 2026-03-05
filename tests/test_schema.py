"""Tests for command schema definitions."""
import pytest


class TestSchemaDataStructures:
    """ParamType, ParamSchema, CommandSchema のテスト"""

    def test_param_type_values(self):
        from lightroom_sdk.schema import ParamType
        assert ParamType.STRING.value == "string"
        assert ParamType.INTEGER.value == "integer"
        assert ParamType.FLOAT.value == "float"
        assert ParamType.BOOLEAN.value == "boolean"
        assert ParamType.ENUM.value == "enum"

    def test_command_schema_creation(self):
        from lightroom_sdk.schema import CommandSchema, ParamSchema, ParamType
        schema = CommandSchema(
            command="develop.setValue",
            cli_path="develop.set",
            description="Set develop parameter",
            params=[
                ParamSchema("parameter", ParamType.STRING, required=True),
                ParamSchema("value", ParamType.FLOAT, required=True),
            ],
            mutating=True,
            timeout=10.0,
        )
        assert schema.command == "develop.setValue"
        assert schema.mutating is True
        assert len(schema.params) == 2

    def test_get_schema_returns_none_for_unknown(self):
        from lightroom_sdk.schema import get_schema
        assert get_schema("nonexistent.command") is None

    def test_get_schema_returns_defined_command(self):
        from lightroom_sdk.schema import get_schema
        schema = get_schema("develop.setValue")
        assert schema is not None
        assert schema.command == "develop.setValue"

    def test_get_schemas_by_group(self):
        from lightroom_sdk.schema import get_schemas_by_group
        develop_schemas = get_schemas_by_group("develop")
        assert len(develop_schemas) > 0
        for schema in develop_schemas.values():
            assert schema.cli_path.startswith("develop.")

    def test_get_all_schemas_not_empty(self):
        from lightroom_sdk.schema import get_all_schemas
        schemas = get_all_schemas()
        assert len(schemas) > 0


class TestSchemaIntegrity:
    """スキーマ定義の整合性テスト"""

    def test_all_schemas_have_command(self):
        from lightroom_sdk.schema import get_all_schemas
        for name, schema in get_all_schemas().items():
            assert schema.command == name, f"Key mismatch: {name} != {schema.command}"

    def test_all_schemas_have_cli_path(self):
        from lightroom_sdk.schema import get_all_schemas
        for name, schema in get_all_schemas().items():
            assert schema.cli_path, f"Missing cli_path for {name}"

    def test_all_schemas_have_description(self):
        from lightroom_sdk.schema import get_all_schemas
        for name, schema in get_all_schemas().items():
            assert schema.description, f"Missing description for {name}"

    def test_enum_params_have_values(self):
        from lightroom_sdk.schema import get_all_schemas, ParamType
        for name, schema in get_all_schemas().items():
            for param in schema.params:
                if param.type == ParamType.ENUM:
                    assert param.enum_values, (
                        f"ENUM param '{param.name}' in '{name}' has no enum_values"
                    )

    def test_no_duplicate_cli_paths(self):
        from lightroom_sdk.schema import get_all_schemas
        paths = [s.cli_path for s in get_all_schemas().values()]
        non_template = [p for p in paths if "<" not in p]
        assert len(non_template) == len(set(non_template)), (
            f"Duplicate cli_paths found: "
            f"{[p for p in non_template if non_template.count(p) > 1]}"
        )

    def test_mutating_commands_count(self):
        """mutating コマンドが一定数以上定義されていることを確認"""
        from lightroom_sdk.schema import get_all_schemas
        mutating = [s for s in get_all_schemas().values() if s.mutating]
        assert len(mutating) >= 30, f"Expected >=30 mutating commands, got {len(mutating)}"


class TestParamDescriptions:
    """パラメータ description 非空テスト"""

    def test_all_params_have_descriptions(self):
        from lightroom_sdk.schema import get_all_schemas
        missing = []
        for cmd_name, schema in get_all_schemas().items():
            for p in schema.params:
                if not p.description:
                    missing.append(f"{cmd_name}.{p.name}")
        assert missing == [], f"Empty descriptions: {missing}"


class TestDevelopAISchema:
    """develop.ai スキーマのテスト"""

    def test_ai_mask_schema_exists(self):
        from lightroom_sdk.schema import get_schema
        schema = get_schema("develop.createAIMaskWithAdjustments")
        assert schema is not None
        assert schema.cli_path == "develop.ai.mask"

    def test_ai_group_lists_mask_and_batch(self):
        from lightroom_sdk.schema import get_schemas_by_group
        schemas = get_schemas_by_group("develop.ai")
        cli_paths = [s.cli_path for s in schemas.values()]
        assert "develop.ai.mask" in cli_paths
        assert "develop.ai.batch" in cli_paths


class TestResponseFields:
    """response_fields の充実テスト"""

    @pytest.mark.parametrize("command,expected_fields", [
        ("system.ping", ["status", "timestamp"]),
        ("system.status", ["status", "uptime", "version", "connections"]),
        ("catalog.getSelectedPhotos", ["photos", "count"]),
        ("catalog.getAllPhotos", ["photos", "total", "limit", "offset"]),
        ("catalog.searchPhotos", ["photos", "total", "query"]),
        ("catalog.getPhotoMetadata", ["filename", "path", "rating", "flag", "keywords"]),
        ("preview.generatePreview", ["path", "size", "format"]),
        ("develop.getValue", ["parameter", "value"]),
        ("develop.getRange", ["parameter", "min", "max"]),
    ])
    def test_response_fields_not_empty(self, command, expected_fields):
        from lightroom_sdk.schema import get_schema
        schema = get_schema(command)
        assert schema is not None, f"Schema not found for {command}"
        assert len(schema.response_fields) > 0, f"response_fields empty for {command}"
        for field in expected_fields:
            assert field in schema.response_fields, f"Missing response field '{field}' in {command}"
