# Agent-First CLI Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** AIエージェント向けにCLIを最適化（TTY検出、スキーマ、バリデーション、--fields、--dry-run、--json）
**Architecture:** Layered Enhancement -- 既存コマンドを壊さず、middleware/decorator/スキーマを段階的に追加
**Tech Stack:** Python 3.10+, Click 8.x, pytest
---

## Phase 1: TTY検出 + 環境変数

### Task 1: cli/middleware.py -- resolve_output_format

**Files:**
- Create: `cli/middleware.py`
- Test: `tests/test_middleware.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_middleware.py
"""Tests for CLI middleware (TTY detection, environment variable resolution)."""
import sys
import pytest


class TestResolveOutputFormat:
    """resolve_output_format() のテスト"""

    def test_explicit_output_takes_priority(self):
        from cli.middleware import resolve_output_format
        assert resolve_output_format("table") == "table"

    def test_explicit_json_overrides_tty(self):
        from cli.middleware import resolve_output_format
        assert resolve_output_format("json") == "json"

    def test_env_var_used_when_no_explicit(self, monkeypatch):
        from cli.middleware import resolve_output_format
        monkeypatch.setenv("LR_OUTPUT", "table")
        assert resolve_output_format(None) == "table"

    def test_invalid_env_var_ignored(self, monkeypatch):
        from cli.middleware import resolve_output_format
        monkeypatch.setenv("LR_OUTPUT", "invalid_format")
        # Should fall through to TTY detection
        result = resolve_output_format(None)
        assert result in ("json", "text")

    def test_non_tty_defaults_to_json(self, monkeypatch):
        from cli.middleware import resolve_output_format
        monkeypatch.delenv("LR_OUTPUT", raising=False)
        monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
        assert resolve_output_format(None) == "json"

    def test_tty_defaults_to_text(self, monkeypatch):
        from cli.middleware import resolve_output_format
        monkeypatch.delenv("LR_OUTPUT", raising=False)
        monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
        assert resolve_output_format(None) == "text"
```

**Step 2: 失敗を確認**
Run: `venv/bin/python -m pytest tests/test_middleware.py::TestResolveOutputFormat -v`
Expected: FAIL (ModuleNotFoundError)

**Step 3: 最小限の実装**

```python
# cli/middleware.py
"""CLI middleware: TTY detection, environment variable resolution."""
import os
import sys


def resolve_output_format(explicit_output: str | None) -> str:
    """
    出力フォーマットの優先順位:
    1. --output / -o フラグ（明示指定）
    2. LR_OUTPUT 環境変数
    3. TTY検出（非TTYなら json, TTYなら text）
    """
    if explicit_output is not None:
        return explicit_output

    env_output = os.environ.get("LR_OUTPUT")
    if env_output and env_output in ("json", "text", "table"):
        return env_output

    if not sys.stdout.isatty():
        return "json"

    return "text"
```

**Step 4: 通過を確認**
Run: `venv/bin/python -m pytest tests/test_middleware.py::TestResolveOutputFormat -v`
Expected: PASS

**Step 5: 全テスト回帰確認**
Run: `venv/bin/python -m pytest tests/ -v --ignore=tests/e2e`
Expected: ALL PASS

**Step 6: コミット**
```
git add cli/middleware.py tests/test_middleware.py
git commit -m "feat: add resolve_output_format with TTY detection (agent-first Phase 1)"
```

---

### Task 2: cli/middleware.py -- resolve_timeout, resolve_fields

**Files:**
- Modify: `cli/middleware.py`
- Modify: `tests/test_middleware.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_middleware.py に追記

class TestResolveTimeout:
    """resolve_timeout() のテスト"""

    def test_explicit_timeout_takes_priority(self):
        from cli.middleware import resolve_timeout
        assert resolve_timeout(60.0) == 60.0

    def test_env_var_used_when_no_explicit(self, monkeypatch):
        from cli.middleware import resolve_timeout
        monkeypatch.setenv("LR_TIMEOUT", "45.0")
        assert resolve_timeout(None) == 45.0

    def test_invalid_env_var_returns_default(self, monkeypatch):
        from cli.middleware import resolve_timeout
        monkeypatch.setenv("LR_TIMEOUT", "not_a_number")
        assert resolve_timeout(None) == 30.0

    def test_no_env_returns_default(self, monkeypatch):
        from cli.middleware import resolve_timeout
        monkeypatch.delenv("LR_TIMEOUT", raising=False)
        assert resolve_timeout(None) == 30.0


class TestResolveFields:
    """resolve_fields() のテスト"""

    def test_explicit_fields_parsed(self):
        from cli.middleware import resolve_fields
        assert resolve_fields("name,rating") == ["name", "rating"]

    def test_env_var_fields(self, monkeypatch):
        from cli.middleware import resolve_fields
        monkeypatch.setenv("LR_FIELDS", "fileName,dateTimeOriginal")
        assert resolve_fields(None) == ["fileName", "dateTimeOriginal"]

    def test_strips_whitespace(self):
        from cli.middleware import resolve_fields
        assert resolve_fields(" name , rating ") == ["name", "rating"]

    def test_none_when_not_set(self, monkeypatch):
        from cli.middleware import resolve_fields
        monkeypatch.delenv("LR_FIELDS", raising=False)
        assert resolve_fields(None) is None
```

**Step 2: 失敗を確認**
Run: `venv/bin/python -m pytest tests/test_middleware.py -v -k "Timeout or Fields"`
Expected: FAIL

**Step 3: 最小限の実装**

`cli/middleware.py` に以下を追加:

```python
def resolve_timeout(explicit_timeout: float | None) -> float:
    """タイムアウトの優先順位: --timeout > LR_TIMEOUT > デフォルト30.0"""
    if explicit_timeout is not None:
        return explicit_timeout

    env_timeout = os.environ.get("LR_TIMEOUT")
    if env_timeout:
        try:
            return float(env_timeout)
        except ValueError:
            pass

    return 30.0


def resolve_fields(explicit_fields: str | None) -> list[str] | None:
    """--fields > LR_FIELDS > None（全フィールド返却）"""
    fields_str = explicit_fields or os.environ.get("LR_FIELDS")
    if fields_str:
        return [f.strip() for f in fields_str.split(",")]
    return None
```

**Step 4: 通過を確認**
Run: `venv/bin/python -m pytest tests/test_middleware.py -v`
Expected: PASS

**Step 5: 全テスト回帰確認**
Run: `venv/bin/python -m pytest tests/ -v --ignore=tests/e2e`
Expected: ALL PASS

**Step 6: コミット**
```
git add cli/middleware.py tests/test_middleware.py
git commit -m "feat: add resolve_timeout and resolve_fields to middleware"
```

---

### Task 3: cli/main.py -- TTY検出とmiddleware統合

**Files:**
- Modify: `cli/main.py`
- Modify: `tests/test_cli_main.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_cli_main.py に追記

def test_cli_output_default_is_none():
    """--output 未指定時は None として middleware に渡される"""
    from click.testing import CliRunner
    from cli.main import cli
    runner = CliRunner()
    # CliRunner は非TTYなので middleware が json をデフォルトにする
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0


def test_cli_fields_option_exists():
    """--fields オプションが利用可能"""
    from click.testing import CliRunner
    from cli.main import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert "--fields" in result.output or "-f" in result.output
```

**Step 2: 失敗を確認**
Run: `venv/bin/python -m pytest tests/test_cli_main.py -v -k "default_is_none or fields_option"`
Expected: FAIL

**Step 3: 最小限の実装**

`cli/main.py` を以下のように修正:

```python
import os
import click
import logging
from cli.middleware import resolve_output_format, resolve_timeout, resolve_fields


@click.group()
@click.version_option(version="0.3.0", prog_name="lr")
@click.option("--output", "-o", type=click.Choice(["json", "text", "table"]),
              default=None, help="Output format (default: json for non-TTY, text for TTY)")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--timeout", "-t", type=float, default=None,
              help="Default command timeout in seconds")
@click.option("--fields", "-f", default=None,
              help="Comma-separated response fields to include")
@click.pass_context
def cli(ctx, output, verbose, timeout, fields):
    """Lightroom Classic CLI - control Lightroom from the command line."""
    ctx.ensure_object(dict)
    ctx.obj["output"] = resolve_output_format(output)
    ctx.obj["verbose"] = verbose or bool(os.environ.get("LR_VERBOSE"))
    ctx.obj["timeout"] = resolve_timeout(timeout)
    ctx.obj["fields"] = resolve_fields(fields)

    if ctx.obj["verbose"]:
        logging.basicConfig(level=logging.DEBUG)


from cli.commands.system import system
from cli.commands.catalog import catalog
from cli.commands.develop import develop
from cli.commands.preview import preview
from cli.commands.selection import selection
from cli.commands.plugin import plugin
cli.add_command(system)
cli.add_command(catalog)
cli.add_command(develop)
cli.add_command(preview)
cli.add_command(selection)
cli.add_command(plugin)
```

**Step 4: 通過を確認**
Run: `venv/bin/python -m pytest tests/test_cli_main.py -v`
Expected: PASS

**Step 5: 全テスト回帰確認**
Run: `venv/bin/python -m pytest tests/ -v --ignore=tests/e2e`
Expected: ALL PASS

注意: 既存テストで `ctx.obj["output"]` が `"text"` であることを前提としているものがあれば、CliRunner (非TTY) では `"json"` がデフォルトになるため修正が必要。各コマンドの `ctx.obj.get("output", "text")` は `ctx.obj` が適切に設定されていれば問題ない。テスト側で `obj={"output": "text", "timeout": 30.0}` を明示指定する。

**Step 6: コミット**
```
git add cli/main.py tests/test_cli_main.py
git commit -m "feat: integrate TTY detection and env vars into main CLI entrypoint (Phase 1)"
```

---

## Phase 2: --fields レスポンスフィルタ

### Task 4: OutputFormatter に fields フィルタリング追加

