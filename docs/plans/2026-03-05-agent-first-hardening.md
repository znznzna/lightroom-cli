# Agent-First Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** エージェントファーストCLI設計原則に基づくP1+P2 7項目の堅牢化
**Architecture:** validation.py/schema.pyの拡張 + output.pyサニタイズ層 + SKILLS.md改善
**Tech Stack:** Python 3.10+, Click 8.x, pytest
---

## 実装順序

```
P1-1 (min/max) → P1-2 (sanitize) → P1-3 (cli_constraints)
                                         ↓
P2-6 (risk_level, cli_constraints 依存) → P2-5 (output sanitize)
                                         ↓
P2-7 (schema_hash) → P2-4 (SKILLS.md, 最後)
```

---

## Task 1: validate_params() に min/max 範囲チェック追加

**Files:**
- Modify: `cli/validation.py`
- Test: `tests/test_validation_range.py`

**Step 1: 失敗するテストを書く**

Create `tests/test_validation_range.py`:

```python
"""Tests for min/max range validation in _coerce_type()."""
import pytest
from cli.validation import validate_params, ValidationError


class TestRangeValidation:
    """min/max 範囲チェックのテスト"""

    def test_integer_below_min_raises(self):
        """min より小さい整数値は ValidationError"""
        with pytest.raises(ValidationError, match="below minimum"):
            validate_params("catalog.setRating", {"photoId": "123", "rating": -1})

    def test_integer_above_max_raises(self):
        """max より大きい整数値は ValidationError"""
        with pytest.raises(ValidationError, match="above maximum"):
            validate_params("catalog.setRating", {"photoId": "123", "rating": 6})

    def test_integer_at_min_boundary_passes(self):
        """min 境界値は通る"""
        result = validate_params("catalog.setRating", {"photoId": "123", "rating": 0})
        assert result["rating"] == 0

    def test_integer_at_max_boundary_passes(self):
        """max 境界値は通る"""
        result = validate_params("catalog.setRating", {"photoId": "123", "rating": 5})
        assert result["rating"] == 5

    def test_integer_within_range_passes(self):
        """範囲内の値は通る"""
        result = validate_params("catalog.setRating", {"photoId": "123", "rating": 3})
        assert result["rating"] == 3

    def test_no_min_max_skips_check(self):
        """min/max 未定義のパラメータはチェックスキップ"""
        result = validate_params(
            "develop.setValue",
            {"parameter": "Exposure", "value": 99999.0}
        )
        assert result["value"] == 99999.0

    def test_range_error_has_suggestions(self):
        """範囲エラー時に suggestions が含まれる"""
        with pytest.raises(ValidationError) as exc_info:
            validate_params("catalog.setRating", {"photoId": "123", "rating": 10})
        assert len(exc_info.value.suggestions) > 0
        assert "0" in exc_info.value.suggestions[0]
        assert "5" in exc_info.value.suggestions[0]

    def test_string_coerced_then_range_checked(self):
        """文字列 → int 変換後に範囲チェック（--json 経由のシナリオ）"""
        with pytest.raises(ValidationError, match="above maximum"):
            validate_params("catalog.setRating", {"photoId": "123", "rating": "10"})

    def test_selection_set_rating_range(self):
        """selection.setRating も同じ min/max チェック"""
        with pytest.raises(ValidationError, match="below minimum"):
            validate_params("selection.setRating", {"rating": -1})
        result = validate_params("selection.setRating", {"rating": 3})
        assert result["rating"] == 3
```

**Step 2: 失敗を確認**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_validation_range.py -v`
Expected: FAIL (test_integer_below_min_raises 等が失敗 — _coerce_type に range チェックがないため)

**Step 3: 最小限の実装**

Modify `cli/validation.py` — `_coerce_type()` 関数の変更と `_check_range()` 関数の追加:

`_check_range()` をファイル末尾（`_find_similar()` の前）に追加:

```python
def _check_range(name: str, value: int | float, schema: ParamSchema) -> None:
    """min/max 範囲チェック。違反時は ValidationError。"""
    if schema.min is not None and value < schema.min:
        raise ValidationError(
            f"Value {value} for '{name}' is below minimum {schema.min}",
            param=name,
            suggestions=[f"Valid range: {schema.min} to {schema.max}"],
        )
    if schema.max is not None and value > schema.max:
        raise ValidationError(
            f"Value {value} for '{name}' is above maximum {schema.max}",
            param=name,
            suggestions=[f"Valid range: {schema.min} to {schema.max}"],
        )
```

`_coerce_type()` の INTEGER/FLOAT case を以下に変更:

```python
case ParamType.INTEGER:
    result = int(value)
    _check_range(name, result, schema)
    return result
case ParamType.FLOAT:
    result = float(value)
    _check_range(name, result, schema)
    return result
```

変更後の `_coerce_type()` 関数全体:

```python
def _coerce_type(name: str, value: object, schema: ParamSchema) -> object:
    """型変換を試みる。失敗時は ValidationError。"""
    try:
        match schema.type:
            case ParamType.STRING:
                return str(value)
            case ParamType.INTEGER:
                result = int(value)
                _check_range(name, result, schema)
                return result
            case ParamType.FLOAT:
                result = float(value)
                _check_range(name, result, schema)
                return result
            case ParamType.BOOLEAN:
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    lower = value.lower()
                    if lower in ("true", "1", "yes"):
                        return True
                    if lower in ("false", "0", "no"):
                        return False
                    raise ValidationError(
                        f"Invalid value '{value}' for '{name}': "
                        f"expected boolean (true/false/yes/no/1/0)",
                        param=name,
                    )
                return bool(value)
            case ParamType.JSON_OBJECT:
                if not isinstance(value, dict):
                    raise ValidationError(
                        f"Invalid type for '{name}': expected JSON object (dict), "
                        f"got {type(value).__name__}",
                        param=name,
                    )
                return value
            case ParamType.JSON_ARRAY:
                if not isinstance(value, list):
                    raise ValidationError(
                        f"Invalid type for '{name}': expected JSON array (list), "
                        f"got {type(value).__name__}",
                        param=name,
                    )
                return value
            case ParamType.ENUM:
                if str(value) not in (schema.enum_values or []):
                    raise ValidationError(
                        f"Invalid value '{value}' for '{name}'. "
                        f"Must be one of: {', '.join(schema.enum_values or [])}",
                        param=name,
                        suggestions=[f"Valid values: {', '.join(schema.enum_values or [])}"],
                    )
                return str(value)
            case _:
                return value
    except ValidationError:
        raise
    except (ValueError, TypeError):
        type_examples = {
            ParamType.STRING: 'e.g., "hello"',
            ParamType.INTEGER: "e.g., 42",
            ParamType.FLOAT: "e.g., 0.5, -1.0",
            ParamType.BOOLEAN: "e.g., true, false",
        }
        example = type_examples.get(schema.type, "")
        suggestions = [f"Expected type: {schema.type.value} ({example})"] if example else [f"Expected type: {schema.type.value}"]
        raise ValidationError(
            f"Invalid type for '{name}': expected {schema.type.value}, "
            f"got {type(value).__name__}",
            param=name,
            suggestions=suggestions,
        )
