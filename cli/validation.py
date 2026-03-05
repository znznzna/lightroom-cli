"""Input validation based on command schemas."""
from __future__ import annotations
import re
from lightroom_sdk.schema import get_schema, ParamType, ParamSchema

_MAX_STRING_LENGTH = 10_000
_CONTROL_CHAR_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


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
    """コマンドのパラメータをスキーマに基づいてバリデーション。

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
            if not suggestions:
                suggestions = [f"Valid parameters: {', '.join(sorted(valid_names))}"]
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


def _check_range(name: str, value: int | float, schema: ParamSchema) -> None:
    """min/max 範囲チェック。schema に min/max が未設定ならスキップ。"""
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


def _sanitize_string(name: str, value: str) -> str:
    """文字列のサニタイズ: NUL・制御文字・過長入力をreject。\t, \n, \r は許可。"""
    if '\x00' in value:
        raise ValidationError(
            f"Parameter '{name}' contains null character",
            param=name,
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


def _sanitize_json_strings(param_name: str, data: object) -> object:
    """JSON_OBJECT/JSON_ARRAY 内の文字列を再帰的にサニタイズ。"""
    if isinstance(data, str):
        return _sanitize_string(param_name, data)
    if isinstance(data, dict):
        return {k: _sanitize_json_strings(param_name, v) for k, v in data.items()}
    if isinstance(data, list):
        return [_sanitize_json_strings(param_name, item) for item in data]
    return data


def _coerce_type(name: str, value: object, schema: ParamSchema) -> object:
    """型変換を試みる。失敗時は ValidationError。"""
    try:
        match schema.type:
            case ParamType.STRING:
                s = str(value)
                return _sanitize_string(name, s)
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
                return _sanitize_json_strings(name, value)
            case ParamType.JSON_ARRAY:
                if not isinstance(value, list):
                    raise ValidationError(
                        f"Invalid type for '{name}': expected JSON array (list), "
                        f"got {type(value).__name__}",
                        param=name,
                    )
                return _sanitize_json_strings(name, value)
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


def _find_similar(name: str, valid_names: set[str], max_results: int = 3) -> list[str]:
    """部分文字列マッチ + 編集距離で類似パラメータを検索"""
    from difflib import get_close_matches
    # difflib for fuzzy matching
    matches = get_close_matches(name, sorted(valid_names), n=max_results, cutoff=0.6)
    if matches:
        return list(matches)
    # Fallback to substring matching
    name_lower = name.lower()
    suggestions = []
    for valid in sorted(valid_names):
        if name_lower in valid.lower() or valid.lower() in name_lower:
            suggestions.append(valid)
    return suggestions[:max_results]