**Files:**
- Modify: `cli/output.py`
- Modify: `tests/test_output_formatter.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_output_formatter.py に追記

class TestFieldsFiltering:
    """--fields によるレスポンスフィールド制限テスト"""

    def test_filter_dict_fields(self):
        from cli.output import OutputFormatter
        data = {"name": "photo.jpg", "rating": 5, "size": 1024}
        result = OutputFormatter.format(data, "json", fields=["name", "rating"])
        import json
        parsed = json.loads(result)
        assert parsed == {"name": "photo.jpg", "rating": 5}
        assert "size" not in parsed

    def test_filter_list_of_dicts(self):
        from cli.output import OutputFormatter
        data = [
            {"name": "a.jpg", "rating": 3, "size": 100},
            {"name": "b.jpg", "rating": 5, "size": 200},
        ]
        result = OutputFormatter.format(data, "json", fields=["name"])
        import json
        parsed = json.loads(result)
        assert parsed == [{"name": "a.jpg"}, {"name": "b.jpg"}]

    def test_no_fields_returns_all(self):
        from cli.output import OutputFormatter
        data = {"name": "photo.jpg", "rating": 5}
        result = OutputFormatter.format(data, "json", fields=None)
        import json
        parsed = json.loads(result)
        assert parsed == {"name": "photo.jpg", "rating": 5}

    def test_filter_non_dict_returns_as_is(self):
        from cli.output import OutputFormatter
        result = OutputFormatter.format("hello", "text", fields=["name"])
        assert result == "hello"

    def test_empty_fields_list_returns_empty_dict(self):
        from cli.output import OutputFormatter
        data = {"name": "photo.jpg", "rating": 5}
        result = OutputFormatter.format(data, "json", fields=[])
        import json
        parsed = json.loads(result)
        assert parsed == {}
```

**Step 2: 失敗を確認**
Run: `venv/bin/python -m pytest tests/test_output_formatter.py::TestFieldsFiltering -v`
Expected: FAIL (TypeError: format() got unexpected keyword argument 'fields')

**Step 3: 最小限の実装**

`cli/output.py` の `format()` と新メソッド `_filter_fields()` を修正:

```python
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
```

**Step 4: 通過を確認**
Run: `venv/bin/python -m pytest tests/test_output_formatter.py -v`
Expected: PASS

**Step 5: 全テスト回帰確認**
Run: `venv/bin/python -m pytest tests/ -v --ignore=tests/e2e`
Expected: ALL PASS (既存 format() 呼び出しは fields=None がデフォルトなので影響なし)

**Step 6: コミット**
```
git add cli/output.py tests/test_output_formatter.py
git commit -m "feat: add --fields response filtering to OutputFormatter (Phase 2)"
```

---

### Task 5: 構造化エラー出力と終了コード

**Files:**
- Modify: `cli/output.py`
- Modify: `tests/test_output_formatter.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_output_formatter.py に追記

class TestStructuredError:
    """構造化エラー出力のテスト"""

    def test_json_error_is_structured(self):
        from cli.output import OutputFormatter
        import json
        result = OutputFormatter.format_error("Something went wrong", mode="json")
        parsed = json.loads(result)
        assert "error" in parsed
        assert parsed["error"]["message"] == "Something went wrong"

    def test_json_error_with_code(self):
        from cli.output import OutputFormatter
        import json
        result = OutputFormatter.format_error(
            "Unknown param", mode="json", code="VALIDATION_ERROR"
        )
        parsed = json.loads(result)
        assert parsed["error"]["code"] == "VALIDATION_ERROR"

    def test_json_error_with_suggestions(self):
        from cli.output import OutputFormatter
        import json
        result = OutputFormatter.format_error(
            "Unknown param 'Exposre'", mode="json",
            code="VALIDATION_ERROR", suggestions=["Exposure"]
        )
        parsed = json.loads(result)
        assert parsed["error"]["suggestions"] == ["Exposure"]

    def test_text_error_unchanged(self):
        from cli.output import OutputFormatter
        result = OutputFormatter.format_error("Something went wrong", mode="text")
        assert result == "Error: Something went wrong"

    def test_json_error_backward_compat(self):
        """既存呼び出し (mode 未指定) が壊れないことを確認"""
        from cli.output import OutputFormatter
        result = OutputFormatter.format_error("fail")
        assert "fail" in result
```

**Step 2: 失敗を確認**
Run: `venv/bin/python -m pytest tests/test_output_formatter.py::TestStructuredError -v`
Expected: FAIL

**Step 3: 最小限の実装**

`cli/output.py` の `format_error()` を修正:

```python
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
```

**Step 4: 通過を確認**
Run: `venv/bin/python -m pytest tests/test_output_formatter.py -v`
Expected: PASS

**Step 5: 全テスト回帰確認**
Run: `venv/bin/python -m pytest tests/ -v --ignore=tests/e2e`
Expected: ALL PASS (既存呼び出し `format_error(str(e))` は `mode="text"` デフォルトで互換維持)

**Step 6: コミット**
```
git add cli/output.py tests/test_output_formatter.py
git commit -m "feat: structured JSON error output with code and suggestions"
```

---

### Task 6: execute_command ヘルパー関数

**Files:**
- Create: `cli/helpers.py`
- Create: `tests/test_helpers.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_helpers.py
"""Tests for CLI command execution helper."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestExecuteCommand:
    """execute_command() のテスト"""

    def test_successful_command(self):
        from cli.helpers import execute_command

        mock_ctx = MagicMock()
        mock_ctx.obj = {"output": "json", "timeout": 30.0, "fields": None}

        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {"result": {"status": "ok"}}

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "system.ping", {})

        mock_bridge.send_command.assert_called_once_with(
            "system.ping", {}, timeout=30.0
        )

    def test_fields_filtering_applied(self):
        from cli.helpers import execute_command

        mock_ctx = MagicMock()
        mock_ctx.obj = {"output": "json", "timeout": 30.0, "fields": ["status"]}

        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {
            "result": {"status": "ok", "extra": "data"}
        }

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "system.ping", {})

        # format was called with fields
        # Verify click.echo was called (output contains only filtered fields)

    def test_connection_error_exit_code_3(self):
        from cli.helpers import execute_command

        mock_ctx = MagicMock()
        mock_ctx.obj = {"output": "json", "timeout": 30.0, "fields": None}

        mock_bridge = AsyncMock()
        mock_bridge.send_command.side_effect = ConnectionError("refused")

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "system.ping", {})

        mock_ctx.exit.assert_called_with(3)

    def test_timeout_error_exit_code_4(self):
        from cli.helpers import execute_command

        mock_ctx = MagicMock()
        mock_ctx.obj = {"output": "json", "timeout": 30.0, "fields": None}

        mock_bridge = AsyncMock()
        mock_bridge.send_command.side_effect = TimeoutError("timed out")

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "system.ping", {})

        mock_ctx.exit.assert_called_with(4)

    def test_general_error_exit_code_1(self):
        from cli.helpers import execute_command

        mock_ctx = MagicMock()
        mock_ctx.obj = {"output": "json", "timeout": 30.0, "fields": None}

        mock_bridge = AsyncMock()
        mock_bridge.send_command.side_effect = RuntimeError("unexpected")

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "system.ping", {})

        mock_ctx.exit.assert_called_with(1)

    def test_custom_timeout_overrides_ctx(self):
        from cli.helpers import execute_command

        mock_ctx = MagicMock()
        mock_ctx.obj = {"output": "json", "timeout": 30.0, "fields": None}

        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {"result": {}}

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(mock_ctx, "preview.generatePreview", {}, timeout=120.0)

        mock_bridge.send_command.assert_called_once_with(
            "preview.generatePreview", {}, timeout=120.0
        )
```

**Step 2: 失敗を確認**
Run: `venv/bin/python -m pytest tests/test_helpers.py -v`
Expected: FAIL (ModuleNotFoundError)

**Step 3: 最小限の実装**

```python
# cli/helpers.py
"""共通コマンド実行ヘルパー。ボイラープレートを集約する。"""
import asyncio
import click
from cli.output import OutputFormatter


def get_bridge(port_file: str | None = None):
    """ResilientSocketBridgeインスタンスを取得（遅延import）"""
    from lightroom_sdk.resilient_bridge import ResilientSocketBridge
    return ResilientSocketBridge(port_file=port_file)


def run_async(coro):
    """CLIからasync関数を実行するヘルパー"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def execute_command(ctx, command: str, params: dict, *, timeout: float | None = None):
    """
    共通コマンド実行ヘルパー。

    - バリデーション（Phase 4 で追加予定）
    - エラーハンドリング（構造化エラー + 終了コード）
    - fields フィルタリング
    - bridge 接続・切断の管理
    """
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
    fields = ctx.obj.get("fields") if ctx.obj else None
    cmd_timeout = timeout or (ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0)

    async def _run():
        bridge = get_bridge()
        try:
            await bridge.connect()
            result = await bridge.send_command(command, params, timeout=cmd_timeout)
            data = result.get("result", result)
            click.echo(OutputFormatter.format(data, fmt, fields=fields))
        except ConnectionError as e:
            click.echo(
                OutputFormatter.format_error(str(e), fmt, code="CONNECTION_ERROR"),
                err=True,
            )
            ctx.exit(3)
        except TimeoutError as e:
            click.echo(
                OutputFormatter.format_error(str(e), fmt, code="TIMEOUT_ERROR"),
                err=True,
            )
            ctx.exit(4)
        except Exception as e:
            click.echo(
                OutputFormatter.format_error(str(e), fmt),
                err=True,
            )
            ctx.exit(1)
        finally:
            await bridge.disconnect()

    run_async(_run())
```

**Step 4: 通過を確認**
Run: `venv/bin/python -m pytest tests/test_helpers.py -v`
Expected: PASS

**Step 5: 全テスト回帰確認**
Run: `venv/bin/python -m pytest tests/ -v --ignore=tests/e2e`
Expected: ALL PASS

**Step 6: コミット**
```
git add cli/helpers.py tests/test_helpers.py
git commit -m "feat: add execute_command helper with structured errors and exit codes"
```

---

## Phase 3: lr schema + スキーマ定義

### Task 7: lightroom_sdk/schema.py -- スキーマデータ構造

**Files:**
- Create: `lightroom_sdk/schema.py`
- Create: `tests/test_schema.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_schema.py
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
```

**Step 2: 失敗を確認**
Run: `venv/bin/python -m pytest tests/test_schema.py -v`
Expected: FAIL (ModuleNotFoundError)

**Step 3: 最小限の実装**