```

**Step 4: 通過を確認**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_validation_range.py -v`
Expected: PASS

**Step 5: リグレッションテスト**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/ -v`
Expected: 全 744+ 件 PASS

**Step 6: コミット**

```bash
git add cli/validation.py tests/test_validation_range.py
git commit -m "feat: add min/max range validation to _coerce_type() (P1-1)"
```

---

## Task 2: 文字列入力の基本サニタイズ

**Files:**
- Modify: `cli/validation.py`
- Test: `tests/test_validation_sanitize.py`

**Step 1: 失敗するテストを書く**

Create `tests/test_validation_sanitize.py`:

```python
"""Tests for string input sanitization in _coerce_type()."""
import pytest
from cli.validation import validate_params, ValidationError


class TestStringSanitization:
    """文字列サニタイズのテスト"""

    def test_null_char_rejected(self):
        """NUL 文字を含む文字列は reject"""
        with pytest.raises(ValidationError, match="null character"):
            validate_params(
                "develop.setValue",
                {"parameter": "Exposure\x00", "value": 0.5}
            )

    def test_control_char_rejected(self):
        """制御文字（\x01）を含む文字列は reject"""
        with pytest.raises(ValidationError, match="control characters"):
            validate_params(
                "develop.setValue",
                {"parameter": "Exposure\x01", "value": 0.5}
            )

    def test_bell_char_rejected(self):
        """ベル文字（\x07）を含む文字列は reject"""
        with pytest.raises(ValidationError, match="control characters"):
            validate_params(
                "develop.setValue",
                {"parameter": "\x07Exposure", "value": 0.5}
            )

    def test_del_char_rejected(self):
        """DEL 文字（\x7f）を含む文字列は reject"""
        with pytest.raises(ValidationError, match="control characters"):
            validate_params(
                "develop.setValue",
                {"parameter": "Exposure\x7f", "value": 0.5}
            )

    def test_tab_allowed(self):
        """タブ文字は許可"""
        result = validate_params(
            "develop.setValue",
            {"parameter": "Exposure\t", "value": 0.5}
        )
        assert "\t" in result["parameter"]

    def test_newline_allowed(self):
        """改行文字は許可"""
        result = validate_params(
            "catalog.setTitle",
            {"photoId": "123", "title": "line1\nline2"}
        )
        assert "\n" in result["title"]

    def test_carriage_return_allowed(self):
        """CR は許可"""
        result = validate_params(
            "catalog.setTitle",
            {"photoId": "123", "title": "line1\rline2"}
        )
        assert "\r" in result["title"]

    def test_normal_string_passes(self):
        """通常の文字列は通る"""
        result = validate_params(
            "develop.setValue",
            {"parameter": "Exposure", "value": 0.5}
        )
        assert result["parameter"] == "Exposure"

    def test_unicode_string_passes(self):
        """Unicode 文字列は通る"""
        result = validate_params(
            "catalog.setTitle",
            {"photoId": "123", "title": "写真タイトル 🌅"}
        )
        assert result["title"] == "写真タイトル 🌅"

    def test_overlong_string_rejected(self):
        """10,000 文字超の文字列は reject"""
        long_str = "a" * 10_001
        with pytest.raises(ValidationError, match="exceeds maximum length"):
            validate_params(
                "develop.setValue",
                {"parameter": long_str, "value": 0.5}
            )

    def test_exactly_max_length_passes(self):
        """ちょうど 10,000 文字は通る"""
        exact_str = "a" * 10_000
        result = validate_params(
            "develop.setValue",
            {"parameter": exact_str, "value": 0.5}
        )
        assert len(result["parameter"]) == 10_000

    def test_sanitize_error_has_suggestions(self):
        """制御文字エラー時に suggestions が含まれる"""
        with pytest.raises(ValidationError) as exc_info:
            validate_params(
                "develop.setValue",
                {"parameter": "\x01bad", "value": 0.5}
            )
        assert len(exc_info.value.suggestions) > 0
```

**Step 2: 失敗を確認**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_validation_sanitize.py -v`
Expected: FAIL

**Step 3: 最小限の実装**

Modify `cli/validation.py` — ファイル冒頭に `import re` を追加し、定数と `_sanitize_string()` 関数を追加。STRING case を変更。

ファイル冒頭の import を以下に変更:

```python
"""Input validation based on command schemas."""
from __future__ import annotations
import re
from lightroom_sdk.schema import get_schema, ParamType, ParamSchema
```

`_check_range()` の前（`_coerce_type()` の後）に定数と関数を追加:

```python
_MAX_STRING_LENGTH = 10_000
_CONTROL_CHAR_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def _sanitize_string(name: str, value: str) -> str:
    """制御文字 reject、NUL reject、過長 reject。"""
    if '\x00' in value:
        raise ValidationError(
            f"Parameter '{name}' contains null character",
            param=name,
            suggestions=["Remove null characters from the value"],
        )
    if _CONTROL_CHAR_RE.search(value):
        raise ValidationError(
            f"Parameter '{name}' contains control characters",
            param=name,
            suggestions=["Remove non-printable characters from the value"],
        )
    if len(value) > _MAX_STRING_LENGTH:
        raise ValidationError(
            f"Parameter '{name}' exceeds maximum length ({len(value)} > {_MAX_STRING_LENGTH})",
            param=name,
            suggestions=[f"Maximum string length is {_MAX_STRING_LENGTH} characters"],
        )
    return value
```

`_coerce_type()` の STRING case を変更:

