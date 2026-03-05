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
