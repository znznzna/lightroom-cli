"""StructuredErrorGroup -- JSON モード時に Click 標準エラーを構造化する"""
from __future__ import annotations

import json
import sys

import click


class StructuredErrorGroup(click.Group):
    """click.Group のサブクラス。

    JSON モードが有効な場合、UsageError (No such command, Missing argument 等)
    を ``{"error": {"code": "USAGE_ERROR", "message": "..."}}`` 形式で出力する。
    テキストモードでは Click のデフォルト動作を維持する。
    """

    def invoke(self, ctx: click.Context) -> None:
        try:
            return super().invoke(ctx)
        except click.UsageError as e:
            if self._is_json_mode(ctx):
                self._emit_structured_error(ctx, e)
            else:
                raise

    def resolve_command(self, ctx: click.Context, args: list[str]):
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError as e:
            if self._is_json_mode(ctx):
                self._emit_structured_error(ctx, e)
            else:
                raise

    # ------------------------------------------------------------------

    @staticmethod
    def _is_json_mode(ctx: click.Context) -> bool:
        """コンテキストから出力モードを判定する。"""
        output = None

        # 1. ctx.params (トップレベルグループのパラメータ)
        if ctx.params:
            output = ctx.params.get("output")

        # 2. 親コンテキストを辿る (サブコマンドから呼ばれた場合)
        if output is None:
            parent = ctx.parent
            while parent is not None:
                if parent.params and parent.params.get("output"):
                    output = parent.params["output"]
                    break
                parent = parent.parent

        # 3. ctx.obj
        if output is None and ctx.obj:
            output = ctx.obj.get("output")

        # 4. 環境変数
        if output is None:
            import os

            output = os.environ.get("LR_OUTPUT")

        # 5. TTY 判定フォールバック
        if output is None:
            output = "json" if not sys.stdout.isatty() else "text"

        return output == "json"

    @staticmethod
    def _emit_structured_error(ctx: click.Context, error: click.UsageError) -> None:
        """構造化エラーを JSON で出力し、exit code 2 で終了する。"""
        error_obj = {
            "error": {
                "code": "USAGE_ERROR",
                "message": error.format_message(),
            }
        }
        click.echo(json.dumps(error_obj))
        ctx.exit(2)