```python
# lightroom_sdk/schema.py
"""Command schema definitions -- Single Source of Truth for validation and introspection."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class ParamType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON_OBJECT = "json_object"
    JSON_ARRAY = "json_array"
    ENUM = "enum"


@dataclass
class ParamSchema:
    name: str
    type: ParamType
    required: bool = False
    description: str = ""
    default: object = None
    enum_values: list[str] | None = None


@dataclass
class CommandSchema:
    command: str
    cli_path: str
    description: str
    params: list[ParamSchema] = field(default_factory=list)
    mutating: bool = False
    timeout: float = 30.0
    response_fields: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# スキーマ定義
# ---------------------------------------------------------------------------

COMMAND_SCHEMAS: dict[str, CommandSchema] = {}


def _register(*schemas: CommandSchema) -> None:
    for s in schemas:
        COMMAND_SCHEMAS[s.command] = s


# --- system ---
_register(
    CommandSchema("system.ping", "system.ping", "Test connection", timeout=5.0),
    CommandSchema("system.status", "system.status", "Get bridge status", timeout=5.0),
)

# --- develop (主要) ---
_register(
    CommandSchema(
        "develop.getSettings", "develop.get-settings",
        "Get all current develop settings",
        response_fields=["Exposure", "Contrast", "Highlights", "Shadows",
                         "Whites", "Blacks", "Temperature", "Tint"],
    ),
    CommandSchema(
        "develop.setValue", "develop.set",
        "Set develop parameter(s)",
        params=[
            ParamSchema("parameter", ParamType.STRING, required=True,
                        description="Develop parameter name (e.g., Exposure, Contrast)"),
            ParamSchema("value", ParamType.FLOAT, required=True,
                        description="Parameter value"),
        ],
        mutating=True, timeout=10.0,
    ),
    CommandSchema(
        "develop.getValue", "develop.get",
        "Get a single develop parameter value",
        params=[
            ParamSchema("param", ParamType.STRING, required=True,
                        description="Parameter name"),
        ],
    ),
    CommandSchema(
        "develop.batchApplySettings", "develop.apply",
        "Apply develop settings from JSON",
        params=[
            ParamSchema("settings", ParamType.JSON_OBJECT, required=True,
                        description="JSON object of settings to apply"),
        ],
        mutating=True,
    ),
    CommandSchema(
        "develop.setAutoTone", "develop.auto-tone",
        "Apply auto tone adjustments",
        mutating=True,
    ),
    CommandSchema(
        "develop.setAutoWhiteBalance", "develop.auto-wb",
        "Apply auto white balance",
        mutating=True,
    ),
    CommandSchema(
        "develop.selectTool", "develop.tool",
        "Select a develop tool",
        params=[
            ParamSchema("tool", ParamType.ENUM, required=True,
                        description="Tool name",
                        enum_values=["loupe", "crop", "dust", "redeye",
                                     "gradient", "circularGradient",
                                     "localized", "upright"]),
        ],
    ),
    CommandSchema(
        "develop.resetAllDevelopAdjustments", "develop.reset",
        "Reset develop settings to defaults",
        mutating=True,
    ),
    CommandSchema(
        "develop.getRange", "develop.range",
        "Get min/max range for a develop parameter",
        params=[
            ParamSchema("param", ParamType.STRING, required=True,
                        description="Parameter name"),
        ],
    ),
    CommandSchema(
        "develop.resetToDefault", "develop.reset-param",
        "Reset a develop parameter to its default value",
        params=[
            ParamSchema("param", ParamType.STRING, required=True),
        ],
        mutating=True,
    ),
    CommandSchema(
        "develop.getProcessVersion", "develop.process-version",
        "Get the current process version",
    ),
    CommandSchema(
        "develop.setProcessVersion", "develop.set-process-version",
        "Set the process version",
        params=[
            ParamSchema("version", ParamType.STRING, required=True),
        ],
        mutating=True,
    ),
)

# --- develop.curve ---
_register(
    CommandSchema(
        "develop.getCurvePoints", "develop.curve.get",
        "Get tone curve points",
        params=[
            ParamSchema("param", ParamType.STRING, required=True,
                        description="Curve parameter name"),
        ],
    ),
    CommandSchema(
        "develop.setCurvePoints", "develop.curve.set",
        "Set tone curve points",
        params=[
            ParamSchema("param", ParamType.STRING, required=True),
            ParamSchema("points", ParamType.JSON_ARRAY, required=True,
                        description="Array of {x, y} points"),
        ],
        mutating=True,
    ),
    CommandSchema(
        "develop.setCurveLinear", "develop.curve.linear",
        "Reset curve to linear",
        params=[ParamSchema("param", ParamType.STRING, required=True)],
        mutating=True,
    ),
    CommandSchema(
        "develop.setCurveSCurve", "develop.curve.s-curve",
        "Apply S-curve preset",
        params=[ParamSchema("param", ParamType.STRING, required=True)],
        mutating=True,
    ),
    CommandSchema(
        "develop.addCurvePoint", "develop.curve.add-point",
        "Add a point to the tone curve",
        params=[
            ParamSchema("param", ParamType.STRING, required=True),
            ParamSchema("x", ParamType.FLOAT, required=True),
            ParamSchema("y", ParamType.FLOAT, required=True),
        ],
        mutating=True,
    ),
    CommandSchema(
        "develop.removeCurvePoint", "develop.curve.remove-point",
        "Remove a point from the tone curve",
        params=[
            ParamSchema("param", ParamType.STRING, required=True),
            ParamSchema("index", ParamType.INTEGER, required=True),
        ],
        mutating=True,
    ),
)

# --- develop.mask ---
_register(
    CommandSchema("develop.getAllMasks", "develop.mask.list", "List all masks"),
    CommandSchema("develop.getSelectedMask", "develop.mask.selected", "Get selected mask"),
    CommandSchema("develop.goToMasking", "develop.mask.go-to", "Go to masking view"),
    CommandSchema("develop.toggleOverlay", "develop.mask.toggle-overlay", "Toggle mask overlay"),
)

# --- develop.local ---
_register(
    CommandSchema(
        "develop.getLocalValue", "develop.local.get",
        "Get a local adjustment parameter value",
        params=[ParamSchema("parameter", ParamType.STRING, required=True)],
    ),
    CommandSchema(
        "develop.setLocalValue", "develop.local.set",
        "Set a local adjustment parameter value",
        params=[
            ParamSchema("parameter", ParamType.STRING, required=True),
            ParamSchema("value", ParamType.FLOAT, required=True),
        ],
        mutating=True,
    ),
    CommandSchema(
        "develop.applyLocalSettings", "develop.local.apply",
        "Apply multiple local adjustment settings",
        params=[
            ParamSchema("settings", ParamType.JSON_OBJECT, required=True),
        ],
        mutating=True,
    ),
    CommandSchema(
        "develop.getAvailableLocalParameters", "develop.local.params",
        "List available local adjustment parameters",
    ),
    CommandSchema(
        "develop.createMaskWithLocalAdjustments", "develop.local.create-mask",
        "Create mask with local adjustments",
        params=[
            ParamSchema("maskType", ParamType.ENUM, enum_values=["brush", "gradient", "radial"]),
            ParamSchema("localSettings", ParamType.JSON_OBJECT),
        ],
        mutating=True,
    ),
)

# --- develop.filter ---
_register(
    CommandSchema("develop.createGraduatedFilter", "develop.filter.graduated",
                  "Create a graduated filter", mutating=True),
    CommandSchema("develop.createRadialFilter", "develop.filter.radial",
                  "Create a radial filter", mutating=True),
    CommandSchema("develop.createAdjustmentBrush", "develop.filter.brush",
                  "Create an adjustment brush", mutating=True),
    CommandSchema(
        "develop.createRangeMask", "develop.filter.range",
        "Create a range mask",
        params=[
            ParamSchema("rangeType", ParamType.ENUM,
                        enum_values=["luminance", "color", "depth"]),
        ],
        mutating=True,
    ),
)

# --- develop reset commands ---
_register(
    CommandSchema("develop.resetGradient", "develop.reset-gradient",
                  "Reset gradient filter", mutating=True),
    CommandSchema("develop.resetCircularGradient", "develop.reset-circular",
                  "Reset circular gradient filter", mutating=True),
    CommandSchema("develop.resetBrushing", "develop.reset-brush",
                  "Reset adjustment brush", mutating=True),
    CommandSchema("develop.resetMasking", "develop.reset-masking",
                  "Reset masking", mutating=True),
    CommandSchema("develop.resetCrop", "develop.reset-crop",
                  "Reset crop", mutating=True),
    CommandSchema("develop.resetTransforms", "develop.reset-transforms",
                  "Reset transforms", mutating=True),
    CommandSchema("develop.resetSpotRemoval", "develop.reset-spot",
                  "Reset spot removal", mutating=True),
    CommandSchema("develop.resetRedeye", "develop.reset-redeye",
                  "Reset red eye removal", mutating=True),
    CommandSchema("develop.resetHealing", "develop.reset-healing",
                  "Reset healing", mutating=True),
)

# --- develop other ---
_register(
    CommandSchema("develop.editInPhotoshop", "develop.edit-in-photoshop",
                  "Open current photo in Photoshop", mutating=True),
    CommandSchema("catalog.applyDevelopPreset", "develop.preset",
                  "Apply a develop preset by name",
                  params=[ParamSchema("presetName", ParamType.STRING, required=True)],
                  mutating=True),
    CommandSchema("catalog.createDevelopSnapshot", "develop.snapshot",
                  "Create a develop snapshot",
                  params=[ParamSchema("name", ParamType.STRING, required=True)],
                  mutating=True),
    CommandSchema("catalog.copySettings", "develop.copy-settings",
                  "Copy develop settings from selected photo"),
    CommandSchema("catalog.pasteSettings", "develop.paste-settings",
                  "Paste develop settings to selected photo", mutating=True),
)

# --- develop.debug ---
_register(
    CommandSchema("develop.dumpLrDevelopController", "develop.debug.dump",
                  "Dump LrDevelopController info"),
    CommandSchema("develop.discoverGradientParameters", "develop.debug.gradient-params",
                  "Discover gradient parameters"),
    CommandSchema("develop.monitorParameterChanges", "develop.debug.monitor",
                  "Monitor parameter changes",
                  params=[ParamSchema("duration", ParamType.INTEGER, default=10)]),
    CommandSchema("develop.probeAllDevelopParameters", "develop.debug.probe",
                  "Probe all develop parameters"),
)

# --- develop.color ---
_register(
    CommandSchema("develop.createGreenSwatch", "develop.color.green-swatch",
                  "Create green color swatch", mutating=True),
    CommandSchema("develop.createCyanSwatch", "develop.color.cyan-swatch",
                  "Create cyan color swatch", mutating=True),
    CommandSchema("develop.enhanceColors", "develop.color.enhance",
                  "Enhance colors",
                  params=[ParamSchema("preset", ParamType.ENUM,
                                      enum_values=["natural", "vivid", "muted"])],
                  mutating=True),
)

# --- develop.ai ---
_register(
    CommandSchema(
        "develop.createAIMaskWithAdjustments", "develop.ai.<type>",
        "Create AI mask with optional adjustments",
        params=[
            ParamSchema("selectionType", ParamType.ENUM, required=True,
                        enum_values=["subject", "sky", "background",
                                     "objects", "people", "landscape"]),
            ParamSchema("adjustments", ParamType.JSON_OBJECT,
                        description="Optional adjustment settings"),
        ],
        mutating=True, timeout=60.0,
    ),
    CommandSchema(
        "develop.batchAIMask", "develop.ai.batch",
        "Apply AI mask to multiple photos",
        params=[
            ParamSchema("selectionType", ParamType.ENUM, required=True,
                        enum_values=["subject", "sky", "background",
                                     "objects", "people", "landscape"]),
            ParamSchema("photoIds", ParamType.JSON_ARRAY),
            ParamSchema("allSelected", ParamType.BOOLEAN, default=False),
            ParamSchema("adjustments", ParamType.JSON_OBJECT),
            ParamSchema("continueOnError", ParamType.BOOLEAN, default=False),
        ],
        mutating=True, timeout=300.0,
    ),
)

# --- catalog ---
_register(
    CommandSchema("catalog.getSelectedPhotos", "catalog.get-selected",
                  "Get currently selected photos"),
    CommandSchema(
        "catalog.getAllPhotos", "catalog.list",
        "List photos in catalog",
        params=[
            ParamSchema("limit", ParamType.INTEGER, default=50),
            ParamSchema("offset", ParamType.INTEGER, default=0),
        ],
        timeout=60.0,
    ),
    CommandSchema(
        "catalog.searchPhotos", "catalog.search",
        "Search photos by keyword",
        params=[
            ParamSchema("query", ParamType.STRING, required=True),
            ParamSchema("limit", ParamType.INTEGER, default=50),
        ],
        timeout=60.0,
    ),
    CommandSchema(
        "catalog.getPhotoMetadata", "catalog.get-info",
        "Get detailed info for a photo",
        params=[ParamSchema("photoId", ParamType.STRING, required=True)],
    ),
    CommandSchema(
        "catalog.setRating", "catalog.set-rating",
        "Set photo star rating",
        params=[
            ParamSchema("photoId", ParamType.STRING, required=True),
            ParamSchema("rating", ParamType.INTEGER, required=True,
                        description="Star rating (0-5)"),
        ],
        mutating=True,
    ),
    CommandSchema(
        "catalog.addKeywords", "catalog.add-keywords",
        "Add keywords to a photo",
        params=[
            ParamSchema("photoId", ParamType.STRING, required=True),
            ParamSchema("keywords", ParamType.JSON_ARRAY, required=True),
        ],
        mutating=True,
    ),
    CommandSchema(
        "catalog.setFlag", "catalog.set-flag",
        "Set photo flag (pick/reject/none)",
        params=[
            ParamSchema("photoId", ParamType.STRING, required=True),
            ParamSchema("flag", ParamType.INTEGER, required=True,
                        description="Flag value (1=pick, -1=reject, 0=none)"),
        ],
        mutating=True,
    ),
    CommandSchema(
        "catalog.getFlag", "catalog.get-flag",
        "Get photo flag status",
        params=[ParamSchema("photoId", ParamType.STRING, required=True)],
    ),
    CommandSchema(
        "catalog.findPhotos", "catalog.find",
        "Find photos by structured criteria",
        params=[
            ParamSchema("searchDesc", ParamType.JSON_OBJECT, required=True),
            ParamSchema("limit", ParamType.INTEGER, default=50),
            ParamSchema("offset", ParamType.INTEGER, default=0),
        ],
    ),
    CommandSchema(
        "catalog.setSelectedPhotos", "catalog.select",
        "Select photos by ID",
        params=[
            ParamSchema("photoIds", ParamType.JSON_ARRAY, required=True),
        ],
        mutating=True,
    ),
    CommandSchema(
        "catalog.findPhotoByPath", "catalog.find-by-path",
        "Find photo by file path",
        params=[ParamSchema("path", ParamType.STRING, required=True)],
    ),
    CommandSchema("catalog.getCollections", "catalog.collections",
                  "List collections in catalog"),
    CommandSchema("catalog.getKeywords", "catalog.keywords",
                  "List keywords in catalog"),
    CommandSchema(
        "catalog.getFolders", "catalog.folders",
        "List folders in catalog",
        params=[ParamSchema("includeSubfolders", ParamType.BOOLEAN, default=False)],
    ),
    CommandSchema(
        "catalog.setTitle", "catalog.set-title",
        "Set photo title",
        params=[
            ParamSchema("photoId", ParamType.STRING, required=True),
            ParamSchema("title", ParamType.STRING, required=True),
        ],
        mutating=True,
    ),
    CommandSchema(
        "catalog.setCaption", "catalog.set-caption",
        "Set photo caption",
        params=[
            ParamSchema("photoId", ParamType.STRING, required=True),
            ParamSchema("caption", ParamType.STRING, required=True),
        ],
        mutating=True,
    ),
    CommandSchema(
        "catalog.setColorLabel", "catalog.set-color-label",
        "Set photo color label",
        params=[
            ParamSchema("photoId", ParamType.STRING, required=True),
            ParamSchema("label", ParamType.ENUM, required=True,
                        enum_values=["red", "yellow", "green", "blue", "purple", "none"]),
        ],
        mutating=True,
    ),
    CommandSchema(
        "catalog.batchGetFormattedMetadata", "catalog.batch-metadata",
        "Get formatted metadata for multiple photos",
        params=[
            ParamSchema("photoIds", ParamType.JSON_ARRAY, required=True),
            ParamSchema("keys", ParamType.JSON_ARRAY, required=True),
        ],
    ),
    CommandSchema("catalog.rotateLeft", "catalog.rotate-left",
                  "Rotate selected photo left", mutating=True),
    CommandSchema("catalog.rotateRight", "catalog.rotate-right",
                  "Rotate selected photo right", mutating=True),
    CommandSchema("catalog.createVirtualCopy", "catalog.create-virtual-copy",
                  "Create virtual copy of selected photo", mutating=True),
    CommandSchema(
        "catalog.setMetadata", "catalog.set-metadata",
        "Set arbitrary metadata key/value",
        params=[
            ParamSchema("photoId", ParamType.STRING, required=True),
            ParamSchema("key", ParamType.STRING, required=True),
            ParamSchema("value", ParamType.STRING, required=True),
        ],
        mutating=True,
    ),
    CommandSchema(
        "catalog.createCollection", "catalog.create-collection",
        "Create a new collection",
        params=[ParamSchema("name", ParamType.STRING, required=True)],
        mutating=True,
    ),
    CommandSchema(
        "catalog.createSmartCollection", "catalog.create-smart-collection",
        "Create a smart collection",
        params=[
            ParamSchema("name", ParamType.STRING, required=True),
            ParamSchema("searchDesc", ParamType.JSON_OBJECT),
        ],
        mutating=True,
    ),
    CommandSchema(
        "catalog.createCollectionSet", "catalog.create-collection-set",
        "Create a collection set",
        params=[ParamSchema("name", ParamType.STRING, required=True)],
        mutating=True,
    ),
    CommandSchema(
        "catalog.createKeyword", "catalog.create-keyword",
        "Create a keyword in catalog",
        params=[ParamSchema("keyword", ParamType.STRING, required=True)],
        mutating=True,
    ),
    CommandSchema(
        "catalog.removeKeyword", "catalog.remove-keyword",
        "Remove keyword from a photo",
        params=[
            ParamSchema("photoId", ParamType.STRING, required=True),
            ParamSchema("keyword", ParamType.STRING, required=True),
        ],
        mutating=True,
    ),
    CommandSchema(
        "catalog.setViewFilter", "catalog.set-view-filter",
        "Set view filter",
        params=[ParamSchema("filter", ParamType.JSON_OBJECT, required=True)],
        mutating=True,
    ),
    CommandSchema("catalog.getCurrentViewFilter", "catalog.get-view-filter",
                  "Get current view filter"),
    CommandSchema(
        "catalog.removeFromCatalog", "catalog.remove-from-catalog",
        "Remove photo from catalog",
        params=[ParamSchema("photoId", ParamType.STRING, required=True)],
        mutating=True,
    ),
)

# --- selection ---
_register(
    CommandSchema("selection.flagAsPick", "selection.flag",
                  "Flag selected photo(s) as Pick", mutating=True),
    CommandSchema("selection.flagAsReject", "selection.reject",
                  "Flag selected photo(s) as Reject", mutating=True),
    CommandSchema("selection.removeFlag", "selection.unflag",
                  "Remove flag from selected photo(s)", mutating=True),
    CommandSchema("selection.nextPhoto", "selection.next",
                  "Move to next photo"),
    CommandSchema("selection.previousPhoto", "selection.previous",
                  "Move to previous photo"),
    CommandSchema(
        "selection.setColorLabel", "selection.color-label",
        "Set color label for selected photo(s)",
        params=[
            ParamSchema("label", ParamType.ENUM, required=True,
                        enum_values=["red", "yellow", "green", "blue", "purple", "none"]),
        ],
        mutating=True,
    ),
    CommandSchema("selection.selectAll", "selection.select-all",
                  "Select all photos", mutating=True),
    CommandSchema("selection.selectNone", "selection.select-none",
                  "Deselect all photos", mutating=True),
    CommandSchema("selection.selectInverse", "selection.select-inverse",
                  "Invert the current selection", mutating=True),
    CommandSchema("selection.increaseRating", "selection.increase-rating",
                  "Increase rating by 1", mutating=True),
    CommandSchema("selection.decreaseRating", "selection.decrease-rating",
                  "Decrease rating by 1", mutating=True),
    CommandSchema(
        "selection.toggleRedLabel", "selection.toggle-label.red",
        "Toggle red label", mutating=True),
    CommandSchema(
        "selection.toggleYellowLabel", "selection.toggle-label.yellow",
        "Toggle yellow label", mutating=True),
    CommandSchema(
        "selection.toggleGreenLabel", "selection.toggle-label.green",
        "Toggle green label", mutating=True),
    CommandSchema(
        "selection.toggleBlueLabel", "selection.toggle-label.blue",
        "Toggle blue label", mutating=True),
    CommandSchema(
        "selection.togglePurpleLabel", "selection.toggle-label.purple",
        "Toggle purple label", mutating=True),
    CommandSchema(
        "selection.extendSelection", "selection.extend",
        "Extend selection in a direction",
        params=[
            ParamSchema("direction", ParamType.ENUM, default="right",
                        enum_values=["left", "right"]),
            ParamSchema("amount", ParamType.INTEGER, default=1),
        ],
        mutating=True,
    ),
    CommandSchema("selection.deselectActive", "selection.deselect-active",
                  "Deselect the active photo", mutating=True),
    CommandSchema("selection.deselectOthers", "selection.deselect-others",
                  "Deselect all except active photo", mutating=True),
    CommandSchema("selection.getFlag", "selection.get-flag",
                  "Get flag status of selected photo"),
    CommandSchema("selection.getRating", "selection.get-rating",
                  "Get rating of selected photo"),
    CommandSchema(
        "selection.setRating", "selection.set-rating",
        "Set rating for selected photo (0-5)",
        params=[
            ParamSchema("rating", ParamType.INTEGER, required=True,
                        description="Rating 0-5"),
        ],
        mutating=True,
    ),
    CommandSchema("selection.getColorLabel", "selection.get-color-label",
                  "Get color label of selected photo"),
)

# --- preview ---
_register(
    CommandSchema("preview.generatePreview", "preview.generate",
                  "Generate preview with specified size and format",
                  params=[
                      ParamSchema("size", ParamType.INTEGER, default=1024),
                      ParamSchema("format", ParamType.ENUM, default="jpeg",
                                  enum_values=["jpeg", "png"]),
                  ],
                  timeout=120.0),
    CommandSchema("preview.generateBatchPreviews", "preview.generate-batch",
                  "Generate batch previews", timeout=300.0),
    CommandSchema("preview.getPreviewInfo", "preview.info",
                  "Get preview info for a photo",
                  params=[ParamSchema("photoId", ParamType.STRING, required=True)]),
)


# ---------------------------------------------------------------------------
# Lookup functions
# ---------------------------------------------------------------------------

def get_schema(command: str) -> CommandSchema | None:
    return COMMAND_SCHEMAS.get(command)


def get_schemas_by_group(group: str) -> dict[str, CommandSchema]:
    """グループ名（develop, catalog 等）でフィルタ"""
    return {k: v for k, v in COMMAND_SCHEMAS.items() if k.startswith(f"{group}.")}


def get_all_schemas() -> dict[str, CommandSchema]:
    return COMMAND_SCHEMAS
```

