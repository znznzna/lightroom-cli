"""CLI decorators and guard functions."""
from __future__ import annotations
import json as json_module
from typing import IO
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
    """dry-run ガード。--dry-run が指定されていればプレビューを出力して True を返す。"""
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
    """--json と --json-stdin の入力を解析する。

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
