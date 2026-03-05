# Agent-First CLI 設計書

**日付**: 2026-03-05
**ステータス**: 提案
**対象**: lightroom-cli v0.3.0

---

## 目次

1. [背景と目的](#背景と目的)
2. [アプローチ比較](#アプローチ比較)
3. [推奨アプローチ: Layered Enhancement の詳細設計](#推奨アプローチの詳細設計)
4. [コンポーネント設計](#コンポーネント設計)
5. [各変更の実装方針](#各変更の実装方針)
6. [エラーハンドリング方針](#エラーハンドリング方針)
7. [テスト戦略](#テスト戦略)
8. [既存コマンド移行戦略](#既存コマンド移行戦略)
9. [不確実な点・要確認事項](#不確実な点要確認事項)

---

## 背景と目的

lightroom-cli は AIエージェントが主な利用者であり、人間がコマンドを叩くことは想定しない。現在の CLI は人間向けのデフォルト（text出力、位置引数、TTY前提）になっており、エージェントにとって以下の問題がある:

1. **出力がパースしにくい** — デフォルトが text 出力で、毎回 `-o json` が必要
2. **入力バリデーションが弱い** — ハルシネーションしたパラメータ名がそのまま Lua に渡る
3. **スキーマが不透明** — エージェントがコマンドの引数・型・制約を自己発見できない
4. **レスポンスが冗長** — 不要なフィールドが context window を圧迫
5. **dry-run が限定的** — batch コマンドのみ対応
6. **環境変数未対応** — CI/CD やエージェント環境での設定が困難

### 実装する7項目

| # | 項目 | 現状 |
|---|------|------|
| 1 | `--output json` | 済み（ただしデフォルトが text） |
| 2 | 入力バリデーション | 未実装 |
| 3 | スキーマ introspection (`lr schema`) | 未実装 |
| 4 | `--fields` レスポンス制限 | 未実装 |
| 5 | `--dry-run` 全 mutating コマンド | batch のみ |
| 6 | CONTEXT.md / SKILLS.md | SKILLS.md 済み（微調整のみ） |
| 7 | MCP surface | スコープ外 |

---

## アプローチ比較

### アプローチ A: Big Rewrite — コマンド定義をスキーマ駆動に全面書き換え

各コマンドを Python dict/dataclass でスキーマ定義し、Click コマンドを自動生成する。CommandRegistry パターンの完全適用。

| 観点 | 評価 |
|------|------|
| コード重複削減 | 最大（ボイラープレート全廃） |
| 既存テストへの影響 | 大（215件の大半が壊れる） |
| 実装工数 | 大（2-3日） |
| リスク | 高（一括変更で予期せぬ regression） |
| スキーマ introspection | 自然に実現 |
| dry-run / fields | スキーマ定義から自動付与 |

### アプローチ B: Layered Enhancement — 既存構造を維持しつつ横断的機能を追加

既存の Click コマンド定義はそのまま残し、middleware / decorator / schema 定義ファイルを追加する。コマンド本体のリファクタリングは段階的に行う。

| 観点 | 評価 |
|------|------|
| コード重複削減 | 中（共通ヘルパー化） |
| 既存テストへの影響 | 小（既存コマンドのシグネチャ不変） |
| 実装工数 | 中（1-2日） |
| リスク | 低（段階的変更、各ステップでテスト通過） |
| スキーマ introspection | 別途スキーマ定義ファイルが必要 |
| dry-run / fields | デコレータで段階的に付与 |

### アプローチ C: Hybrid — スキーマ定義 + 既存コマンドの漸進的移行

スキーマ定義ファイルを Single Source of Truth として作成し、新コマンドはスキーマ駆動で自動生成、既存コマンドは phase ごとに移行する。

| 観点 | 評価 |
|------|------|
| コード重複削減 | 大（完了時） |
| 既存テストへの影響 | 小（移行対象のみ） |
| 実装工数 | 中-大（Phase 分割で管理） |
| リスク | 中（Phase 間の二重管理コスト） |
| スキーマ introspection | スキーマ定義から自動生成 |
| dry-run / fields | スキーマ定義に含める |

### 推奨: アプローチ B（Layered Enhancement）

**理由:**
1. **215件のテストを壊さない** — 既存コマンドのシグネチャを変更しないため、段階的にテストを追加・修正できる
2. **即座に価値を提供** — TTY検出とスキーマコマンドは既存コードに触れずに追加可能
3. **将来の Big Rewrite を妨げない** — スキーマ定義ファイルは Approach C への自然な移行パスになる
4. **リスクが最小** — 各変更が独立しており、個別にロールバック可能

---

## 推奨アプローチの詳細設計

### アーキテクチャ

```
[CLI Layer]
  cli/main.py          — エントリポイント（TTY検出・環境変数・グローバルオプション追加）
  cli/output.py        — OutputFormatter（--fields フィルタリング追加）
  cli/schema.py        — NEW: lr schema コマンド + スキーマ定義
  cli/validation.py    — NEW: 入力バリデーション
  cli/decorators.py    — NEW: @dry_run, @with_fields, @validated デコレータ
  cli/middleware.py     — NEW: TTY検出・環境変数解決
  cli/commands/*.py    — 既存コマンド（デコレータ付与のみの変更）

[SDK Layer]
  lightroom_sdk/schema.py  — NEW: コマンドスキーマ定義（Single Source of Truth）

[既存（変更なし）]
  lightroom_sdk/client.py
  lightroom_sdk/socket_bridge.py
  lightroom_sdk/resilient_bridge.py
  lightroom_sdk/retry.py
  Lua Plugin（変更なし）
```

### データフロー

```
エージェント入力
  ↓
[cli/main.py] TTY検出 → 非TTYなら output="json" をデフォルトに
  ↓
[cli/middleware.py] 環境変数解決 (LR_OUTPUT, LR_TIMEOUT, LR_FIELDS)
  ↓
[cli/decorators.py] @validated → schema.py のスキーマでバリデーション
  ↓
[cli/decorators.py] @dry_run → dry-runなら実行せずプレビュー返却
  ↓
[既存コマンド実行] → bridge.send_command()
  ↓
[cli/output.py] --fields でフィールド制限 → JSON出力
  ↓
エージェントへ
```

---

## コンポーネント設計

### 1. lightroom_sdk/schema.py — コマンドスキーマ定義

スキーマ定義を SDK 層に置く理由: バリデーションは SDK の責務であり、CLI 以外のクライアント（将来の MCP server 等）でも再利用できるため。

```python
from dataclasses import dataclass, field
from typing import Any, Optional
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
    default: Any = None
    enum_values: list[str] | None = None  # type=ENUM 時のみ

@dataclass
class CommandSchema:
    command: str          # bridge コマンド名 (e.g., "develop.setValue")
    cli_path: str         # CLI パス (e.g., "develop.set")
    description: str
    params: list[ParamSchema] = field(default_factory=list)
    mutating: bool = False  # dry-run 対象かどうか
    timeout: float = 30.0
    response_fields: list[str] = field(default_factory=list)  # 利用可能なレスポンスフィールド

# --- スキーマ定義 ---

COMMAND_SCHEMAS: dict[str, CommandSchema] = {
    "develop.setValue": CommandSchema(
        command="develop.setValue",
        cli_path="develop.set",
        description="Set develop parameter(s)",
        params=[
            ParamSchema("parameter", ParamType.STRING, required=True,
                        description="Develop parameter name (e.g., Exposure, Contrast)"),
            ParamSchema("value", ParamType.FLOAT, required=True,
                        description="Parameter value"),
        ],
        mutating=True,
        timeout=10.0,
    ),
    "catalog.setRating": CommandSchema(
        command="catalog.setRating",
        cli_path="catalog.set-rating",
        description="Set photo star rating",
        params=[
            ParamSchema("photoId", ParamType.STRING, required=True,
                        description="Photo ID"),
            ParamSchema("rating", ParamType.INTEGER, required=True,
                        description="Star rating (0-5)"),
        ],
        mutating=True,
    ),
    # ... 全107コマンド分を定義
}

def get_schema(command: str) -> CommandSchema | None:
    return COMMAND_SCHEMAS.get(command)

def get_schemas_by_group(group: str) -> dict[str, CommandSchema]:
    """グループ名（develop, catalog 等）でフィルタ"""
    return {k: v for k, v in COMMAND_SCHEMAS.items() if k.startswith(f"{group}.")}

def get_all_schemas() -> dict[str, CommandSchema]:
    return COMMAND_SCHEMAS
```

### 2. cli/validation.py — 入力バリデーション

```python
from lightroom_sdk.schema import get_schema, ParamType, ParamSchema
from lightroom_sdk.exceptions import ParameterError

class ValidationError(ParameterError):
    """バリデーションエラー"""
    def __init__(self, message: str, param: str | None = None, suggestions: list[str] | None = None):
        super().__init__(message, code="VALIDATION_ERROR")
        self.param = param
        self.suggestions = suggestions or []

def validate_params(command: str, params: dict) -> dict:
    """
    コマンドのパラメータをスキーマに基づいてバリデーション。

    チェック項目:
    1. パラメータ名の存在チェック（ハルシネーション対策）
    2. 型チェック（string, int, float, bool, json）
    3. 必須パラメータの欠損チェック
    4. enum 値のチェック

    注意: 範囲チェック（min/max）は Lua 側に任せる。
    """
    schema = get_schema(command)
    if schema is None:
        return params  # スキーマ未定義のコマンドはバリデーションスキップ

    valid_names = {p.name for p in schema.params}

    # 1. 未知のパラメータ名チェック
    for key in params:
        if key not in valid_names:
            # 類似パラメータを提案
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

    # 3. 型チェック
    validated = {}
    for key, value in params.items():
        param_schema = next(p for p in schema.params if p.name == key)
        validated[key] = _coerce_type(key, value, param_schema)

    return validated

def _coerce_type(name: str, value: any, schema: ParamSchema) -> any:
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
    except (ValueError, TypeError) as e:
        raise ValidationError(
            f"Invalid type for '{name}': expected {schema.type.value}, got {type(value).__name__}",
            param=name,
        )

def _find_similar(name: str, valid_names: set[str], threshold: int = 3) -> list[str]:
    """レーベンシュタイン距離で類似パラメータを検索（簡易版）"""
    suggestions = []
    name_lower = name.lower()
    for valid in valid_names:
        if name_lower in valid.lower() or valid.lower() in name_lower:
            suggestions.append(valid)
    return suggestions[:3]
```

### 3. cli/middleware.py — TTY検出・環境変数

```python
import os
import sys

# 環境変数マッピング
ENV_VARS = {
    "LR_OUTPUT": {"cli_key": "output", "type": str, "default": None},
    "LR_TIMEOUT": {"cli_key": "timeout", "type": float, "default": None},
    "LR_FIELDS": {"cli_key": "fields", "type": str, "default": None},
    "LR_VERBOSE": {"cli_key": "verbose", "type": bool, "default": False},
    "LR_PORT_FILE": {"cli_key": "port_file", "type": str, "default": "/tmp/lightroom_ports.txt"},
}

def resolve_output_format(explicit_output: str | None) -> str:
    """
    出力フォーマットの優先順位:
    1. --output / -o フラグ（明示指定）
    2. LR_OUTPUT 環境変数
    3. TTY検出（非TTYなら json, TTYなら text）
    """
    if explicit_output:
        return explicit_output

    env_output = os.environ.get("LR_OUTPUT")
    if env_output and env_output in ("json", "text", "table"):
        return env_output

    # 非TTY（パイプ、エージェント実行）では自動的に json
    if not sys.stdout.isatty():
        return "json"

    return "text"

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

### 4. cli/decorators.py — コマンドデコレータ

```python
import functools
import json
import click
from cli.output import OutputFormatter

def dry_run_support(func):
    """@dry_run_support: mutating コマンドに --dry-run を追加"""
    # Click option を動的に追加
    func = click.option("--dry-run", is_flag=True, help="Preview without executing")(func)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        dry_run = kwargs.pop("dry_run", False)
        ctx = click.get_current_context()
        if dry_run:
            # コマンド名とパラメータをプレビュー表示
            fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
            preview = {
                "dry_run": True,
                "command": ctx.info_name,
                "group": ctx.parent.info_name if ctx.parent else None,
                "params": {k: v for k, v in kwargs.items()
                           if v is not None and k not in ("ctx",)},
            }
            click.echo(OutputFormatter.format(preview, fmt))
            return
        return func(*args, **kwargs)

    return wrapper

def fields_filter(func):
    """@fields_filter: --fields でレスポンスフィールドを制限"""
    func = click.option("--fields", default=None,
                        help="Comma-separated fields to include in response")(func)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        fields = kwargs.pop("fields", None)
        ctx = click.get_current_context()
        if fields:
            ctx.obj = ctx.obj or {}
            ctx.obj["fields"] = [f.strip() for f in fields.split(",")]
        return func(*args, **kwargs)

    return wrapper
```

### 5. cli/schema.py — `lr schema` コマンド

```python
import click
from cli.output import OutputFormatter

@click.command("schema")
@click.argument("path", required=False, default=None)
@click.pass_context
def schema_cmd(ctx):
    """
    Introspect command schemas.

    Usage:
      lr schema                    # 全グループ一覧
      lr schema develop            # develop グループのコマンド一覧
      lr schema develop.set        # develop.set のパラメータ詳細
    """
    from lightroom_sdk.schema import get_all_schemas, get_schemas_by_group, get_schema
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    path = ctx.params.get("path")

    if path is None:
        # 全グループ一覧
        schemas = get_all_schemas()
        groups = {}
        for cmd_name, schema in schemas.items():
            group = cmd_name.split(".")[0]
            if group not in groups:
                groups[group] = {"name": group, "commands": 0}
            groups[group]["commands"] += 1
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
        # コマンド単位の詳細
        # cli_path から bridge コマンドへの逆引き
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

### 6. cli/output.py への変更 — `--fields` フィルタリング

```python
# 既存 OutputFormatter.format() に fields パラメータを追加

@staticmethod
def format(data: Any, mode: str = "text", fields: list[str] | None = None) -> str:
    if fields:
        data = OutputFormatter._filter_fields(data, fields)
    # ... 既存ロジック

@staticmethod
def _filter_fields(data: Any, fields: list[str]) -> Any:
    """指定フィールドのみを残す"""
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if k in fields}
    elif isinstance(data, list):
        return [OutputFormatter._filter_fields(item, fields) for item in data]
    return data
```

### 7. cli/main.py への変更

```python
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

# schema コマンドを追加
from cli.schema import schema_cmd
cli.add_command(schema_cmd)

# 既存グループ（変更なし）
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

---

## 各変更の実装方針

### Phase 1: TTY検出 + 環境変数（影響: main.py のみ）

**変更ファイル**: `cli/main.py`, `cli/middleware.py`（新規）

- `--output` のデフォルトを `None` に変更（現在: `"text"`）
- `resolve_output_format()` で TTY 検出 → 非 TTY 時は `json` をデフォルトに
- 環境変数 `LR_OUTPUT`, `LR_TIMEOUT`, `LR_VERBOSE` のサポート
- **既存テストへの影響**: テストは `CliRunner` を使用（非 TTY）。テスト内で `obj={"output": "text"}` を明示すれば問題なし

**テスト追加**:
- `tests/test_middleware.py` — TTY/非TTY、環境変数の優先順位テスト

### Phase 2: `--fields` レスポンスフィルタリング

**変更ファイル**: `cli/main.py`（`--fields` オプション追加）, `cli/output.py`（`_filter_fields` 追加）

- グローバルオプション `--fields` / `-f` を追加
- `OutputFormatter.format()` に `fields` パラメータを追加
- 各コマンドの `click.echo(OutputFormatter.format(result, fmt))` を `click.echo(OutputFormatter.format(result, fmt, fields=ctx.obj.get("fields")))` に変更

**テスト追加**:
- `tests/test_output_formatter.py` に fields フィルタリングテスト追加

### Phase 3: スキーマ定義 + `lr schema` コマンド

**新規ファイル**: `lightroom_sdk/schema.py`, `cli/schema.py`

- `lightroom_sdk/schema.py` に全107コマンドのスキーマ定義
- `lr schema` / `lr schema <group>` / `lr schema <group>.<command>` の3段階 introspection
- スキーマ定義は段階的に追加可能（未定義コマンドはバリデーションスキップ）

**テスト追加**:
- `tests/test_schema.py` — スキーマ定義の整合性テスト
- `tests/test_cli_schema.py` — CLI schema コマンドテスト

### Phase 4: 入力バリデーション

**新規ファイル**: `cli/validation.py`

- バリデーションは CLI 層のコマンド実行前に呼び出す
- 初期は主要コマンド（develop.set, catalog.setRating 等の mutating 系）から適用
- スキーマ未定義のコマンドはバリデーションスキップ（段階的移行）

**実装方法**: 既存コマンドの `bridge.send_command()` 呼び出し前に `validate_params()` を挿入

```python
# Before (既存)
result = await bridge.send_command("develop.setValue", {"parameter": param, "value": value})

# After (バリデーション追加)
from cli.validation import validate_params
validated = validate_params("develop.setValue", {"parameter": param, "value": value})
result = await bridge.send_command("develop.setValue", validated)
```

**テスト追加**:
- `tests/test_validation.py` — パラメータ名チェック、型チェック、類似候補提案

### Phase 5: `--dry-run` 全 mutating コマンド拡大

**新規ファイル**: `cli/decorators.py`

- スキーマの `mutating=True` なコマンドに `@dry_run_support` デコレータを付与
- 既存の `ai batch --dry-run` はそのまま動作（互換性維持）
- dry-run 時の出力は JSON 構造化（コマンド名、パラメータ、対象を含む）

**適用対象（mutating コマンドの例）**:
- `develop set`, `develop apply`, `develop auto-tone`, `develop reset*`
- `catalog set-rating`, `catalog add-keywords`, `catalog set-flag`, `catalog set-title`, `catalog set-caption`, `catalog set-color-label`, `catalog remove-from-catalog`
- `selection flag`, `selection reject`, `selection set-rating`, `selection color-label`

**テスト追加**:
- `tests/test_decorators.py` — dry-run 動作テスト

### Phase 6: SKILLS.md 微調整

- Agent-first のデフォルト動作を反映（`-o json` が不要になる旨）
- `lr schema` コマンドの使い方を追記
- `--fields`, `--dry-run` の使い方を追記
- 環境変数セクションの拡充

---

## エラーハンドリング方針

### 構造化エラー出力

全エラーは JSON 構造で返す（非 TTY 時）:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Unknown parameter 'Exposre' for command 'develop.setValue'",
    "suggestions": ["Exposure"],
    "command": "develop.setValue"
  }
}
```

### エラー階層

```
LightroomSDKError (base)
├── ConnectionError        — 接続失敗
├── TimeoutError           — タイムアウト
├── ParameterError         — パラメータ不正
│   ├── ParameterOutOfRangeError  — 範囲外（Lua側で検出）
│   └── ValidationError          — NEW: スキーマバリデーション失敗
├── PhotoNotSelectedError  — 写真未選択
├── PhotoNotFoundError     — 写真不存在
└── ...
```

### 終了コード

| コード | 意味 |
|--------|------|
| 0 | 成功 |
| 1 | 一般エラー |
| 2 | バリデーションエラー（パラメータ不正） |
| 3 | 接続エラー |
| 4 | タイムアウト |

**実装**: `cli/main.py` でグローバル例外ハンドラを追加

```python
@cli.result_callback()
def handle_result(result, **kwargs):
    pass  # Click の正常終了

# グローバル例外ハンドリングは各コマンドの try/except を統一ヘルパーに集約
def execute_command(ctx, command, params, *, timeout=None):
    """共通コマンド実行ヘルパー（エラーハンドリング統一）"""
    fmt = ctx.obj.get("output", "text")
    fields = ctx.obj.get("fields")
    timeout = timeout or ctx.obj.get("timeout", 30.0)

    async def _run():
        bridge = get_bridge()
        try:
            # バリデーション
            validated = validate_params(command, params)
            result = await bridge.send_command(command, validated, timeout=timeout)
            data = result.get("result", result)
            click.echo(OutputFormatter.format(data, fmt, fields=fields))
        except ValidationError as e:
            click.echo(OutputFormatter.format_error(str(e), fmt), err=True)
            ctx.exit(2)
        except ConnectionError as e:
            click.echo(OutputFormatter.format_error(str(e), fmt), err=True)
            ctx.exit(3)
        except TimeoutError as e:
            click.echo(OutputFormatter.format_error(str(e), fmt), err=True)
            ctx.exit(4)
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e), fmt), err=True)
            ctx.exit(1)
        finally:
            await bridge.disconnect()

    run_async(_run())
```

---

## テスト戦略

### テスト構成

| カテゴリ | ファイル | テスト数（見込み） |
|----------|----------|-------------------|
| ミドルウェア | `tests/test_middleware.py` | 10-15 |
| バリデーション | `tests/test_validation.py` | 20-25 |
| スキーマ | `tests/test_schema.py` | 15-20 |
| OutputFormatter拡張 | `tests/test_output_formatter.py`（追加） | 5-10 |
| デコレータ | `tests/test_decorators.py` | 10-15 |
| CLI schema コマンド | `tests/test_cli_schema.py` | 10-15 |
| 既存テスト | 変更なし | 215（全パス維持） |

### テスト方針

1. **既存215件は壊さない** — 各 Phase 完了時に `pytest tests/` 全パスを確認
2. **ミドルウェアは環境変数モック** — `monkeypatch.setenv()` でテスト
3. **TTY検出はモック** — `monkeypatch.setattr(sys.stdout, "isatty", lambda: True/False)`
4. **バリデーションは独立テスト** — bridge 接続不要、純粋なロジックテスト
5. **スキーマの整合性テスト** — 「COMMAND_SCHEMAS の全エントリが有効なコマンド名を持つ」「全 ParamType が正しい」等

### 回帰テスト確認手順

各 Phase のマージ前:
```bash
# 1. 既存テスト全パス
python -m pytest tests/ -v

# 2. 新規テストパス
python -m pytest tests/test_middleware.py tests/test_validation.py tests/test_schema.py -v

# 3. CLI コマンドの動作確認（Lightroom 不要）
lr schema
lr schema develop
lr schema develop.set
lr --help  # --fields, --output のデフォルト確認
```

---

## 既存コマンド移行戦略

### 原則: 既存コマンドのシグネチャは変更しない

107コマンドを一括変更するのではなく、横断的機能（TTY検出、`--fields`、`--dry-run`）をミドルウェアとデコレータで追加する。

### Phase 別の移行計画

| Phase | 対象 | 既存コマンドへの変更 |
|-------|------|---------------------|
| 1 | TTY検出 + 環境変数 | `main.py` のみ。コマンド本体は変更なし |
| 2 | `--fields` | `main.py` にグローバルオプション追加。各コマンドの `OutputFormatter.format()` 呼び出しに `fields` パラメータ追加（107箇所、sed で一括置換可能） |
| 3 | `lr schema` | 新規コマンド追加のみ。既存コマンド変更なし |
| 4 | バリデーション | mutating コマンドの `send_command()` 前に `validate_params()` を挿入。段階的に適用（最初は develop.set, catalog.setRating の2コマンドから開始） |
| 5 | `--dry-run` | mutating コマンドに `@dry_run_support` デコレータ付与。段階的に適用 |
| 6 | SKILLS.md | ドキュメント変更のみ |

### ボイラープレート削減（Phase 4-5 と並行）

現在の全コマンドで重複している以下のパターンを `execute_command()` ヘルパーに集約する:

```python
# Before（各コマンドで30行前後のボイラープレート）
@develop.command("get-settings")
@click.pass_context
def get_settings(ctx):
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.getSettings", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()
    run_async(_run())

# After（5行）
@develop.command("get-settings")
@click.pass_context
def get_settings(ctx):
    """Get all current develop settings"""
    execute_command(ctx, "develop.getSettings", {})
```

この集約は Phase 4-5 のバリデーション・dry-run 導入と同時に行うことで、変更回数を最小化する。

### 移行の安全策

1. **feature flag なし** — 各 Phase が独立しており、コードレベルで ON/OFF する必要がない
2. **スキーマ未定義コマンドはバリデーションスキップ** — 全107コマンドのスキーマを書き終える前にリリース可能
3. **`execute_command()` 移行は optional** — 既存の try/except パターンでも動作する。段階的に移行

---

## 不確実な点・要確認事項

### 1. スキーマ定義の粒度

107コマンド全てのスキーマを初期リリースまでに定義するか、主要コマンド（mutating 系 + 高頻度利用）のみを先行するか。

**推奨**: 主要30コマンド（develop.*, catalog.* の mutating 系）を先行定義。残りは v0.3.1 で追加。

### 2. `--fields` のネストフィールド対応

```bash
# フラットなフィールド
lr -o json --fields "fileName,rating" catalog get-info PHOTO_ID

# ネストフィールド（要対応?）
lr -o json --fields "metadata.fileName,develop.Exposure" catalog get-info PHOTO_ID
```

**推奨**: 初期はトップレベルフィールドのみ対応。ネストフィールドは需要が確認されてから追加。

### 3. `--json` 入力の設計（Codex×Opus 討論で合意済み）

**合意案**: `--json` オプションを全コマンドに追加し、既存フラグは互換維持（段階的非推奨化パス）。

- `--json` が指定された場合、他の位置引数/フラグは無視し、JSONから全パラメータを取得
- `--json-stdin` も追加し、stdinからJSON入力を受け付ける（長大JSON対応）
- 既存フラグはそのまま動作（テスト215件維持）
- SKILLS.md にはJSON形式のみ推奨として記載（エージェントには新方式だけ教える）
- 将来のPhaseで旧形式の deprecated 警告 → 廃止を検討

**根拠**:
- AIエージェントは subprocess リスト渡しするため、シェルエスケープ問題は発生しない
- 既に `--adjust`, `--settings` 等でJSON引数を受け取るコマンドが存在し、運用上問題なし
- JSONスキーマベースのツール呼び出しは OpenAI function calling / Anthropic tool use と同型

### 4. TTY検出の CI 環境での挙動

GitHub Actions や他の CI 環境では `sys.stdout.isatty()` が `False` を返すため、自動的に JSON 出力になる。これは意図通りだが、既存の CI テストが text 出力前提で書かれている場合は修正が必要。

**対応**: テストコード内で `ctx.obj["output"] = "text"` を明示設定しているため、影響なし。

### 5. `execute_command()` への一括移行タイミング

107コマンドのボイラープレートを `execute_command()` に移行するタイミング。Phase 4-5 と同時に行うと差分が大きくなる。

**推奨**: Phase 4 で mutating コマンド（約30コマンド）を移行、Phase 5 で残りを移行。各 Phase で `pytest` 全パスを確認。

---

## 実装スケジュール（見込み）

| Phase | 所要時間 | 依存関係 |
|-------|----------|----------|
| Phase 1: TTY + 環境変数 | 30分 | なし |
| Phase 2: --fields | 30分 | Phase 1 |
| Phase 3: lr schema + スキーマ定義 | 1-2時間 | なし（並行可能） |
| Phase 4: 入力バリデーション | 1時間 | Phase 3（スキーマ定義） |
| Phase 5: --dry-run 全mutating | 30分 | Phase 3 |
| Phase 6: --json 入力統一 | 1-2時間 | Phase 3（スキーマ定義） |
| Phase 7: SKILLS.md 微調整 | 15分 | Phase 1-6 完了後 |

**合計**: 約5-7時間

---

## まとめ

Layered Enhancement アプローチにより:

- **既存215テストを壊さず** に Agent-first 機能を追加
- **TTY検出で自動 JSON 出力** — エージェントは `-o json` 不要に
- **スキーマ introspection** でエージェントがコマンドを自己発見
- **入力バリデーション** でハルシネーション対策
- **`--fields`** で context window 節約
- **`--dry-run`** で安全な事前確認
- **将来のスキーマ駆動 Big Rewrite** への自然な移行パスを確保
