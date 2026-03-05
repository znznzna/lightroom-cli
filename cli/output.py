import json
from io import StringIO
from typing import Any
from rich.console import Console
from rich.table import Table


class OutputFormatter:
    @staticmethod
    def format(data: Any, mode: str = "text", fields: list[str] | None = None) -> str:
        if fields is not None:
            data = OutputFormatter._filter_fields(data, fields)
        if mode == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)
        elif mode == "table":
            return OutputFormatter._format_table(data)
        else:
            return OutputFormatter._format_text(data)

    @staticmethod
    def _filter_fields(data: Any, fields: list[str]) -> Any:
        """指定フィールドのみを残す（トップレベルのみ）"""
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if k in fields}
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
    def format_error(message: str, mode: str = "text") -> str:
        if mode == "json":
            return json.dumps({"error": message})
        return f"Error: {message}"
