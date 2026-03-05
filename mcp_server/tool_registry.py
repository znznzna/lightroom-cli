"""Schema-driven MCP tool registration.

Converts COMMAND_SCHEMAS into FastMCP tools automatically.

fastmcp >=3.0 では **kwargs 関数を tool として登録できないため、
各コマンドのパラメータから明示的シグネチャを持つ関数を動的生成する。
"""

from __future__ import annotations

import inspect
import re
from typing import TYPE_CHECKING, Any, Literal, Optional

from pydantic import Field
from pydantic.fields import FieldInfo

from lightroom_sdk.schema import COMMAND_SCHEMAS, CommandSchema, ParamSchema, ParamType

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from mcp_server.connection import ConnectionManager


def sanitize_tool_name(command: str) -> str:
    """Convert command name to MCP tool name.

    catalog.searchPhotos -> lr_catalog_search_photos
    develop.createAIMaskWithAdjustments -> lr_develop_create_ai_mask_with_adjustments
    """
    parts = command.split(".")
    result_parts = []
    for part in parts:
        # CamelCase -> snake_case
        snake = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", part)
        snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", snake)
        result_parts.append(snake.lower())
    return "lr_" + "_".join(result_parts)


def build_description(schema: CommandSchema) -> str:
    """Build tool description with metadata suffix."""
    tags = []
    tags.append(schema.risk_level)
    if schema.mutating:
        tags.append("mutating")
    if schema.requires_confirm:
        tags.append("requires_confirm")
    if schema.supports_dry_run:
        tags.append("supports_dry_run")

    tag_str = ", ".join(tags)
    return f"{schema.description} [{tag_str}] Timeout: {schema.timeout}s"


def param_type_to_json_schema(param_type: ParamType, enum_values: list[str] | None = None) -> dict[str, Any]:
    """Convert ParamType to JSON Schema type."""
    mapping = {
        ParamType.STRING: {"type": "string"},
        ParamType.INTEGER: {"type": "integer"},
        ParamType.FLOAT: {"type": "number"},
        ParamType.BOOLEAN: {"type": "boolean"},
        ParamType.JSON_OBJECT: {"type": "object"},
        ParamType.JSON_ARRAY: {"type": "array"},
    }
    if param_type == ParamType.ENUM:
        result: dict[str, Any] = {"type": "string"}
        if enum_values:
            result["enum"] = enum_values
        return result
    return mapping.get(param_type, {"type": "string"})


# ParamSchema から型アノテーション + Field() を生成
_PARAM_TYPE_MAP = {
    ParamType.STRING: str,
    ParamType.INTEGER: int,
    ParamType.FLOAT: float,
    ParamType.BOOLEAN: bool,
    ParamType.JSON_OBJECT: dict,
    ParamType.JSON_ARRAY: list,
}


def build_param_field(param: ParamSchema) -> tuple[type, FieldInfo]:
    """ParamSchema から (annotation, Field()) ペアを生成。

    NOTE: ParamSchema uses .type, .min, .max (not param_type, min_value, max_value)
    """
    # 型アノテーション
    if param.type == ParamType.ENUM and param.enum_values:
        annotation = Literal[tuple(param.enum_values)]  # type: ignore[valid-type]
    else:
        annotation = _PARAM_TYPE_MAP.get(param.type, str)

    # Field kwargs
    field_kwargs: dict[str, Any] = {
        "description": param.description,
    }

    if param.required:
        field_kwargs["default"] = ...
    else:
        field_kwargs["default"] = None
        annotation = Optional[annotation]  # type: ignore[valid-type]

    if param.min is not None:
        field_kwargs["ge"] = param.min
    if param.max is not None:
        field_kwargs["le"] = param.max

    return annotation, Field(**field_kwargs)


def create_tool_function(schema: CommandSchema, connection: "ConnectionManager | None") -> Any:
    """Create an async tool function for a given CommandSchema.

    fastmcp >=3.0 では **kwargs を持つ関数を tool 登録できないため、
    inspect.Parameter で明示的シグネチャを持つ関数を動的生成する。
    """
    tool_name = sanitize_tool_name(schema.command)

    # パラメータ情報を収集
    param_annotations: dict[str, type] = {}
    param_fields: dict[str, FieldInfo] = {}
    sig_params: list[inspect.Parameter] = []

    if schema.params:
        for param_schema in schema.params:
            annotation, field = build_param_field(param_schema)
            param_annotations[param_schema.name] = annotation
            param_fields[param_schema.name] = field

            # ParamSchema.required を直接チェック（Field.default は PydanticUndefined になるため）
            default = inspect.Parameter.empty if param_schema.required else None
            sig_params.append(
                inspect.Parameter(
                    name=param_schema.name,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    default=default,
                    annotation=annotation,
                )
            )

    # mutating コマンドには dry_run パラメータを追加
    if schema.mutating:
        sig_params.append(
            inspect.Parameter(
                name="dry_run",
                kind=inspect.Parameter.KEYWORD_ONLY,
                default=False,
                annotation=bool,
            )
        )
        param_annotations["dry_run"] = bool

    sig = inspect.Signature(parameters=sig_params)

    # クロージャで schema と connection をキャプチャ
    _schema = schema
    _connection = connection

    async def tool_fn(**kwargs: Any) -> Any:
        if _connection is None:
            return {"error": "No connection manager configured"}

        dry_run = kwargs.pop("dry_run", False)
        if dry_run and _schema.mutating:
            return {
                "dry_run": True,
                "command": _schema.command,
                "mutating": _schema.mutating,
                "risk_level": _schema.risk_level,
                "params": kwargs,
            }

        # None のオプションパラメータを除去
        filtered = {k: v for k, v in kwargs.items() if v is not None}

        return await _connection.execute(
            command=_schema.command,
            params=filtered,
            timeout=_schema.timeout,
            mutating=_schema.mutating,
        )

    tool_fn.__name__ = tool_name
    tool_fn.__qualname__ = tool_name
    tool_fn.__signature__ = sig
    tool_fn.__annotations__ = param_annotations.copy()

    return tool_fn


def register_all_tools(mcp: "FastMCP", connection: "ConnectionManager") -> int:
    """Register all COMMAND_SCHEMAS as MCP tools. Returns count of registered tools."""
    count = 0
    for name, schema in COMMAND_SCHEMAS.items():
        if name.startswith("plugin."):
            continue

        tool_fn = create_tool_function(schema, connection)
        tool_name = sanitize_tool_name(name)
        description = build_description(schema)

        mcp.tool(name=tool_name, description=description)(tool_fn)
        count += 1

    return count