```python
case ParamType.STRING:
    s = str(value)
    return _sanitize_string(name, s)
```

**Step 4: 通過を確認**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_validation_sanitize.py -v`
Expected: PASS

**Step 5: リグレッションテスト**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/ -v`
Expected: 全件 PASS

**Step 6: コミット**

```bash
git add cli/validation.py tests/test_validation_sanitize.py
git commit -m "feat: add string sanitization to _coerce_type() (P1-2)"
```

---

## Task 3: CommandSchema に supports_dry_run / requires_confirm フィールド追加

**Files:**
- Modify: `lightroom_sdk/schema.py`
- Test: `tests/test_schema_cli_constraints.py`

**Step 1: 失敗するテストを書く**

Create `tests/test_schema_cli_constraints.py`:

```python
"""Tests for CommandSchema cli_constraints fields."""
import pytest
from lightroom_sdk.schema import CommandSchema, ParamSchema, ParamType, get_schema


class TestCliConstraintsFields:
    """supports_dry_run / requires_confirm フィールドのテスト"""

    def test_default_values_false(self):
        """デフォルト値は False"""
        schema = CommandSchema(
            command="test.cmd", cli_path="test.cmd",
            description="test",
        )
        assert schema.supports_dry_run is False
        assert schema.requires_confirm is False

    def test_explicit_values(self):
        """明示的に True を設定"""
        schema = CommandSchema(
            command="test.cmd", cli_path="test.cmd",
            description="test",
            supports_dry_run=True,
            requires_confirm=True,
        )
        assert schema.supports_dry_run is True
        assert schema.requires_confirm is True


class TestRiskLevelProperty:
    """risk_level プロパティのテスト"""

    def test_read_command_risk_level(self):
        """mutating=False → 'read'"""
        schema = CommandSchema(
            command="test.cmd", cli_path="test.cmd",
            description="test", mutating=False,
        )
        assert schema.risk_level == "read"

    def test_write_command_risk_level(self):
        """mutating=True, requires_confirm=False → 'write'"""
        schema = CommandSchema(
            command="test.cmd", cli_path="test.cmd",
            description="test", mutating=True,
        )
        assert schema.risk_level == "write"

    def test_destructive_command_risk_level(self):
        """requires_confirm=True → 'destructive'"""
        schema = CommandSchema(
            command="test.cmd", cli_path="test.cmd",
            description="test", mutating=True, requires_confirm=True,
        )
        assert schema.risk_level == "destructive"

    def test_requires_confirm_without_mutating(self):
        """requires_confirm=True で mutating=False でも 'destructive'"""
        schema = CommandSchema(
            command="test.cmd", cli_path="test.cmd",
            description="test", mutating=False, requires_confirm=True,
        )
        assert schema.risk_level == "destructive"


class TestRegisteredSchemaConstraints:
    """登録済みスキーマの cli_constraints テスト"""

    def test_remove_from_catalog_requires_confirm(self):
        schema = get_schema("catalog.removeFromCatalog")
        assert schema is not None
        assert schema.requires_confirm is True
        assert schema.risk_level == "destructive"

    def test_ai_reset_requires_confirm(self):
        schema = get_schema("develop.ai.reset")
        assert schema is not None
        assert schema.requires_confirm is True
        assert schema.risk_level == "destructive"

    def test_develop_set_value_supports_dry_run(self):
        schema = get_schema("develop.setValue")
        assert schema is not None
        assert schema.supports_dry_run is True
        assert schema.risk_level == "write"

    def test_system_ping_is_read(self):
        schema = get_schema("system.ping")
        assert schema is not None
        assert schema.supports_dry_run is False
        assert schema.requires_confirm is False
        assert schema.risk_level == "read"

    def test_catalog_set_rating_supports_dry_run(self):
        schema = get_schema("catalog.setRating")
        assert schema is not None
        assert schema.supports_dry_run is True
```

**Step 2: 失敗を確認**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_schema_cli_constraints.py -v`
Expected: FAIL (CommandSchema に supports_dry_run / requires_confirm フィールドがないため)

**Step 3: 最小限の実装**

Modify `lightroom_sdk/schema.py`:

3a. `CommandSchema` dataclass にフィールドと property を追加:

```python
@dataclass
class CommandSchema:
    command: str
    cli_path: str
    description: str
    params: list[ParamSchema] = field(default_factory=list)
    mutating: bool = False
    timeout: float = 30.0
    response_fields: list[str] = field(default_factory=list)
    supports_dry_run: bool = False
    requires_confirm: bool = False

    @property
    def risk_level(self) -> str:
        """操作のリスクレベルを導出"""
        if self.requires_confirm:
            return "destructive"
        if self.mutating:
            return "write"
        return "read"
