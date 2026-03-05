"""MCP tool_registry のテスト。"""

import pytest
from annotated_types import Ge, Le

from lightroom_sdk.schema import CommandSchema, ParamSchema, ParamType
from mcp_server.tool_registry import (
    build_description,
    build_param_field,
    create_tool_function,
    param_type_to_json_schema,
    sanitize_tool_name,
)


class TestSanitizeToolName:
    def test_basic_conversion(self):
        assert sanitize_tool_name("catalog.searchPhotos") == "lr_catalog_search_photos"

    def test_system_ping(self):
        assert sanitize_tool_name("system.ping") == "lr_system_ping"

    def test_develop_set_value(self):
        assert sanitize_tool_name("develop.setValue") == "lr_develop_set_value"

    def test_nested_camel_case(self):
        assert (
            sanitize_tool_name("develop.createAIMaskWithAdjustments")
            == "lr_develop_create_ai_mask_with_adjustments"
        )

    def test_consecutive_uppercase(self):
        """AI のような連続大文字も正しく変換"""
        assert sanitize_tool_name("develop.getAISettings") == "lr_develop_get_ai_settings"


class TestBuildDescription:
    def test_read_only_command(self):
        schema = CommandSchema("system.ping", "system.ping", "Test connection")
        desc = build_description(schema)
        assert "Test connection" in desc
        assert "[read]" in desc
        assert "Timeout:" in desc

    def test_mutating_command(self):
        schema = CommandSchema(
            "develop.setValue",
            "develop.set",
            "Set develop parameter(s)",
            mutating=True,
            supports_dry_run=True,
        )
        desc = build_description(schema)
        assert "mutating" in desc

    def test_destructive_command(self):
        schema = CommandSchema(
            "catalog.removeFromCatalog",
            "catalog.remove-from-catalog",
            "Remove photo from catalog",
            mutating=True,
            requires_confirm=True,
        )
        desc = build_description(schema)
        assert "destructive" in desc


class TestParamTypeToJsonSchema:
    def test_string(self):
        assert param_type_to_json_schema(ParamType.STRING) == {"type": "string"}

    def test_integer(self):
        assert param_type_to_json_schema(ParamType.INTEGER) == {"type": "integer"}

    def test_float(self):
        assert param_type_to_json_schema(ParamType.FLOAT) == {"type": "number"}

    def test_boolean(self):
        assert param_type_to_json_schema(ParamType.BOOLEAN) == {"type": "boolean"}

    def test_json_object(self):
        assert param_type_to_json_schema(ParamType.JSON_OBJECT) == {"type": "object"}

    def test_json_array(self):
        assert param_type_to_json_schema(ParamType.JSON_ARRAY) == {"type": "array"}

    def test_enum_with_values(self):
        result = param_type_to_json_schema(ParamType.ENUM, enum_values=["a", "b"])
        assert result == {"type": "string", "enum": ["a", "b"]}


class TestBuildParamField:
    """required/min/max が Field() に正しく反映されること"""

    def test_required_param_no_default(self):
        """required=True のパラメータは default なし (Pydantic v2: is_required())"""
        param = ParamSchema("photoId", ParamType.STRING, required=True, description="Photo ID")
        annotation, field = build_param_field(param)
        assert annotation is str
        assert field.is_required()

    def test_optional_param_has_default(self):
        """required=False のパラメータは default=None"""
        param = ParamSchema("limit", ParamType.INTEGER, required=False, description="Limit")
        annotation, field = build_param_field(param)
        assert field.default is None

    def test_float_with_min_max(self):
        """min/max が Field(ge=, le=) に変換されること (Pydantic v2: metadata)"""
        param = ParamSchema("rating", ParamType.FLOAT, required=True, description="Rating", min=0.0, max=5.0)
        annotation, field = build_param_field(param)
        assert annotation is float
        assert Ge(ge=0.0) in field.metadata
        assert Le(le=5.0) in field.metadata

    def test_integer_with_min_max(self):
        """integer の min/max (Pydantic v2: metadata)"""
        param = ParamSchema("rating", ParamType.INTEGER, required=True, description="Rating", min=0, max=5)
        annotation, field = build_param_field(param)
        assert annotation is int
        assert Ge(ge=0) in field.metadata
        assert Le(le=5) in field.metadata

    def test_enum_param(self):
        """ENUM パラメータの annotation が Literal になること"""
        param = ParamSchema(
            "label", ParamType.ENUM, required=True, description="Color label", enum_values=["red", "green", "blue"]
        )
        annotation, field = build_param_field(param)
        assert hasattr(annotation, "__args__")
        assert set(annotation.__args__) == {"red", "green", "blue"}

    def test_description_is_set(self):
        """description が Field に設定されること"""
        param = ParamSchema("photoId", ParamType.STRING, required=True, description="The photo identifier")
        _, field = build_param_field(param)
        assert field.description == "The photo identifier"


class TestCreateToolFunction:
    def test_returns_callable(self):
        schema = CommandSchema("system.ping", "system.ping", "Test connection")
        fn = create_tool_function(schema, connection=None)
        assert callable(fn)

    def test_function_name(self):
        schema = CommandSchema("system.ping", "system.ping", "Test connection")
        fn = create_tool_function(schema, connection=None)
        assert fn.__name__ == "lr_system_ping"

    def test_function_has_annotations_for_params(self):
        """パラメータ付きコマンドの関数に型アノテーションがあること"""
        schema = CommandSchema(
            "catalog.setRating",
            "catalog.set-rating",
            "Set rating",
            mutating=True,
            params=[
                ParamSchema("photoId", ParamType.STRING, required=True, description="Photo ID"),
                ParamSchema("rating", ParamType.INTEGER, required=True, description="Rating 0-5", min=0, max=5),
            ],
        )
        fn = create_tool_function(schema, connection=None)
        annotations = fn.__annotations__
        assert "photoId" in annotations
        assert "rating" in annotations


class TestToolCount:
    def test_plugin_commands_excluded(self):
        """plugin.* コマンドは MCP ツールから除外される"""
        from lightroom_sdk.schema import COMMAND_SCHEMAS

        non_plugin = {k: v for k, v in COMMAND_SCHEMAS.items() if not k.startswith("plugin.")}
        assert len(non_plugin) > 100
        plugin_count = sum(1 for k in COMMAND_SCHEMAS if k.startswith("plugin."))
        assert plugin_count == 3