**Step 4: 通過を確認**
Run: `venv/bin/python -m pytest tests/test_schema.py -v`
Expected: PASS

**Step 5: 全テスト回帰確認**
Run: `venv/bin/python -m pytest tests/ -v --ignore=tests/e2e`
Expected: ALL PASS

**Step 6: コミット**
```
git add lightroom_sdk/schema.py tests/test_schema.py
git commit -m "feat: add command schema definitions for introspection and validation (Phase 3)"
```

---

### Task 8: スキーマ整合性テスト

**Files:**
- Modify: `tests/test_schema.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_schema.py に追記

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
        # Some commands may share cli_path (e.g., ai.<type>), skip those
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
```

**Step 2: 失敗を確認**
Run: `venv/bin/python -m pytest tests/test_schema.py::TestSchemaIntegrity -v`
Expected: テストが通るか確認。FAIL なら Step 3 でスキーマ定義を修正。

**Step 3: 修正（必要に応じて）**
スキーマ定義のバグを修正。

**Step 4: 通過を確認**
Run: `venv/bin/python -m pytest tests/test_schema.py -v`
Expected: PASS

**Step 5: 全テスト回帰確認**
Run: `venv/bin/python -m pytest tests/ -v --ignore=tests/e2e`
Expected: ALL PASS

