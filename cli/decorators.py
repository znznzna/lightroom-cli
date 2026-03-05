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
