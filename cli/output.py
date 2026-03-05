import json
import re
from io import StringIO
from typing import Any

from rich.console import Console
from rich.table import Table


class OutputFormatter:
    _OUTPUT_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
    _MAX_OUTPUT_STRING_LENGTH = 50_000

    @staticmethod
    def _sanitize_output(data: Any, *, truncate: bool = False, _truncated: list | None = None) -> Any:
        """Sanitize output data: strip control chars, optionally truncate long strings."""
        if isinstance(data, str):
            s = OutputFormatter._OUTPUT_CONTROL_CHAR_RE.sub("", data)
            if truncate and len(s) > OutputFormatter._MAX_OUTPUT_STRING_LENGTH:
                if _truncated is not None:
                    _truncated.append(True)
                return s[: OutputFormatter._MAX_OUTPUT_STRING_LENGTH] + f"... (truncated, {len(data)} chars total)"
            return s
        if isinstance(data, dict):
            return {
                k: OutputFormatter._sanitize_output(v, truncate=truncate, _truncated=_truncated)
                for k, v in data.items()
            }
        if isinstance(data, list):
            return [OutputFormatter._sanitize_output(item, truncate=truncate, _truncated=_truncated) for item in data]
        return data

    @staticmethod
    def format(data: Any, mode: str = "text", fields: list[str] | None = None) -> str:
        truncated_tracker: list = []
        data = OutputFormatter._sanitize_output(data, truncate=(mode == "json"), _truncated=truncated_tracker)
        if truncated_tracker and isinstance(data, dict):
            data["_truncated"] = True
        if fields is not None:
            filtered = OutputFormatter._filter_fields(data, fields)
            if isinstance(filtered, dict) and not filtered and isinstance(data, dict) and data and fields:
                available = sorted(data.keys())[:10]
                filtered["_warning"] = (
                    f"No matching fields found. Requested: {', '.join(fields)}. Available: {', '.join(available)}"
                )
            data = filtered
        if mode == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)
        elif mode == "table":
            return OutputFormatter._format_table(data)
        else:
            return OutputFormatter._format_text(data)

    @staticmethod
    def _filter_fields(data: Any, fields: list[str]) -> Any:
        """指定フィールドのみを残す（ドット記法サポート）"""
        if isinstance(data, dict):
            plain_fields: list[str] = []
            nested_fields: dict[str, list[str]] = {}
            for f in fields:
                if "." in f:
                    parent, child = f.split(".", 1)
                    nested_fields.setdefault(parent, []).append(child)
                else:
                    plain_fields.append(f)

            result: dict[str, Any] = {}
            for k, v in data.items():
                if k in plain_fields:
                    result[k] = v
            for parent, children in nested_fields.items():
                if parent not in data:
                    continue
                value = data[parent]
                if isinstance(value, list):
                    result[parent] = [
                        {c: item[c] for c in children if c in item} if isinstance(item, dict) else item
                        for item in value
                    ]
                elif isinstance(value, dict):
                    result[parent] = {c: value[c] for c in children if c in value}
                # scalar values have no children — skip (dotted filter on scalar is a no-op)
            return result
        elif isinstance(data, list):
            return [OutputFormatter._filter_fields(item, fields) for item in data]
        return data

    @staticmethod
    def _format_text(data: Any, indent: int = 0) -> str:
        if isinstance(data, dict):
            lines = []
            for k, v in data.items():
                if isinstance(v, (dict, list)):
                    lines.append(f"{'  ' * indent}{k}:")
                    lines.append(OutputFormatter._format_text(v, indent + 1))
                else:
                    lines.append(f"{'  ' * indent}{k}: {v}")
            return "\n".join(lines)
        elif isinstance(data, list):
            return "\n".join(OutputFormatter._format_text(item, indent) for item in data)
        return str(data)

    @staticmethod
    def _format_table(data: Any) -> str:
        if not isinstance(data, list) or not data:
            return OutputFormatter._format_text(data)
        console = Console(file=StringIO(), force_terminal=False)
        table = Table()
        for key in data[0].keys():
            table.add_column(key)
        for row in data:
            table.add_row(*[str(v) for v in row.values()])
        console.print(table)
        return console.file.getvalue()

    @staticmethod
    def format_error(
        message: str,
        mode: str = "text",
        *,
        code: str = "ERROR",
        command: str | None = None,
        suggestions: list[str] | None = None,
    ) -> str:
        if mode == "json":
            error_obj: dict[str, Any] = {
                "code": code,
                "message": message,
            }
            if command:
                error_obj["command"] = command
            if suggestions:
                error_obj["suggestions"] = suggestions
            return json.dumps({"error": error_obj})
        return f"Error: {message}"
