import asyncio
import click
from cli.output import OutputFormatter


def get_bridge():
    """ResilientSocketBridgeインスタンスを取得（遅延import）"""
    from lightroom_sdk.resilient_bridge import ResilientSocketBridge
    return ResilientSocketBridge()


def run_async(coro):
    """CLIからasync関数を実行するヘルパー（コマンドごとに1回だけ呼ぶ）"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _parse_pairs(pairs: tuple) -> dict:
    """可変長引数 (param, value, param, value, ...) を辞書に変換"""
    if len(pairs) % 2 != 0:
        raise click.BadParameter("Parameters must be in 'param value' pairs")
    result = {}
    for i in range(0, len(pairs), 2):
        result[pairs[i]] = float(pairs[i + 1])
    return result


@click.group()
def develop():
    """Develop commands (get-settings, get, set, apply, auto-tone, auto-wb, tool, reset)"""
    pass


@develop.command("get-settings")
@click.pass_context
def get_settings(ctx):
    """Get all current develop settings"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.getSettings", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@develop.command("set")
@click.argument("pairs", nargs=-1, required=True)
@click.pass_context
def set_values(ctx, pairs):
    """Set develop parameter(s): lr develop set <param> <value> [<param2> <value2> ...]"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            parsed = _parse_pairs(pairs)
            if len(parsed) == 1:
                param, value = next(iter(parsed.items()))
                result = await bridge.send_command(
                    "develop.setValue", {"parameter": param, "value": value}, timeout=timeout
                )
            else:
                result = await bridge.send_command(
                    "develop.batchApplySettings", {"settings": parsed}, timeout=timeout
                )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@develop.command("auto-tone")
@click.pass_context
def auto_tone(ctx):
    """Apply auto tone adjustments"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.setAutoTone", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@develop.command("get")
@click.argument("parameter")
@click.pass_context
def get_value(ctx, parameter):
    """Get a single develop parameter value"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "develop.getValue", {"param": parameter}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@develop.command("apply")
@click.option("--settings", required=True, help="JSON string of settings to apply")
@click.pass_context
def apply_settings(ctx, settings):
    """Apply develop settings from JSON"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    import json
    try:
        parsed = json.loads(settings)
    except json.JSONDecodeError as e:
        click.echo(OutputFormatter.format_error(f"Invalid JSON: {e}"))
        ctx.exit(1)
        return

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "develop.applySettings", {"settings": parsed}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@develop.command("auto-wb")
@click.pass_context
def auto_wb(ctx):
    """Apply auto white balance"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "develop.setAutoWhiteBalance", {}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@develop.command("tool")
@click.argument("tool_name")
@click.pass_context
def select_tool(ctx, tool_name):
    """Select a develop tool (loupe/crop/dust/redeye/gradient/circularGradient/localized/upright)"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "develop.selectTool", {"tool": tool_name}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@develop.command("reset")
@click.pass_context
def reset(ctx):
    """Reset develop settings to defaults"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.resetAllDevelopAdjustments", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())
