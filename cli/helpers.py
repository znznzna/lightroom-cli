import asyncio
import functools
import click
from cli.output import OutputFormatter


def get_bridge():
    """ResilientSocketBridgeインスタンスを取得（遅延import）"""
    from lightroom_sdk.resilient_bridge import ResilientSocketBridge
    return ResilientSocketBridge()


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
    cmd_timeout = timeout if timeout is not None else (ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0)

    async def _run():
        bridge = get_bridge()
        try:
            await bridge.connect()
            result = await bridge.send_command(command, params, timeout=cmd_timeout)
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