```

3b. 既存スキーマ登録に `supports_dry_run=True` と `requires_confirm=True` を追加。

以下のコマンドに `supports_dry_run=True` を追加（`mutating=True` かつ実際に `--dry-run` が CLI で使えるもの）:

> **C2修正 (Codex指摘)**: `selection.*` / `preview.*` / `develop.ai.*` 等の `--dry-run` 付きコマンドが漏れていた。CLI実装 (`cli/commands/`) で `--dry-run` オプションが付いている全コマンドを網羅する。

**catalog系:**
- `catalog.setRating` — `supports_dry_run=True` を追加
- `catalog.addKeywords` — `supports_dry_run=True` を追加
- `catalog.setFlag` — `supports_dry_run=True` を追加
- `catalog.setTitle` — `supports_dry_run=True` を追加
- `catalog.setCaption` — `supports_dry_run=True` を追加
- `catalog.setColorLabel` — `supports_dry_run=True` を追加
- `catalog.setMetadata` — `supports_dry_run=True` を追加
- `catalog.removeFromCatalog` — `supports_dry_run=True` を追加
- `catalog.removeKeyword` — `supports_dry_run=True` を追加
- `catalog.selectPhotos` — `supports_dry_run=True` を追加
- `catalog.rotateLeft` — `supports_dry_run=True` を追加
- `catalog.rotateRight` — `supports_dry_run=True` を追加
- `catalog.createVirtualCopy` — `supports_dry_run=True` を追加
- `catalog.createCollection` — `supports_dry_run=True` を追加
- `catalog.createSmartCollection` — `supports_dry_run=True` を追加
- `catalog.createCollectionSet` — `supports_dry_run=True` を追加
- `catalog.createKeyword` — `supports_dry_run=True` を追加
- `catalog.setViewFilter` — `supports_dry_run=True` を追加

**develop系:**
- `develop.setValue` — `supports_dry_run=True` を追加
- `develop.applySettings` — `supports_dry_run=True` を追加
- `develop.batchApplySettings` — `supports_dry_run=True` を追加
- `develop.setAutoTone` — `supports_dry_run=True` を追加
- `develop.setAutoWhiteBalance` — `supports_dry_run=True` を追加
- `develop.resetAllDevelopAdjustments` — `supports_dry_run=True` を追加
- `develop.applyPreset` — `supports_dry_run=True` を追加
- `develop.createSnapshot` — `supports_dry_run=True` を追加
- `develop.copySettings` — `supports_dry_run=True` を追加
- `develop.pasteSettings` — `supports_dry_run=True` を追加
- `develop.resetParam` — `supports_dry_run=True` を追加
- `develop.setProcessVersion` — `supports_dry_run=True` を追加
- `develop.setCurvePoints` — `supports_dry_run=True` を追加
- `develop.linearCurve` — `supports_dry_run=True` を追加
- `develop.sCurve` — `supports_dry_run=True` を追加
- `develop.addCurvePoint` — `supports_dry_run=True` を追加
- `develop.removeCurvePoint` — `supports_dry_run=True` を追加
- `develop.goToMasking` — `supports_dry_run=True` を追加
- `develop.toggleMaskOverlay` — `supports_dry_run=True` を追加
- `develop.local.set` — `supports_dry_run=True` を追加
- `develop.local.apply` — `supports_dry_run=True` を追加
- `develop.local.createMask` — `supports_dry_run=True` を追加
- `develop.filter.graduated` — `supports_dry_run=True` を追加
- `develop.filter.radial` — `supports_dry_run=True` を追加
- `develop.filter.brush` — `supports_dry_run=True` を追加
- `develop.filter.range` — `supports_dry_run=True` を追加
- `develop.debug.monitor` — `supports_dry_run=True` を追加
- `develop.color.greenSwatch` — `supports_dry_run=True` を追加
- `develop.color.cyanSwatch` — `supports_dry_run=True` を追加
- `develop.color.enhance` — `supports_dry_run=True` を追加
- `develop.reset.gradient` — `supports_dry_run=True` を追加
- `develop.reset.circular` — `supports_dry_run=True` を追加
- `develop.reset.brush` — `supports_dry_run=True` を追加
- `develop.reset.masking` — `supports_dry_run=True` を追加
- `develop.reset.crop` — `supports_dry_run=True` を追加
- `develop.reset.transforms` — `supports_dry_run=True` を追加
- `develop.reset.spot` — `supports_dry_run=True` を追加
- `develop.reset.redeye` — `supports_dry_run=True` を追加
- `develop.reset.healing` — `supports_dry_run=True` を追加
- `develop.editInPhotoshop` — `supports_dry_run=True` を追加

**selection系 (C2追加):**
- `selection.flagAsPick` — `supports_dry_run=True` を追加
- `selection.flagAsReject` — `supports_dry_run=True` を追加
- `selection.removeFlag` — `supports_dry_run=True` を追加
- `selection.setColorLabel` — `supports_dry_run=True` を追加
- `selection.selectAll` — `supports_dry_run=True` を追加
- `selection.selectNone` — `supports_dry_run=True` を追加
- `selection.selectInverse` — `supports_dry_run=True` を追加
- `selection.increaseRating` — `supports_dry_run=True` を追加
- `selection.decreaseRating` — `supports_dry_run=True` を追加
- `selection.toggleColorLabel` — `supports_dry_run=True` を追加
- `selection.extendSelection` — `supports_dry_run=True` を追加
- `selection.deselectActive` — `supports_dry_run=True` を追加
- `selection.deselectOthers` — `supports_dry_run=True` を追加
- `selection.setRating` — `supports_dry_run=True` を追加

**preview系 (C2追加):**
- `preview.generatePreview` — `supports_dry_run=True` を追加
- `preview.generateBatchPreviews` — `supports_dry_run=True` を追加

**develop.ai系 (C2追加):**
- `develop.ai.*` (全AIマスクタイプ) — `supports_dry_run=True` を追加
- `develop.ai.reset` — `supports_dry_run=True` を追加
- `develop.batchAIMask` — `supports_dry_run=True` を追加

以下のコマンドに `requires_confirm=True` を追加:

- `catalog.removeFromCatalog` — `requires_confirm=True` を追加
- `develop.ai.reset` — `requires_confirm=True` を追加

具体的な変更例（`catalog.removeFromCatalog`）:

```python
    CommandSchema(
        "catalog.removeFromCatalog", "catalog.remove-from-catalog",
        "Remove photo from catalog",
        params=[ParamSchema("photoId", ParamType.STRING, required=True,
                            description="Photo ID to remove from catalog")],
        mutating=True, supports_dry_run=True, requires_confirm=True,
    ),
```

具体的な変更例（`develop.ai.reset`）:

```python
    CommandSchema("develop.ai.reset", "develop.ai.reset",
                  "Remove all masks from the current photo",
                  mutating=True, requires_confirm=True),
```

具体的な変更例（`develop.setValue`）:

```python
    CommandSchema(
        "develop.setValue", "develop.set",
        "Set develop parameter(s)",
        params=[
            ParamSchema("parameter", ParamType.STRING, required=True,
                        description="Develop parameter name (e.g., Exposure, Contrast)"),
            ParamSchema("value", ParamType.FLOAT, required=True,
                        description="Parameter value"),
        ],
        mutating=True, supports_dry_run=True, timeout=10.0,
        response_fields=["parameter", "value", "previousValue"],
    ),
```

**Step 4: 通過を確認**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_schema_cli_constraints.py -v`
Expected: PASS

