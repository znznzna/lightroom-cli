import asyncio
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


@click.group()
def selection():
    """Selection commands (flag, unflag, reject, next, previous, color-label)"""
    pass


@selection.command("flag")
@click.pass_context
def flag_as_pick(ctx):
    """Flag selected photo(s) as Pick"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("selection.flagAsPick", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@selection.command("reject")
@click.pass_context
def flag_as_reject(ctx):
    """Flag selected photo(s) as Reject"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("selection.flagAsReject", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@selection.command("unflag")
@click.pass_context
def remove_flag(ctx):
    """Remove flag from selected photo(s)"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("selection.removeFlag", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@selection.command("next")
@click.pass_context
def next_photo(ctx):
    """Move to next photo"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("selection.nextPhoto", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@selection.command("previous")
@click.pass_context
def previous_photo(ctx):
    """Move to previous photo"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("selection.previousPhoto", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@selection.command("color-label")
@click.argument("label", type=click.Choice(["red", "yellow", "green", "blue", "purple", "none"]))
@click.pass_context
def set_color_label(ctx, label):
    """Set color label for selected photo(s)"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "selection.setColorLabel", {"label": label}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())
