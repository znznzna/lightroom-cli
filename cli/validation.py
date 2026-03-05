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
