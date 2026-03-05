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
        for key in develop_schemas:
            assert key.startswith("develop.")

    def test_get_all_schemas_not_empty(self):
        from lightroom_sdk.schema import get_all_schemas
        schemas = get_all_schemas()
        assert len(schemas) > 0