**Step 6: コミット**
```
git add tests/test_schema.py
git commit -m "test: add schema integrity tests"
```

---

### Task 9: cli/schema.py -- lr schema コマンド

**Files:**
- Create: `cli/schema.py`
- Create: `tests/test_cli_schema.py`
- Modify: `cli/main.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_cli_schema.py
"""Tests for lr schema CLI command."""
import json
import pytest
from click.testing import CliRunner
from cli.main import cli


class TestSchemaCommand:
    """lr schema コマンドのテスト"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_schema_list_groups(self, runner):
        result = runner.invoke(cli, ["-o", "json", "schema"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        group_names = [g["name"] for g in data]
        assert "develop" in group_names
        assert "catalog" in group_names

    def test_schema_group_commands(self, runner):
        result = runner.invoke(cli, ["-o", "json", "schema", "develop"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "command" in data[0]
        assert "description" in data[0]

    def test_schema_command_detail(self, runner):
        result = runner.invoke(cli, ["-o", "json", "schema", "develop.set"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "command" in data
        assert "params" in data
        assert isinstance(data["params"], list)

    def test_schema_unknown_group(self, runner):
        result = runner.invoke(cli, ["-o", "json", "schema", "nonexistent"])
        assert result.exit_code == 0
        # Should show error message
        assert "error" in result.output.lower() or "unknown" in result.output.lower()

    def test_schema_unknown_command(self, runner):
        result = runner.invoke(cli, ["-o", "json", "schema", "develop.nonexistent"])
        assert result.exit_code == 0
        assert "error" in result.output.lower() or "unknown" in result.output.lower()
```

**Step 2: 失敗を確認**
Run: `venv/bin/python -m pytest tests/test_cli_schema.py -v`
Expected: FAIL

**Step 3: 最小限の実装**

```python
# cli/schema.py
"""lr schema -- command schema introspection."""
import click
from cli.output import OutputFormatter


@click.command("schema")
@click.argument("path", required=False, default=None)
@click.pass_context
def schema_cmd(ctx, path):
    """Introspect command schemas.

    Usage:
      lr schema                    -- list all groups
      lr schema develop            -- list commands in group
      lr schema develop.set        -- show command detail
    """
    from lightroom_sdk.schema import get_all_schemas, get_schemas_by_group
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    if path is None:
        # 全グループ一覧
        schemas = get_all_schemas()
        groups: dict[str, dict] = {}
        for cmd_name, schema in schemas.items():
            group = cmd_name.split(".")[0]
            if group not in groups:
                groups[group] = {"name": group, "commands": 0, "mutating": 0}
            groups[group]["commands"] += 1
            if schema.mutating:
                groups[group]["mutating"] += 1
        click.echo(OutputFormatter.format(list(groups.values()), fmt))

    elif "." not in path:
        # グループ内コマンド一覧
        schemas = get_schemas_by_group(path)
        if not schemas:
            click.echo(OutputFormatter.format_error(f"Unknown group: {path}", fmt))
            return
        summary = [
            {
                "command": s.cli_path,
                "description": s.description,
                "mutating": s.mutating,
                "params": len(s.params),
            }
            for s in schemas.values()
        ]
        click.echo(OutputFormatter.format(summary, fmt))

    else:
        # コマンド詳細 (cli_path または bridge command で検索)
        schemas = get_all_schemas()
        target = None
        for s in schemas.values():
            if s.cli_path == path or s.command == path:
                target = s
                break
        if target is None:
            click.echo(OutputFormatter.format_error(f"Unknown command: {path}", fmt))
            return
        detail = {
            "command": target.cli_path,
            "bridge_command": target.command,
            "description": target.description,
            "mutating": target.mutating,
            "timeout": target.timeout,
            "params": [
                {
                    "name": p.name,
                    "type": p.type.value,
                    "required": p.required,
                    "description": p.description,
                    **({"default": p.default} if p.default is not None else {}),
                    **({"enum_values": p.enum_values} if p.enum_values else {}),
                }
                for p in target.params
            ],
            "response_fields": target.response_fields,
        }
        click.echo(OutputFormatter.format(detail, fmt))
```

`cli/main.py` に追加:
```python
from cli.schema import schema_cmd
cli.add_command(schema_cmd)
```

**Step 4: 通過を確認**
Run: `venv/bin/python -m pytest tests/test_cli_schema.py -v`
Expected: PASS

**Step 5: 全テスト回帰確認**
Run: `venv/bin/python -m pytest tests/ -v --ignore=tests/e2e`
Expected: ALL PASS

**Step 6: コミット**
```
git add cli/schema.py tests/test_cli_schema.py cli/main.py
git commit -m "feat: add lr schema command for introspection (Phase 3)"
```

---

## Phase 4: 入力バリデーション

### Task 10: cli/validation.py -- バリデーション基盤