**Step 5: リグレッションテスト**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/ -v`
Expected: 全件 PASS

**Step 6: コミット**

```bash
git add lightroom_sdk/schema.py tests/test_schema_cli_constraints.py
git commit -m "feat: add supports_dry_run/requires_confirm to CommandSchema (P1-3)"
```

---

## Task 4: lr schema 出力に cli_constraints フィールド追加

**Files:**
- Modify: `cli/schema.py`
- Test: `tests/test_cli_schema.py` (既存ファイルにテスト追加)

**Step 1: 失敗するテストを書く**

`tests/test_cli_schema.py` の末尾に以下のクラスを追加:

```python
class TestSchemaCliConstraints:
    """lr schema 出力の cli_constraints フィールドテスト"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_schema_detail_includes_supports_dry_run(self, runner):
        result = runner.invoke(cli, ["-o", "json", "schema", "develop.set"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "supports_dry_run" in data
        assert data["supports_dry_run"] is True

    def test_schema_detail_includes_requires_confirm(self, runner):
        result = runner.invoke(cli, ["-o", "json", "schema", "catalog.remove-from-catalog"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "requires_confirm" in data
        assert data["requires_confirm"] is True

    def test_schema_detail_includes_risk_level(self, runner):
        result = runner.invoke(cli, ["-o", "json", "schema", "develop.set"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "risk_level" in data
        assert data["risk_level"] == "write"

    def test_schema_detail_read_risk_level(self, runner):
        result = runner.invoke(cli, ["-o", "json", "schema", "system.ping"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["risk_level"] == "read"

    def test_schema_detail_destructive_risk_level(self, runner):
        result = runner.invoke(cli, ["-o", "json", "schema", "catalog.remove-from-catalog"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["risk_level"] == "destructive"
```

**Step 2: 失敗を確認**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_cli_schema.py::TestSchemaCliConstraints -v`
Expected: FAIL (schema 出力に supports_dry_run 等がない)

**Step 3: 最小限の実装**

Modify `cli/schema.py` — `detail` dict にフィールドを追加。

変更後の detail 部分（`schema_cmd` 関数内の `detail = {` から `click.echo(OutputFormatter.format(detail, fmt))` まで）:

```python
        detail = {
            "command": target.cli_path,
            "bridge_command": target.command,
            "description": target.description,
            "mutating": target.mutating,
            "supports_dry_run": target.supports_dry_run,
            "requires_confirm": target.requires_confirm,
            "risk_level": target.risk_level,
            "timeout": target.timeout,
            "params": [
                {
                    "name": p.name,
                    "type": p.type.value,
                    "required": p.required,
                    "description": p.description,
                    **({"default": p.default} if p.default is not None else {}),
                    **({"enum_values": p.enum_values} if p.enum_values else {}),
                    **({"min": p.min} if p.min is not None else {}),
                    **({"max": p.max} if p.max is not None else {}),
                }
                for p in target.params
            ],
            "response_fields": target.response_fields,
        }
        click.echo(OutputFormatter.format(detail, fmt))
```

**Step 4: 通過を確認**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_cli_schema.py -v`
Expected: PASS

**Step 5: リグレッションテスト**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/ -v`
Expected: 全件 PASS

**Step 6: コミット**

```bash
git add cli/schema.py tests/test_cli_schema.py
git commit -m "feat: expose cli_constraints and risk_level in lr schema output (P1-3 cont.)"
```

---

## Task 5: --dry-run 出力に risk_level フィールド追加

**Files:**
- Modify: `cli/helpers.py`
- Modify: `cli/decorators.py`
- Test: `tests/test_dry_run_risk_level.py`

**Step 1: 失敗するテストを書く**

Create `tests/test_dry_run_risk_level.py`:

```python
"""Tests for risk_level field in --dry-run output."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestDryRunRiskLevelInExecuteCommand:
    """execute_command() の dry-run に risk_level が含まれるテスト"""

    def _make_ctx(self, **overrides):
        ctx = MagicMock()
        ctx.obj = {"output": "json", "timeout": 30.0, "fields": None}
        ctx.params = {"dry_run": True}
        for k, v in overrides.items():
            if k == "obj":
                ctx.obj = v
            elif k == "params":
                ctx.params = v
            else:
                setattr(ctx, k, v)
        return ctx

    def test_dry_run_includes_risk_level_write(self):
        from cli.helpers import execute_command
        mock_ctx = self._make_ctx()

        with patch("click.echo") as mock_echo:
            execute_command(mock_ctx, "develop.setValue", {"parameter": "Exposure", "value": 0.5})

        output = mock_echo.call_args[0][0]
        data = json.loads(output)
        assert data["risk_level"] == "write"

    def test_dry_run_includes_risk_level_read(self):
        from cli.helpers import execute_command
        mock_ctx = self._make_ctx()

        with patch("click.echo") as mock_echo:
            execute_command(mock_ctx, "system.ping", {})

        output = mock_echo.call_args[0][0]
        data = json.loads(output)
        assert data["risk_level"] == "read"

    def test_dry_run_includes_risk_level_destructive(self):
        from cli.helpers import execute_command
        mock_ctx = self._make_ctx()

        with patch("click.echo") as mock_echo:
            execute_command(mock_ctx, "catalog.removeFromCatalog", {"photoId": "123"})

        output = mock_echo.call_args[0][0]
        data = json.loads(output)
        assert data["risk_level"] == "destructive"

    def test_dry_run_unknown_command_risk_level_none(self):
        from cli.helpers import execute_command
        mock_ctx = self._make_ctx()

        with patch("click.echo") as mock_echo:
            execute_command(mock_ctx, "unknown.cmd", {"foo": "bar"})

        output = mock_echo.call_args[0][0]
        data = json.loads(output)
        assert data["risk_level"] is None


