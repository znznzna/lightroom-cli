"""CLI middleware: TTY detection, environment variable resolution."""
import os
import sys


def resolve_output_format(explicit_output: str | None) -> str:
    """Resolve output format with priority: explicit > LR_OUTPUT env > TTY detection."""
    if explicit_output is not None:
        return explicit_output
    env_output = os.environ.get("LR_OUTPUT")
    if env_output and env_output in ("json", "text", "table"):
        return env_output
    if not sys.stdout.isatty():
        return "json"
    return "text"


def resolve_timeout(explicit_timeout: float | None) -> float:
    """Resolve timeout with priority: explicit > LR_TIMEOUT env > default 30s."""
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
    """Resolve field filter with priority: explicit > LR_FIELDS env > None."""
    fields_str = explicit_fields or os.environ.get("LR_FIELDS")
    if fields_str:
        return [f.strip() for f in fields_str.split(",")]
    return None
