import asyncio

import click

from cli.output import OutputFormatter


def _is_connection_error(e: Exception) -> bool:
    """ビルトイン ConnectionError と SDK ConnectionError の両方を判定"""
    from lightroom_sdk.exceptions import ConnectionError as SDKConnectionError

    return isinstance(e, (ConnectionError, SDKConnectionError))


def _is_timeout_error(e: Exception) -> bool:
    """ビルトイン TimeoutError と SDK TimeoutError の両方を判定"""
    from lightroom_sdk.exceptions import TimeoutError as SDKTimeoutError

    return isinstance(e, (TimeoutError, SDKTimeoutError))


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


def execute_command(ctx, command: str, params: dict, *, timeout: float | None = None, post_process=None):
    """共通コマンド実行ヘルパー。

    - エラーハンドリング（構造化エラー + 終了コード）
    - fields フィルタリング
    - bridge 接続・切断の管理
    """
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
    fields = ctx.obj.get("fields") if ctx.obj else None
    global_timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    if timeout is not None:
        cmd_timeout = max(timeout, global_timeout)
    else:
        cmd_timeout = global_timeout

    # --json / --json-stdin 入力チェック
    json_str = getattr(ctx, "params", {}).get("json_str")
    json_stdin = getattr(ctx, "params", {}).get("json_stdin", False)
    if json_str is not None or json_stdin:
        import sys

        from cli.decorators import parse_json_input

        if json_str is not None and not json_str.strip():
            click.echo(
                OutputFormatter.format_error("Empty --json value", fmt, code="VALIDATION_ERROR"),
                err=True,
            )
            ctx.exit(2)
            return
        stdin = sys.stdin if json_stdin else None
        try:
            json_params = parse_json_input(json_str, stdin)
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

    async def _run():
        # バリデーション（スキーマ未定義コマンドはスキップ）
        from cli.validation import ValidationError, validate_params

        try:
            validated = validate_params(command, params)
        except ValidationError as e:
            click.echo(
                OutputFormatter.format_error(
                    str(e),
                    fmt,
                    code="VALIDATION_ERROR",
                    suggestions=e.suggestions,
                ),
                err=True,
            )
            ctx.exit(2)
            return

        bridge = get_bridge()
        try:
            await bridge.connect()
            result = await bridge.send_command(command, validated, timeout=cmd_timeout)
            data = result.get("result", result)
            if post_process is not None:
                data = post_process(data)
            click.echo(OutputFormatter.format(data, fmt, fields=fields))
        except Exception as e:
            if _is_connection_error(e):
                click.echo(
                    OutputFormatter.format_error(str(e), fmt, code="CONNECTION_ERROR"),
                    err=True,
                )
                ctx.exit(3)
                return
            if _is_timeout_error(e):
                click.echo(
                    OutputFormatter.format_error(str(e), fmt, code="TIMEOUT_ERROR"),
                    err=True,
                )
                ctx.exit(4)
                return
            click.echo(
                OutputFormatter.format_error(str(e), fmt),
                err=True,
            )
            ctx.exit(1)
        finally:
            await bridge.disconnect()

    run_async(_run())


def handle_error(ctx, error: Exception, fmt: str = "text"):
    """共通エラーハンドリング（execute_command を使わないコマンド用）"""
    if _is_connection_error(error):
        click.echo(
            OutputFormatter.format_error(str(error), fmt, code="CONNECTION_ERROR"),
            err=True,
        )
        ctx.exit(3)
    elif _is_timeout_error(error):
        click.echo(
            OutputFormatter.format_error(str(error), fmt, code="TIMEOUT_ERROR"),
            err=True,
        )
        ctx.exit(4)
    else:
        click.echo(
            OutputFormatter.format_error(str(error), fmt),
            err=True,
        )
        ctx.exit(1)
