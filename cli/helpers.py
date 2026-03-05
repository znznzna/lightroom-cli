import asyncio
import functools
import click
from cli.output import OutputFormatter


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


def execute_command(ctx, command: str, params: dict, *, timeout: float | None = None):
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

    # --json 入力チェック
    json_str = getattr(ctx, "params", {}).get("json_str")
    if json_str is not None:
        from cli.decorators import parse_json_input
        if not json_str.strip():
            click.echo(
                OutputFormatter.format_error(
                    "Empty --json value", fmt, code="VALIDATION_ERROR"
                ),
                err=True,
            )
            ctx.exit(2)
            return
        try:
            json_params = parse_json_input(json_str, None)
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
            "params": {k: v for k, v in params.items() if v is not None},
        }
        click.echo(OutputFormatter.format(preview, fmt))
        return

    async def _run():
        # バリデーション（スキーマ未定義コマンドはスキップ）
        from cli.validation import validate_params, ValidationError
        try:
            validated = validate_params(command, params)
        except ValidationError as e:
            click.echo(
                OutputFormatter.format_error(
                    str(e), fmt,
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
            click.echo(OutputFormatter.format(data, fmt, fields=fields))
        except ConnectionError as e:
            click.echo(
                OutputFormatter.format_error(str(e), fmt, code="CONNECTION_ERROR"),
                err=True,
            )
            ctx.exit(3)
        except TimeoutError as e:
            click.echo(
                OutputFormatter.format_error(str(e), fmt, code="TIMEOUT_ERROR"),
                err=True,
            )
            ctx.exit(4)
        except Exception as e:
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
    if isinstance(error, ConnectionError):
        click.echo(
            OutputFormatter.format_error(str(error), fmt, code="CONNECTION_ERROR"),
            err=True,
        )
        ctx.exit(3)
    elif isinstance(error, TimeoutError):
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


def bridge_command(bridge_cmd: str, timeout: float = 30.0):
    """CLIコマンドのボイラープレートを削減するデコレータ。

    デコレートされた関数はパラメータのdictを返す。
    デコレータがbridge通信・出力フォーマット・エラーハンドリングを担当する。

    Usage:
        @some_group.command("cmd-name")
        @click.argument("photo_id")
        @bridge_command("catalog.someCommand")
        def cmd_name(photo_id):
            return {"photoId": photo_id}
    """
    def decorator(func):
        @functools.wraps(func)
        @click.pass_context
        def wrapper(ctx, **kwargs):
            global_timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
            _timeout = timeout if timeout != 30.0 else global_timeout
            fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

            params = func(**kwargs)
            if params is None:
                params = {}

            loop = asyncio.new_event_loop()
            try:
                async def _run():
                    bridge = get_bridge()
                    try:
                        await bridge.connect()
                        result = await bridge.send_command(
                            bridge_cmd, params, timeout=_timeout
                        )
                        click.echo(OutputFormatter.format(
                            result.get("result", result), fmt
                        ))
                    except Exception as e:
                        click.echo(OutputFormatter.format_error(str(e), fmt))
                    finally:
                        await bridge.disconnect()

                loop.run_until_complete(_run())
            finally:
                loop.close()
        return wrapper
    return decorator