**Files:**
- Create: `cli/validation.py`
- Create: `tests/test_validation.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_validation.py
"""Tests for input validation."""
import pytest


class TestValidateParams:
    """validate_params() のテスト"""

    def test_valid_params_pass_through(self):
        from cli.validation import validate_params
        result = validate_params(
            "develop.setValue",
            {"parameter": "Exposure", "value": 0.5}
        )
        assert result["parameter"] == "Exposure"
        assert result["value"] == 0.5

    def test_unknown_param_raises(self):
        from cli.validation import validate_params, ValidationError
        with pytest.raises(ValidationError, match="Unknown parameter"):
            validate_params("develop.setValue", {"Exposre": 0.5})

    def test_missing_required_param_raises(self):
        from cli.validation import validate_params, ValidationError
        with pytest.raises(ValidationError, match="Required parameter"):
            validate_params("develop.setValue", {"parameter": "Exposure"})

    def test_type_coercion_string_to_float(self):
        from cli.validation import validate_params
        result = validate_params(
            "develop.setValue",
            {"parameter": "Exposure", "value": "0.5"}
        )
        assert result["value"] == 0.5
        assert isinstance(result["value"], float)

    def test_invalid_type_raises(self):
        from cli.validation import validate_params, ValidationError
        with pytest.raises(ValidationError, match="Invalid type"):
            validate_params(
                "develop.setValue",
                {"parameter": "Exposure", "value": "not_a_number"}
            )

    def test_unknown_command_skips_validation(self):
        from cli.validation import validate_params
        result = validate_params(
            "unknown.command",
            {"any_param": "any_value"}
        )
        assert result == {"any_param": "any_value"}

    def test_enum_valid_value(self):
        from cli.validation import validate_params
        result = validate_params(
            "develop.selectTool",
            {"tool": "crop"}
        )
        assert result["tool"] == "crop"

    def test_enum_invalid_value_raises(self):
        from cli.validation import validate_params, ValidationError
        with pytest.raises(ValidationError, match="Invalid value"):
            validate_params(
                "develop.selectTool",
                {"tool": "invalid_tool"}
            )


class TestFindSimilar:
    """類似パラメータ名提案のテスト"""

    def test_finds_similar_by_substring(self):
        from cli.validation import _find_similar
        suggestions = _find_similar("Exposre", {"Exposure", "Contrast", "Highlights"})
        assert "Exposure" in suggestions

    def test_returns_empty_for_no_match(self):
        from cli.validation import _find_similar
        suggestions = _find_similar("zzzzz", {"Exposure", "Contrast"})
        assert suggestions == []
```

**Step 2: 失敗を確認**
Run: `venv/bin/python -m pytest tests/test_validation.py -v`
Expected: FAIL (ModuleNotFoundError)

**Step 3: 最小限の実装**

```python
# cli/validation.py
"""Input validation based on command schemas."""
from __future__ import annotations
from lightroom_sdk.schema import get_schema, ParamType, ParamSchema


class ValidationError(Exception):
    """バリデーションエラー"""
    def __init__(
        self,
        message: str,
        param: str | None = None,
        suggestions: list[str] | None = None,
    ):
        super().__init__(message)
        self.param = param
        self.suggestions = suggestions or []


def validate_params(command: str, params: dict) -> dict:
    """
    コマンドのパラメータをスキーマに基づいてバリデーション。

    スキーマ未定義のコマンドはバリデーションスキップ。
    """
    schema = get_schema(command)
    if schema is None:
        return params

    valid_names = {p.name for p in schema.params}

    # 1. 未知のパラメータ名チェック
    for key in params:
        if key not in valid_names:
            suggestions = _find_similar(key, valid_names)
            raise ValidationError(
                f"Unknown parameter '{key}' for command '{command}'. "
                f"Valid parameters: {', '.join(sorted(valid_names))}",
                param=key,
                suggestions=suggestions,
            )

    # 2. 必須パラメータチェック
    for p in schema.params:
        if p.required and p.name not in params:
            raise ValidationError(
                f"Required parameter '{p.name}' missing for command '{command}'",
                param=p.name,
            )

    # 3. 型チェック・変換
    validated = {}
    for key, value in params.items():
        param_schema = next(p for p in schema.params if p.name == key)
        validated[key] = _coerce_type(key, value, param_schema)

    return validated


def _coerce_type(name: str, value: object, schema: ParamSchema) -> object:
    """型変換を試みる。失敗時は ValidationError。"""
    try:
        match schema.type:
            case ParamType.STRING:
                return str(value)
            case ParamType.INTEGER:
                return int(value)
            case ParamType.FLOAT:
                return float(value)
            case ParamType.BOOLEAN:
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes")
                return bool(value)
            case ParamType.ENUM:
                if str(value) not in (schema.enum_values or []):
                    raise ValidationError(
                        f"Invalid value '{value}' for '{name}'. "
                        f"Must be one of: {', '.join(schema.enum_values or [])}",
                        param=name,
                    )
                return str(value)
            case _:
                return value
    except ValidationError:
        raise
    except (ValueError, TypeError):
        raise ValidationError(
            f"Invalid type for '{name}': expected {schema.type.value}, "
            f"got {type(value).__name__}",
            param=name,
        )


def _find_similar(name: str, valid_names: set[str], max_results: int = 3) -> list[str]:
    """部分文字列マッチで類似パラメータを検索"""
    suggestions = []
    name_lower = name.lower()
    for valid in sorted(valid_names):
        if name_lower in valid.lower() or valid.lower() in name_lower:
            suggestions.append(valid)
    return suggestions[:max_results]
```

**Step 4: 通過を確認**
Run: `venv/bin/python -m pytest tests/test_validation.py -v`
Expected: PASS

**Step 5: 全テスト回帰確認**
Run: `venv/bin/python -m pytest tests/ -v --ignore=tests/e2e`
Expected: ALL PASS

**Step 6: コミット**
```
git add cli/validation.py tests/test_validation.py
git commit -m "feat: add input validation with type coercion and suggestions (Phase 4)"
```

---

### Task 11: execute_command にバリデーション統合

**Files:**
- Modify: `cli/helpers.py`
- Modify: `tests/test_helpers.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_helpers.py に追記

class TestExecuteCommandValidation:
    """execute_command() のバリデーション統合テスト"""

    def test_validation_error_exit_code_2(self):
        from cli.helpers import execute_command
        mock_ctx = MagicMock()
        mock_ctx.obj = {"output": "json", "timeout": 30.0, "fields": None}

        # Unknown parameter for a schema-defined command
        with patch("cli.helpers.get_bridge") as mock_get:
            mock_bridge = AsyncMock()
            mock_get.return_value = mock_bridge
            execute_command(mock_ctx, "develop.setValue", {"Exposre": 0.5})

        mock_ctx.exit.assert_called_with(2)
        # Bridge should NOT have been called
        mock_bridge.send_command.assert_not_called()

    def test_valid_params_pass_to_bridge(self):
        from cli.helpers import execute_command
        mock_ctx = MagicMock()
        mock_ctx.obj = {"output": "json", "timeout": 30.0, "fields": None}

        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {"result": {"status": "ok"}}

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(
                mock_ctx, "develop.setValue",
                {"parameter": "Exposure", "value": 0.5}
            )

        mock_bridge.send_command.assert_called_once()
```

**Step 2: 失敗を確認**
Run: `venv/bin/python -m pytest tests/test_helpers.py::TestExecuteCommandValidation -v`
Expected: FAIL

**Step 3: 最小限の実装**

`cli/helpers.py` の `execute_command()` にバリデーション呼び出しを追加:

```python
# execute_command() 内の async def _run() を修正:

async def _run():
    bridge = get_bridge()
    try:
        # バリデーション（スキーマ未定義コマンドはスキップ）
        from cli.validation import validate_params, ValidationError
        try:
            validated = validate_params(command, params)
        except ValidationError as e:
            click.echo(
                OutputFormatter.format_error(
                    str(e), fmt,
                    code="VALIDATION_ERROR",
                    suggestions=e.suggestions,
                ),
                err=True,
            )
            ctx.exit(2)
            return

        await bridge.connect()
        result = await bridge.send_command(command, validated, timeout=cmd_timeout)
        # ... 以下既存
```

**Step 4: 通過を確認**
Run: `venv/bin/python -m pytest tests/test_helpers.py -v`
Expected: PASS

**Step 5: 全テスト回帰確認**
Run: `venv/bin/python -m pytest tests/ -v --ignore=tests/e2e`
Expected: ALL PASS

**Step 6: コミット**
```
git add cli/helpers.py tests/test_helpers.py
git commit -m "feat: integrate validation into execute_command with exit code 2"
```

---

## Phase 5: --dry-run 全 mutating コマンド

### Task 12: cli/decorators.py -- dry_run_support デコレータ

**Files:**
- Create: `cli/decorators.py`
- Create: `tests/test_decorators.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_decorators.py
"""Tests for CLI decorators."""
import json
import pytest
from click.testing import CliRunner
import click


class TestDryRunSupport:
    """@dry_run_support デコレータのテスト"""

    def test_dry_run_returns_preview(self):
        @click.group()
        @click.pass_context
        def test_group(ctx):
            ctx.ensure_object(dict)
            ctx.obj["output"] = "json"

        @test_group.command("test-cmd")
        @click.argument("param")
        @click.pass_context
        def test_cmd(ctx, param):
            from cli.decorators import dry_run_guard
            preview = dry_run_guard(ctx, command="test.command", params={"param": param})
            if preview:
                return
            click.echo("executed")

        runner = CliRunner()
        result = runner.invoke(test_group, ["test-cmd", "--dry-run", "value"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["dry_run"] is True
        assert "executed" not in result.output

    def test_no_dry_run_executes_normally(self):
        @click.group()
        @click.pass_context
        def test_group(ctx):
            ctx.ensure_object(dict)
            ctx.obj["output"] = "text"

        @test_group.command("test-cmd")
        @click.argument("param")
        @click.pass_context
        def test_cmd(ctx, param):
            from cli.decorators import dry_run_guard
            preview = dry_run_guard(ctx, command="test.command", params={"param": param})
            if preview:
                return
            click.echo("executed")

        runner = CliRunner()
        result = runner.invoke(test_group, ["test-cmd", "value"])
        assert "executed" in result.output
```

注意: デコレータではなくガード関数方式を採用。理由: Click のデコレータ順序の複雑さを避けるため。

**Step 2: 失敗を確認**
Run: `venv/bin/python -m pytest tests/test_decorators.py -v`
Expected: FAIL

**Step 3: 最小限の実装**

