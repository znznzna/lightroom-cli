"""Schema-driven MCP tool registration.

Converts COMMAND_SCHEMAS into FastMCP tools automatically.
"""

from __future__ import annotations

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


def param_type_to_json_schema(
    param_type: ParamType, enum_values: list[str] | None = None
) -> dict[str, Any]:
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


def create_tool_function(
    schema: CommandSchema, connection: "ConnectionManager | None"
) -> Any:
    """Create an async tool function for a given CommandSchema."""
    tool_name = sanitize_tool_name(schema.command)

    param_annotations: dict[str, type] = {}
    param_defaults: dict[str, FieldInfo] = {}

    if schema.params:
        for param in schema.params:
            annotation, field = build_param_field(param)
            param_annotations[param.name] = annotation
            param_defaults[param.name] = field

    async def tool_fn(**kwargs: Any) -> Any:
        if connection is None:
            return {"error": "No connection manager configured"}

        dry_run = kwargs.pop("dry_run", False)
        if dry_run and schema.mutating:
            return {
                "dry_run": True,
                "command": schema.command,
                "mutating": schema.mutating,
                "risk_level": schema.risk_level,
                "params": kwargs,
            }

        return await connection.execute(
            command=schema.command,
            params=kwargs,
            timeout=schema.timeout,
            mutating=schema.mutating,
        )

    tool_fn.__name__ = tool_name
    tool_fn.__qualname__ = tool_name

    tool_fn.__annotations__ = param_annotations.copy()
    if param_defaults:
        tool_fn.__kwdefaults__ = {
            name: field.default
            for name, field in param_defaults.items()
            if field.default is not ...
        }

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