class TestDryRunGuardRiskLevel:
    """dry_run_guard() の risk_level テスト"""

    def test_guard_includes_risk_level(self):
        import click
        from cli.decorators import dry_run_guard
        from click.testing import CliRunner

        @click.group()
        @click.pass_context
        def test_group(ctx):
            ctx.ensure_object(dict)
            ctx.obj["output"] = "json"

        @test_group.command("test-cmd")
        @click.option("--dry-run", is_flag=True, default=False)
        @click.pass_context
        def test_cmd(ctx, dry_run):
            preview = dry_run_guard(ctx, command="develop.setValue", params={"parameter": "Exposure"})
            if preview:
                return
            click.echo("executed")

        runner = CliRunner()
        result = runner.invoke(test_group, ["test-cmd", "--dry-run"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "risk_level" in data
        assert data["risk_level"] == "write"
```

**Step 2: 失敗を確認**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_dry_run_risk_level.py -v`
Expected: FAIL

**Step 3: 最小限の実装**

Modify `cli/helpers.py` — `execute_command()` 内の dry-run ブロックを変更:

```python
    # dry-run チェック
    if getattr(ctx, "params", {}).get("dry_run", False):
        from lightroom_sdk.schema import get_schema
        schema = get_schema(command)
        preview = {
            "dry_run": True,
            "command": command,
            "mutating": schema.mutating if schema else None,
            "risk_level": schema.risk_level if schema else None,
            "params": {k: v for k, v in params.items() if v is not None},
        }
        click.echo(OutputFormatter.format(preview, fmt))
        return
```

Modify `cli/decorators.py` — `dry_run_guard()` 関数全体を変更:

```python
def dry_run_guard(
    ctx: click.Context,
    *,
    command: str,
    params: dict,
) -> bool:
    """dry-run ガード。--dry-run が指定されていればプレビューを出力して True を返す。"""
    dry_run = ctx.params.get("dry_run", False)
    if not dry_run:
        return False

    from lightroom_sdk.schema import get_schema
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
    schema = get_schema(command)
    preview = {
        "dry_run": True,
        "command": command,
        "risk_level": schema.risk_level if schema else None,
        "params": {k: v for k, v in params.items() if v is not None},
    }
    click.echo(OutputFormatter.format(preview, fmt))
    return True
```

**Step 4: 通過を確認**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_dry_run_risk_level.py -v`
Expected: PASS

**Step 5: リグレッションテスト**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/ -v`
Expected: 全件 PASS

**Step 6: コミット**

```bash
git add cli/helpers.py cli/decorators.py tests/test_dry_run_risk_level.py
git commit -m "feat: add risk_level to --dry-run output (P2-6)"
```

---

## Task 6: OutputFormatter にサニタイズ層追加

**Files:**
- Modify: `cli/output.py`
- Test: `tests/test_output_sanitize.py`

**Step 1: 失敗するテストを書く**

Create `tests/test_output_sanitize.py`:

```python
"""Tests for OutputFormatter output sanitization."""
import json
import pytest
from cli.output import OutputFormatter


class TestOutputSanitize:
    """出力サニタイズのテスト"""

    def test_control_chars_stripped_from_string(self):
        """制御文字が出力から除去される"""
        data = {"name": "hello\x00world\x07test"}
        result = OutputFormatter.format(data, "json")
        parsed = json.loads(result)
        assert "\x00" not in parsed["name"]
        assert "\x07" not in parsed["name"]
        assert "helloworld" in parsed["name"]

    def test_tab_newline_preserved(self):
        """タブ・改行は保持される"""
        data = {"text": "line1\nline2\ttab"}
        result = OutputFormatter.format(data, "json")
        parsed = json.loads(result)
        assert "\n" in parsed["text"]
        assert "\t" in parsed["text"]

    def test_nested_dict_sanitized(self):
        """ネストした dict も再帰サニタイズ"""
        data = {"outer": {"inner": "val\x01ue"}}
        result = OutputFormatter.format(data, "json")
        parsed = json.loads(result)
        assert "\x01" not in parsed["outer"]["inner"]
        assert parsed["outer"]["inner"] == "value"

    def test_list_sanitized(self):
        """リスト内の文字列もサニタイズ"""
        data = [{"name": "test\x02"}, {"name": "ok"}]
        result = OutputFormatter.format(data, "json")
        parsed = json.loads(result)
        assert parsed[0]["name"] == "test"
        assert parsed[1]["name"] == "ok"

    def test_non_string_values_unchanged(self):
        """数値・bool はそのまま"""
        data = {"count": 42, "active": True, "value": 3.14}
        result = OutputFormatter.format(data, "json")
        parsed = json.loads(result)
        assert parsed["count"] == 42
        assert parsed["active"] is True
        assert parsed["value"] == 3.14

    def test_overlong_string_truncated_in_json_mode(self):
        """C3修正: 50,000 文字超の文字列は json モードのみ truncate"""
        long_str = "a" * 60_000
        data = {"content": long_str}
        result = OutputFormatter.format(data, "json")
        parsed = json.loads(result)
        assert len(parsed["content"]) < 60_000
        assert "truncated" in parsed["content"]
        assert "60000" in parsed["content"]

    def test_overlong_string_not_truncated_in_text_mode(self):
        """C3修正: text モードでは長文 truncate しない"""
        long_str = "a" * 60_000
        data = {"content": long_str}
        result = OutputFormatter.format(data, "text")
        assert "truncated" not in result

    def test_exactly_max_length_not_truncated(self):
        """ちょうど 50,000 文字は truncate されない"""
        exact_str = "a" * 50_000
        data = {"content": exact_str}
        result = OutputFormatter.format(data, "json")
        parsed = json.loads(result)
        assert parsed["content"] == exact_str

    def test_normal_data_unchanged(self):
        """正常データは影響なし"""
        data = {"status": "ok", "photos": [{"id": "123", "name": "IMG_001.jpg"}]}
        result = OutputFormatter.format(data, "json")
        parsed = json.loads(result)
        assert parsed == data

    def test_text_mode_also_sanitized(self):
        """text モードでもサニタイズ適用"""
        data = {"name": "hello\x00world"}
        result = OutputFormatter.format(data, "text")
        assert "\x00" not in result
        assert "helloworld" in result
```

**Step 2: 失敗を確認**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_output_sanitize.py -v`
Expected: FAIL

**Step 3: 最小限の実装**

Modify `cli/output.py` — ファイル冒頭に `import re` を追加し、定数と `_sanitize_output()` メソッドを追加、`format()` の冒頭にサニタイズ呼び出しを追加。

ファイル冒頭の import を変更:

```python
import json
import re
from io import StringIO
from typing import Any
from rich.console import Console
from rich.table import Table
```

`OutputFormatter` クラスに定数とメソッドを追加（`format()` の前）:

```python
class OutputFormatter:
    _OUTPUT_CONTROL_CHAR_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
    _MAX_OUTPUT_STRING_LENGTH = 50_000
```

`_sanitize_output()` スタティックメソッドを `format()` の前に追加:

```python
    @staticmethod
    def _sanitize_output(data: Any, *, truncate: bool = False) -> Any:
        """出力データから制御文字を除去。truncate=True の場合のみ長文をカットする。

        C3修正 (Codex指摘): 制御文字除去は全モードで常時適用（安全措置）。
        長文truncateはjsonモードのみ適用（設計書の意図に合わせる）。
        """
        if isinstance(data, str):
            s = OutputFormatter._OUTPUT_CONTROL_CHAR_RE.sub('', data)
            if truncate and len(s) > OutputFormatter._MAX_OUTPUT_STRING_LENGTH:
                return s[:OutputFormatter._MAX_OUTPUT_STRING_LENGTH] + f"... (truncated, {len(data)} chars total)"
            return s
        if isinstance(data, dict):
            return {k: OutputFormatter._sanitize_output(v, truncate=truncate) for k, v in data.items()}
        if isinstance(data, list):
            return [OutputFormatter._sanitize_output(item, truncate=truncate) for item in data]
        return data
```

`format()` の冒頭にサニタイズ呼び出しを追加（`truncate` はjsonモードのみ `True`）:

```python
    @staticmethod
    def format(data: Any, mode: str = "text", fields: list[str] | None = None) -> str:
        data = OutputFormatter._sanitize_output(data, truncate=(mode == "json"))
        if fields is not None:
            # ... 以下既存コードそのまま
```

**Step 4: 通過を確認**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_output_sanitize.py -v`
Expected: PASS

**Step 5: リグレッションテスト**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/ -v`
Expected: 全件 PASS

**Step 6: コミット**

```bash
git add cli/output.py tests/test_output_sanitize.py
git commit -m "feat: add output sanitization layer to OutputFormatter (P2-5)"
```

---

## Task 7: lr system status に schema_hash 追加 — ハッシュ計算関数

**Files:**
- Modify: `lightroom_sdk/schema.py`
- Test: `tests/test_schema_hash.py`

**Step 1: 失敗するテストを書く**

Create `tests/test_schema_hash.py`:

```python
"""Tests for schema hash computation."""
import pytest


class TestSchemaHash:
    """get_schema_hash() のテスト"""

    def test_hash_returns_string(self):
        from lightroom_sdk.schema import get_schema_hash
        h = get_schema_hash()
        assert isinstance(h, str)
        assert len(h) == 12

    def test_hash_is_stable(self):
        """同一スキーマなら同じハッシュを返す"""
        from lightroom_sdk.schema import get_schema_hash
        h1 = get_schema_hash()
        h2 = get_schema_hash()
        assert h1 == h2

    def test_hash_is_hex(self):
        """ハッシュは16進数文字列"""
        from lightroom_sdk.schema import get_schema_hash
        h = get_schema_hash()
        int(h, 16)  # raises ValueError if not hex

    def test_hash_not_empty(self):
        from lightroom_sdk.schema import get_schema_hash
        h = get_schema_hash()
        assert len(h) > 0
```

**Step 2: 失敗を確認**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_schema_hash.py -v`
Expected: FAIL (get_schema_hash が存在しない)

**Step 3: 最小限の実装**

Modify `lightroom_sdk/schema.py` — ファイル冒頭の import に追加し、`get_schema_hash()` 関数を末尾に追加。

ファイル冒頭の import を変更:

```python
"""Command schema definitions -- Single Source of Truth for validation and introspection."""
from __future__ import annotations
import hashlib
import json as json_module
from dataclasses import dataclass, field
from enum import Enum
```

ファイル末尾（`get_all_schemas()` の後）に追加:

```python
def get_schema_hash() -> str:
    """COMMAND_SCHEMAS の安定ハッシュを計算"""
    keys = sorted(COMMAND_SCHEMAS.keys())
    content = json_module.dumps(
        [{
            "command": COMMAND_SCHEMAS[k].command,
            "cli_path": COMMAND_SCHEMAS[k].cli_path,
            "params": [(p.name, p.type.value) for p in COMMAND_SCHEMAS[k].params],
        } for k in keys],
        sort_keys=True,
    )
    return hashlib.sha256(content.encode()).hexdigest()[:12]
```

**Step 4: 通過を確認**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_schema_hash.py -v`
Expected: PASS

**Step 5: リグレッションテスト**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/ -v`
Expected: 全件 PASS

**Step 6: コミット**

```bash
git add lightroom_sdk/schema.py tests/test_schema_hash.py
git commit -m "feat: add get_schema_hash() for schema version tracking (P2-7)"
```

---

## Task 8: lr system status に schema_hash / cli_version 付与

**Files:**
- Modify: `cli/commands/system.py`, `cli/helpers.py`
- Test: `tests/test_system_status_metadata.py`

**Step 1: 失敗するテストを書く**

Create `tests/test_system_status_metadata.py`:

```python
"""Tests for schema_hash and cli_version in system status."""
import json
import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


class TestSystemStatusMetadata:
    """system status 応答に schema_hash / cli_version が含まれるテスト"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_status_includes_schema_hash(self, runner):
        """C1修正: patchパスは cli.helpers.get_bridge（execute_command経由）"""
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {
            "id": "1", "success": True,
            "result": {"status": "connected", "uptime": 100}
        }

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            result = runner.invoke(cli, ["-o", "json", "system", "status"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "schema_hash" in data
        assert isinstance(data["schema_hash"], str)
        assert len(data["schema_hash"]) == 12

    def test_status_includes_cli_version(self, runner):
        """C1修正: patchパスは cli.helpers.get_bridge（execute_command経由）"""
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {
            "id": "1", "success": True,
            "result": {"status": "connected", "uptime": 100}
        }

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            result = runner.invoke(cli, ["-o", "json", "system", "status"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "cli_version" in data
        assert isinstance(data["cli_version"], str)

    def test_status_preserves_bridge_data(self, runner):
        """C1修正: bridge応答のフィールド（plugin_version含む）がそのまま残る"""
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {
            "id": "1", "success": True,
            "result": {"status": "connected", "uptime": 100, "plugin_version": "1.0.0"}
        }

        with patch("cli.helpers.get_bridge", return_value=mock_bridge):
            result = runner.invoke(cli, ["-o", "json", "system", "status"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "connected"
        assert data["uptime"] == 100
        assert data["plugin_version"] == "1.0.0"
        # W1: plugin_version(Lua側) と cli_version(Python側) は別フィールド
        assert "cli_version" in data
```

**Step 2: 失敗を確認**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_system_status_metadata.py -v`
Expected: FAIL (status に schema_hash がない)

**Step 3: 最小限の実装**

Modify `cli/commands/system.py` — `execute_command()` を維持しつつ、応答に `schema_hash` / `cli_version` を付与する `post_process` コールバック方式を採用。

> **C1修正 (Codex指摘)**: 手動実装だと `execute_command()` の `--json/--json-stdin` パース・バリデーション・dry-runチェックが無効化され、`tests/test_cli_system.py::test_system_status` の `@patch("cli.helpers.get_bridge")` も壊れる。`execute_command()` に `post_process` 引数を追加する方式に変更。

3a. `cli/helpers.py` の `execute_command()` に `post_process` 引数を追加:

```python
def execute_command(ctx, command: str, params: dict, *, timeout: float | None = None,
                    post_process: callable | None = None):
    """共通コマンド実行ヘルパー。
    ...
    post_process: 応答 data を加工するコールバック（省略時は何もしない）
    """
    # ... 既存コードそのまま ...

    async def _run():
        # ... 既存の validate / bridge.connect / send_command ...
            data = result.get("result", result)
            if post_process is not None:
                data = post_process(data)
            click.echo(OutputFormatter.format(data, fmt, fields=fields))
        # ... 既存のエラーハンドリングそのまま ...
```

3b. `cli/commands/system.py` の `status` コマンドを変更:

```python
@system.command()
@json_input_options
@click.pass_context
def status(ctx, **kwargs):
    """Get Lightroom bridge status"""
    from lightroom_sdk.schema import get_schema_hash

    def _enrich(data):
        data["schema_hash"] = get_schema_hash()
        data["cli_version"] = _get_cli_version()
        return data

    execute_command(ctx, "system.status", {}, post_process=_enrich)


def _get_cli_version() -> str:
    """CLI バージョンを取得。インストール済みパッケージから取得、失敗時は 'dev'"""
    try:
        from importlib.metadata import version
        return version("lightroom-cli")
    except Exception:
        return "dev"
```

> **W1修正**: `system.status` 応答には bridge から返る `plugin_version` フィールド（Luaプラグイン側が返す）がそのまま残り、CLI側で `cli_version`（Pythonパッケージバージョン）と `schema_hash` を付与する。最終的な応答は `{...bridge応答..., "cli_version": "0.3.0", "schema_hash": "abc123...", "plugin_version": "1.0.0"}` の形になる。

**利点**: `execute_command()` を通るため:
- `@patch("cli.helpers.get_bridge")` がそのまま機能（既存テストのデグレなし）
- `--json/--json-stdin` パース・バリデーション・dry-runチェックも有効

**Step 4: 通過を確認**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_system_status_metadata.py -v`
Expected: PASS

**Step 5: リグレッションテスト**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/ -v`
Expected: 全件 PASS

**Step 6: コミット**

```bash
git add cli/commands/system.py tests/test_system_status_metadata.py
git commit -m "feat: add schema_hash and cli_version to system status (P2-7 cont.)"
```

---

## Task 9: SKILLS.md に Agent Quick Contract 節追加

**Files:**
- Modify: `SKILLS.md`

**Step 1: テストなし（ドキュメントのみ）**

**Step 2: SKILLS.md を変更**

`## Prerequisites` の直後、`## Getting Started for Agents` の直前に以下を追加:

```markdown
## Agent Quick Contract

1. **Always use `--fields`** to limit response size: `lr --fields id,filename catalog list`
2. **Always use `-o json`** (or pipe) for machine-readable output
3. **Use `--dry-run`** before mutating commands to preview changes
4. **Check `lr schema CMD`** for parameter types and ranges before calling
5. **Exit codes matter**: 0=ok, 2=validation, 3=connection, 4=timeout
6. **`requires_confirm` commands** need `--confirm` flag (see `lr schema CMD`)
```

**Step 3: schema detail の Response Examples セクションも更新**

`### schema detail` の出力例に `supports_dry_run`, `requires_confirm`, `risk_level` を追加:

変更前:
```json
{"command": "develop.set", "bridge_command": "develop.setValue", "description": "Set develop parameter(s)", "mutating": true, "timeout": 10.0, "params": [{"name": "parameter", "type": "string", "required": true, "description": "Develop parameter name"}, {"name": "value", "type": "float", "required": true, "description": "Parameter value"}], "response_fields": ["parameter", "value", "previousValue"]}
```

変更後:
```json
{"command": "develop.set", "bridge_command": "develop.setValue", "description": "Set develop parameter(s)", "mutating": true, "supports_dry_run": true, "requires_confirm": false, "risk_level": "write", "timeout": 10.0, "params": [{"name": "parameter", "type": "string", "required": true, "description": "Develop parameter name"}, {"name": "value", "type": "float", "required": true, "description": "Parameter value"}], "response_fields": ["parameter", "value", "previousValue"]}
```

**Step 4: リグレッションテスト**

Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/ -v`
Expected: 全件 PASS

**Step 5: コミット**

```bash
git add SKILLS.md
git commit -m "docs: add Agent Quick Contract and update schema response example (P2-4)"
```

---

## 最終確認

全タスク完了後:

```bash
cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/ -v
```

Expected: 全 744+ 件 + 新規テスト約 30 件 = 全 PASS

---

## 変更ファイルサマリー

| Task | 変更ファイル | 新規テストファイル | コミット |
|------|-------------|-------------------|---------|
| 1 | `cli/validation.py` | `tests/test_validation_range.py` | `feat: add min/max range validation` |
| 2 | `cli/validation.py` | `tests/test_validation_sanitize.py` | `feat: add string sanitization` |
| 3 | `lightroom_sdk/schema.py` | `tests/test_schema_cli_constraints.py` | `feat: add supports_dry_run/requires_confirm` |
| 4 | `cli/schema.py` | `tests/test_cli_schema.py` (追加) | `feat: expose cli_constraints in lr schema` |
| 5 | `cli/helpers.py`, `cli/decorators.py` | `tests/test_dry_run_risk_level.py` | `feat: add risk_level to --dry-run` |
| 6 | `cli/output.py` | `tests/test_output_sanitize.py` | `feat: add output sanitization layer` |
| 7 | `lightroom_sdk/schema.py` | `tests/test_schema_hash.py` | `feat: add get_schema_hash()` |
| 8 | `cli/commands/system.py`, `cli/helpers.py` | `tests/test_system_status_metadata.py` | `feat: add schema_hash to system status` |
| 9 | `SKILLS.md` | なし | `docs: add Agent Quick Contract` |