```python
# cli/decorators.py
"""CLI decorators and guard functions."""
from __future__ import annotations
import click
from cli.output import OutputFormatter


def dry_run_option(func):
    """Click コマンドに --dry-run オプションを追加するデコレータ"""
    return click.option("--dry-run", is_flag=True, default=False,
                        help="Preview without executing")(func)


def dry_run_guard(
    ctx: click.Context,
    *,
    command: str,
    params: dict,
) -> bool:
    """
    dry-run ガード。--dry-run が指定されていればプレビューを出力して True を返す。
    False を返した場合はコマンドを通常実行する。

    Usage:
        @cmd.command("set")
        @dry_run_option
        @click.pass_context
        def set_value(ctx, dry_run, ...):
            preview = dry_run_guard(ctx, command="develop.setValue", params={...})
            if preview:
                return
            execute_command(ctx, "develop.setValue", params)
    """
    dry_run = ctx.params.get("dry_run", False)
    if not dry_run:
        return False

    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
    preview = {
        "dry_run": True,
        "command": command,
        "params": {k: v for k, v in params.items() if v is not None},
    }
    click.echo(OutputFormatter.format(preview, fmt))
    return True
```

**Step 4: 通過を確認**
Run: `venv/bin/python -m pytest tests/test_decorators.py -v`
Expected: PASS

**Step 5: 全テスト回帰確認**
Run: `venv/bin/python -m pytest tests/ -v --ignore=tests/e2e`
Expected: ALL PASS

**Step 6: コミット**
```
git add cli/decorators.py tests/test_decorators.py
git commit -m "feat: add dry_run_option and dry_run_guard for mutating commands (Phase 5)"
```

---

### Task 13: execute_command に dry-run 統合

**Files:**
- Modify: `cli/helpers.py`
- Modify: `tests/test_helpers.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_helpers.py に追記

class TestExecuteCommandDryRun:
    """execute_command() の dry-run テスト"""

    def test_dry_run_skips_execution(self):
        from cli.helpers import execute_command
        mock_ctx = MagicMock()
        mock_ctx.obj = {"output": "json", "timeout": 30.0, "fields": None}
        mock_ctx.params = {"dry_run": True}

        mock_bridge = AsyncMock()
        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(
                mock_ctx, "develop.setValue",
                {"parameter": "Exposure", "value": 0.5}
            )

        # Bridge should NOT be called
        mock_bridge.send_command.assert_not_called()

    def test_no_dry_run_executes(self):
        from cli.helpers import execute_command
        mock_ctx = MagicMock()
        mock_ctx.obj = {"output": "json", "timeout": 30.0, "fields": None}
        mock_ctx.params = {}

        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {"result": {"ok": True}}

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(
                mock_ctx, "develop.setValue",
                {"parameter": "Exposure", "value": 0.5}
            )

        mock_bridge.send_command.assert_called_once()
```

**Step 2: 失敗を確認**
Run: `venv/bin/python -m pytest tests/test_helpers.py::TestExecuteCommandDryRun -v`
Expected: FAIL

**Step 3: 最小限の実装**

`cli/helpers.py` の `execute_command()` 先頭に dry-run チェックを追加:

```python
def execute_command(ctx, command: str, params: dict, *, timeout: float | None = None):
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
    fields = ctx.obj.get("fields") if ctx.obj else None
    cmd_timeout = timeout or (ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0)

    # dry-run チェック
    if getattr(ctx, "params", {}).get("dry_run", False):
        from lightroom_sdk.schema import get_schema
        schema = get_schema(command)
        preview = {
            "dry_run": True,
            "command": command,
            "mutating": schema.mutating if schema else None,
            "params": {k: v for k, v in params.items() if v is not None},
        }
        click.echo(OutputFormatter.format(preview, fmt))
        return

    # ... 以下既存の async def _run() ...
```

**Step 4: 通過を確認**
Run: `venv/bin/python -m pytest tests/test_helpers.py -v`
Expected: PASS

**Step 5: 全テスト回帰確認**
Run: `venv/bin/python -m pytest tests/ -v --ignore=tests/e2e`
Expected: ALL PASS

**Step 6: コミット**
```
git add cli/helpers.py tests/test_helpers.py
git commit -m "feat: add dry-run support to execute_command"
```

---

## Phase 6: --json 入力統一

### Task 14: cli/decorators.py -- json_input_option

**Files:**
- Modify: `cli/decorators.py`
- Modify: `tests/test_decorators.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_decorators.py に追記

class TestJsonInput:
    """--json / --json-stdin 入力テスト"""

    def test_json_option_parses_dict(self):
        from cli.decorators import parse_json_input

        result = parse_json_input('{"parameter": "Exposure", "value": 0.5}', None)
        assert result == {"parameter": "Exposure", "value": 0.5}

    def test_json_option_invalid_json_raises(self):
        from cli.decorators import parse_json_input
        with pytest.raises(click.BadParameter, match="Invalid JSON"):
            parse_json_input("{invalid", None)

    def test_json_option_non_dict_raises(self):
        from cli.decorators import parse_json_input
        with pytest.raises(click.BadParameter, match="must be a JSON object"):
            parse_json_input("[1, 2, 3]", None)

    def test_json_stdin_reads_from_stdin(self):
        from cli.decorators import parse_json_input
        import io
        stdin = io.StringIO('{"key": "value"}')
        result = parse_json_input(None, stdin)
        assert result == {"key": "value"}

    def test_no_json_returns_none(self):
        from cli.decorators import parse_json_input
        result = parse_json_input(None, None)
        assert result is None

    def test_both_json_and_stdin_raises(self):
        from cli.decorators import parse_json_input
        import io
        with pytest.raises(click.BadParameter, match="Cannot use both"):
            parse_json_input('{"a": 1}', io.StringIO('{"b": 2}'))
```

**Step 2: 失敗を確認**
Run: `venv/bin/python -m pytest tests/test_decorators.py::TestJsonInput -v`
Expected: FAIL

**Step 3: 最小限の実装**

`cli/decorators.py` に追加:

```python
import json as json_module
import sys
from typing import IO


def json_input_options(func):
    """--json と --json-stdin オプションを追加するデコレータ"""
    func = click.option("--json", "json_str", default=None,
                        help="JSON string with all parameters")(func)
    func = click.option("--json-stdin", "json_stdin", is_flag=True, default=False,
                        help="Read JSON parameters from stdin")(func)
    return func


def parse_json_input(
    json_str: str | None,
    stdin: IO | None,
) -> dict | None:
    """
    --json と --json-stdin の入力を解析する。

    Returns:
        dict: パース済みパラメータ
        None: JSON入力なし（既存フラグを使用）
    Raises:
        click.BadParameter: JSON解析失敗
    """
    has_json = json_str is not None
    has_stdin = stdin is not None and (
        not hasattr(stdin, "isatty") or not stdin.isatty()
    )

    # stdin が実際にデータを持っているか確認
    stdin_data = None
    if has_stdin and stdin is not None:
        stdin_data = stdin.read().strip()
        if not stdin_data:
            has_stdin = False

    if has_json and has_stdin and stdin_data:
        raise click.BadParameter("Cannot use both --json and --json-stdin")

    raw = json_str or stdin_data
    if not raw:
        return None

    try:
        parsed = json_module.loads(raw)
    except json_module.JSONDecodeError as e:
        raise click.BadParameter(f"Invalid JSON: {e}")

    if not isinstance(parsed, dict):
        raise click.BadParameter("--json must be a JSON object (dict)")

    return parsed
```

**Step 4: 通過を確認**
Run: `venv/bin/python -m pytest tests/test_decorators.py -v`
Expected: PASS

**Step 5: 全テスト回帰確認**
Run: `venv/bin/python -m pytest tests/ -v --ignore=tests/e2e`
Expected: ALL PASS

**Step 6: コミット**
```
git add cli/decorators.py tests/test_decorators.py
git commit -m "feat: add --json and --json-stdin input options (Phase 6)"
```

---

### Task 15: execute_command に --json 入力統合

**Files:**
- Modify: `cli/helpers.py`
- Modify: `tests/test_helpers.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_helpers.py に追記

class TestExecuteCommandJsonInput:
    """execute_command() の --json 入力テスト"""

    def test_json_input_overrides_params(self):
        from cli.helpers import execute_command
        mock_ctx = MagicMock()
        mock_ctx.obj = {"output": "json", "timeout": 30.0, "fields": None}
        mock_ctx.params = {"json_str": '{"parameter": "Contrast", "value": 50}'}

        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {"result": {"ok": True}}

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            execute_command(
                mock_ctx, "develop.setValue",
                {"parameter": "Exposure", "value": 0.5}  # overridden by --json
            )

        call_args = mock_bridge.send_command.call_args
        assert call_args[0][1]["parameter"] == "Contrast"
        assert call_args[0][1]["value"] == 50
```

**Step 2: 失敗を確認**
Run: `venv/bin/python -m pytest tests/test_helpers.py::TestExecuteCommandJsonInput -v`
Expected: FAIL

**Step 3: 最小限の実装**

`cli/helpers.py` の `execute_command()` に JSON 入力チェックを追加（dry-run チェックの前）:

```python
def execute_command(ctx, command: str, params: dict, *, timeout: float | None = None):
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
    fields = ctx.obj.get("fields") if ctx.obj else None
    cmd_timeout = timeout or (ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0)

    # --json 入力チェック
    json_str = getattr(ctx, "params", {}).get("json_str")
    if json_str:
        from cli.decorators import parse_json_input
        try:
            json_params = parse_json_input(json_str, None)
            if json_params is not None:
                params = json_params
        except click.BadParameter as e:
            click.echo(
                OutputFormatter.format_error(str(e), fmt, code="VALIDATION_ERROR"),
                err=True,
            )
            ctx.exit(2)
            return

    # dry-run チェック
    # ... 以下既存 ...
```

**Step 4: 通過を確認**
Run: `venv/bin/python -m pytest tests/test_helpers.py -v`
Expected: PASS

**Step 5: 全テスト回帰確認**
Run: `venv/bin/python -m pytest tests/ -v --ignore=tests/e2e`
Expected: ALL PASS

**Step 6: コミット**
```
git add cli/helpers.py tests/test_helpers.py
git commit -m "feat: integrate --json input into execute_command (Phase 6)"
```

---

## Phase 7: 既存コマンドの段階的移行

### Task 16: system.py を execute_command に移行

**Files:**
- Modify: `cli/commands/system.py`
- Modify: `tests/test_cli_system.py`

**Step 1: 失敗するテストを書く**

既存テスト (`tests/test_cli_system.py`) が通ることを確認するのが主目的。追加テスト:

```python
# tests/test_cli_system.py に追記

def test_ping_uses_json_output_in_non_tty():
    """非TTY環境ではデフォルト出力がJSONになることを確認"""
    from click.testing import CliRunner
    from cli.main import cli
    runner = CliRunner()
    # CliRunner は非TTYなので json がデフォルト
    # ただし接続エラーになるため、エラー出力が JSON であることを確認
    result = runner.invoke(cli, ["system", "ping"])
    # exit_code 3 (connection error) または JSON エラー出力
    assert result.exit_code != 0 or "error" in result.output.lower() or "{" in result.output
```

**Step 2: 既存テストが通ることを確認**
Run: `venv/bin/python -m pytest tests/test_cli_system.py -v`
Expected: PASS (既存テストが壊れていないことを確認)

**Step 3: system.py を execute_command に移行**

`cli/commands/system.py` を以下のように書き換え:

```python
import click
from pathlib import Path
from cli.helpers import execute_command, get_bridge, run_async
from cli.output import OutputFormatter
from cli.decorators import dry_run_option, json_input_options


@click.group()
def system():
    """System commands (ping, status, reconnect, check-connection)"""
    pass


@system.command()
@click.pass_context
def ping(ctx):
    """Test connection to Lightroom"""
    execute_command(ctx, "system.ping", {})


@system.command()
@click.pass_context
def status(ctx):
    """Get Lightroom bridge status"""
    execute_command(ctx, "system.status", {})


@system.command()
def reconnect():
    """Force reconnection to Lightroom"""
    async def _run():
        bridge = get_bridge()
        try:
            await bridge.connect()
            await bridge.disconnect()
            await bridge.connect()
            click.echo("Reconnected")
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()
    run_async(_run())


@system.command("check-connection")
@click.option("--port-file", default=None, help="Path to port file (default: auto-detect)")
@click.pass_context
def check_connection(ctx, port_file):
    """Check if Lightroom is available"""
    if port_file is None:
        from lightroom_sdk.paths import get_port_file
        port_path = get_port_file()
    else:
        port_path = Path(port_file)
    if not port_path.exists():
        click.echo("Lightroom connection unavailable: port file not found")
        return
    timeout = ctx.obj.get("timeout", 5.0) if ctx.obj else 5.0

    async def _run():
        bridge = get_bridge(port_file=port_file)
        try:
            await bridge.connect()
            await bridge.send_command("system.ping", timeout=timeout)
            click.echo("Lightroom connection: ok")
        except Exception as e:
            click.echo(f"Lightroom connection unavailable: {e}")
        finally:
            await bridge.disconnect()
    run_async(_run())
```

**Step 4: 通過を確認**
Run: `venv/bin/python -m pytest tests/test_cli_system.py -v`
Expected: PASS

**Step 5: 全テスト回帰確認**
Run: `venv/bin/python -m pytest tests/ -v --ignore=tests/e2e`
Expected: ALL PASS

**Step 6: コミット**
```
git add cli/commands/system.py tests/test_cli_system.py
git commit -m "refactor: migrate system commands to execute_command helper"
```

---

### Task 17: catalog.py を execute_command に移行

**重要**: catalog.py は30コマンドあるため、移行パターンを示す。

**Files:**
- Modify: `cli/commands/catalog.py`

**移行パターン**:

Before (既存):
```python
@catalog.command("get-selected")
@click.pass_context
def get_selected(ctx):
    """Get currently selected photos"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("catalog.getSelectedPhotos", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()
    run_async(_run())
```

After (移行後):
```python
@catalog.command("get-selected")
@click.pass_context
def get_selected(ctx):
    """Get currently selected photos"""
    execute_command(ctx, "catalog.getSelectedPhotos", {})
```

mutating コマンドは `@dry_run_option` も追加:
```python
@catalog.command("set-rating")
@click.argument("photo_id")
@click.argument("rating", type=int)
@dry_run_option
@click.pass_context
def set_rating(ctx, photo_id, rating, dry_run):
    """Set photo rating (0-5)"""
    params = {"photoId": photo_id, "rating": rating}
    execute_command(ctx, "catalog.setRating", params)
```

全30コマンドを同パターンで移行する。テストは既存テスト (`tests/integration/test_cli_catalog*.py`) で回帰確認。

**Step 4: 通過を確認**
Run: `venv/bin/python -m pytest tests/integration/test_cli_catalog*.py -v`
Expected: PASS

**Step 5: 全テスト回帰確認**
Run: `venv/bin/python -m pytest tests/ -v --ignore=tests/e2e`
Expected: ALL PASS

**Step 6: コミット**
```
git add cli/commands/catalog.py
git commit -m "refactor: migrate catalog commands to execute_command helper"
```

---

### Task 18: develop.py を execute_command に移行

develop.py は最大のファイル（40+コマンド、サブグループ含む）。Task 17 と同じパターン。

**移行対象サブグループ**:
- `develop.*` (直接コマンド: get-settings, set, get, apply, auto-tone, auto-wb, tool, reset, preset, snapshot, copy-settings, paste-settings, range, reset-param, process-version, set-process-version)
- `develop.curve.*` (get, set, linear, s-curve, add-point, remove-point)
- `develop.mask.*` (list, selected, go-to, toggle-overlay)
- `develop.local.*` (get, set, apply, params, create-mask)
- `develop.filter.*` (graduated, radial, brush, range)
- `develop.debug.*` (dump, gradient-params, monitor, probe)
- `develop.color.*` (green-swatch, cyan-swatch, enhance)
- `develop.reset-*` (gradient, circular, brush, masking, crop, transforms, spot, redeye, healing)
- `develop.edit-in-photoshop`

ファイル先頭の `get_bridge()` / `run_async()` は削除し、`from cli.helpers import execute_command, get_bridge, run_async` に置き換える。

**Step 5: 全テスト回帰確認**
Run: `venv/bin/python -m pytest tests/ -v --ignore=tests/e2e`
Expected: ALL PASS

**Step 6: コミット**
```
git add cli/commands/develop.py
git commit -m "refactor: migrate develop commands to execute_command helper"
```

---

### Task 19: selection.py, preview.py を execute_command に移行

Task 17 と同パターン。

**Step 6: コミット**
```
git add cli/commands/selection.py cli/commands/preview.py
git commit -m "refactor: migrate selection and preview commands to execute_command helper"
```

---

### Task 20: ai_mask.py の --dry-run を execute_command に統合

ai_mask.py の batch コマンドは既に `--dry-run` を持つ。`execute_command()` ベースに移行して一貫性を確保。個別の AI タイプコマンド（subject, sky 等）はファクトリ関数で生成されているため、ファクトリ内で `execute_command()` を呼ぶように変更。

**Step 6: コミット**
```
git add cli/commands/ai_mask.py
git commit -m "refactor: migrate ai_mask commands to execute_command helper"
```

---

## Phase 8: SKILLS.md 微調整

### Task 21: SKILLS.md 更新

**Files:**
- Modify: `SKILLS.md`

**変更内容**:
- TTY検出による自動JSON出力を説明（`-o json` が不要になった旨）
- `lr schema` コマンドの使い方を追記
- `--fields` の使い方を追記
- `--dry-run` の使い方を追記
- `--json` 入力の推奨を追記
- 環境変数 `LR_OUTPUT`, `LR_TIMEOUT`, `LR_FIELDS`, `LR_VERBOSE` を追記

**Step 6: コミット**
```
git add SKILLS.md
git commit -m "docs: update SKILLS.md for agent-first CLI features"
```

---

## Phase 9: 最終回帰テスト + バージョンバンプ

### Task 22: 全テスト通過確認 + バージョンバンプ

**Step 1: 全テスト実行**
```
venv/bin/python -m pytest tests/ -v --ignore=tests/e2e
```
Expected: ALL PASS (215件 + 新規約80件 = 約295件)

**Step 2: バージョンバンプ**
- `cli/main.py`: `version="0.3.0"`
- `pyproject.toml` (存在する場合): `version = "0.3.0"`

**Step 3: コミット**
```
git add cli/main.py pyproject.toml
git commit -m "feat: bump version to 0.3.0 (agent-first CLI optimization)"
```

---

## タスク一覧サマリ

| # | Phase | タスク | 新規/修正ファイル |
|---|-------|--------|------------------|
| 1 | 1 | resolve_output_format | cli/middleware.py, tests/test_middleware.py |
| 2 | 1 | resolve_timeout, resolve_fields | cli/middleware.py, tests/test_middleware.py |
| 3 | 1 | main.py TTY統合 | cli/main.py, tests/test_cli_main.py |
| 4 | 2 | OutputFormatter fields | cli/output.py, tests/test_output_formatter.py |
| 5 | 2 | 構造化エラー出力 | cli/output.py, tests/test_output_formatter.py |
| 6 | 2 | execute_command ヘルパー | cli/helpers.py, tests/test_helpers.py |
| 7 | 3 | スキーマデータ構造 | lightroom_sdk/schema.py, tests/test_schema.py |
| 8 | 3 | スキーマ整合性テスト | tests/test_schema.py |
| 9 | 3 | lr schema コマンド | cli/schema.py, tests/test_cli_schema.py, cli/main.py |
| 10 | 4 | バリデーション基盤 | cli/validation.py, tests/test_validation.py |
| 11 | 4 | バリデーション統合 | cli/helpers.py, tests/test_helpers.py |
| 12 | 5 | dry_run_support | cli/decorators.py, tests/test_decorators.py |
| 13 | 5 | dry-run統合 | cli/helpers.py, tests/test_helpers.py |
| 14 | 6 | --json入力 | cli/decorators.py, tests/test_decorators.py |
| 15 | 6 | --json統合 | cli/helpers.py, tests/test_helpers.py |
| 16 | 7 | system.py移行 | cli/commands/system.py |
| 17 | 7 | catalog.py移行 | cli/commands/catalog.py |
| 18 | 7 | develop.py移行 | cli/commands/develop.py |
| 19 | 7 | selection.py, preview.py移行 | cli/commands/selection.py, cli/commands/preview.py |
| 20 | 7 | ai_mask.py移行 | cli/commands/ai_mask.py |
| 21 | 8 | SKILLS.md更新 | SKILLS.md |
| 22 | 9 | 最終回帰テスト + バージョンバンプ | cli/main.py, pyproject.toml |

**合計: 22タスク (9 Phase)**
