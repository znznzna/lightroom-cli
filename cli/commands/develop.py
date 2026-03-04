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


@develop.command("preset")
@click.argument("preset_name")
@click.pass_context
def preset(ctx, preset_name):
    """Apply a develop preset by name"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.applyDevelopPreset", {"presetName": preset_name}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@develop.command("snapshot")
@click.argument("name")
@click.pass_context
def snapshot(ctx, name):
    """Create a develop snapshot"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.createDevelopSnapshot", {"name": name}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@develop.command("copy-settings")
@click.pass_context
def copy_settings(ctx):
    """Copy develop settings from selected photo"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.copySettings", {}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@develop.command("paste-settings")
@click.pass_context
def paste_settings(ctx):
    """Paste develop settings to selected photo"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.pasteSettings", {}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@develop.command("range")
@click.argument("param")
@click.pass_context
def get_range(ctx, param):
    """Get min/max range for a develop parameter"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.getRange", {"param": param}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@develop.command("reset-param")
@click.argument("param")
@click.pass_context
def reset_param(ctx, param):
    """Reset a develop parameter to its default value"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.resetToDefault", {"param": param}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@develop.command("process-version")
@click.pass_context
def process_version(ctx):
    """Get the current process version"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.getProcessVersion", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@develop.command("set-process-version")
@click.argument("version")
@click.pass_context
def set_process_version(ctx, version):
    """Set the process version"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.setProcessVersion", {"version": version}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


CHANNEL_TO_PARAM = {
    "RGB": "ToneCurvePV2012",
    "Red": "ToneCurvePV2012Red",
    "Green": "ToneCurvePV2012Green",
    "Blue": "ToneCurvePV2012Blue",
}


@develop.group()
def curve():
    """Tone curve commands"""
    pass


@curve.command("get")
@click.option("--channel", default="RGB", help="Channel (RGB/Red/Green/Blue)")
@click.pass_context
def curve_get(ctx, channel):
    """Get tone curve points"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "develop.getCurvePoints", {"param": CHANNEL_TO_PARAM.get(channel, channel)}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@curve.command("set")
@click.option("--points", required=True, help="JSON array of [x,y] points")
@click.option("--channel", default="RGB", help="Channel (RGB/Red/Green/Blue)")
@click.pass_context
def curve_set(ctx, points, channel):
    """Set tone curve points"""
    import json
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    try:
        parsed = json.loads(points)
    except json.JSONDecodeError as e:
        click.echo(OutputFormatter.format_error(f"Invalid JSON: {e}"))
        ctx.exit(1)
        return

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "develop.setCurvePoints", {"param": CHANNEL_TO_PARAM.get(channel, channel), "points": [{"x": p[0], "y": p[1]} if isinstance(p, list) else p for p in parsed]}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@curve.command("linear")
@click.option("--channel", default="RGB", help="Channel")
@click.pass_context
def curve_linear(ctx, channel):
    """Reset curve to linear"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "develop.setCurveLinear", {"param": CHANNEL_TO_PARAM.get(channel, channel)}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@curve.command("s-curve")
@click.option("--channel", default="RGB", help="Channel")
@click.pass_context
def curve_s_curve(ctx, channel):
    """Apply S-curve preset"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "develop.setCurveSCurve", {"param": CHANNEL_TO_PARAM.get(channel, channel)}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@curve.command("add-point")
@click.argument("x", type=float)
@click.argument("y", type=float)
@click.option("--channel", default="RGB", help="Channel")
@click.pass_context
def curve_add_point(ctx, x, y, channel):
    """Add a point to the tone curve"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "develop.addCurvePoint", {"param": CHANNEL_TO_PARAM.get(channel, channel), "x": x, "y": y}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@curve.command("remove-point")
@click.argument("index", type=int)
@click.option("--channel", default="RGB", help="Channel")
@click.pass_context
def curve_remove_point(ctx, index, channel):
    """Remove a point from the tone curve"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "develop.removeCurvePoint", {"param": CHANNEL_TO_PARAM.get(channel, channel), "index": index}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


# --- Masking commands ---


@develop.group()
def mask():
    """Masking commands"""
    pass


@mask.command("list")
@click.pass_context
def mask_list(ctx):
    """List all masks"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.getAllMasks", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@mask.command("selected")
@click.pass_context
def mask_selected(ctx):
    """Get selected mask"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.getSelectedMask", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@mask.command("create")
@click.pass_context
def mask_create(ctx):
    """Create a new mask"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.createNewMask", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@mask.command("select")
@click.argument("mask_id")
@click.pass_context
def mask_select(ctx, mask_id):
    """Select a mask by ID"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.selectMask", {"maskId": mask_id}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@mask.command("delete")
@click.argument("mask_id")
@click.pass_context
def mask_delete(ctx, mask_id):
    """Delete a mask by ID"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.deleteMask", {"maskId": mask_id}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@mask.command("tool-info")
@click.pass_context
def mask_tool_info(ctx):
    """Get selected mask tool info"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.getSelectedMaskTool", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@mask.command("select-tool")
@click.argument("tool_id")
@click.pass_context
def mask_select_tool(ctx, tool_id):
    """Select a mask tool by ID"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.selectMaskTool", {"toolId": tool_id}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@mask.command("delete-tool")
@click.argument("tool_id")
@click.pass_context
def mask_delete_tool(ctx, tool_id):
    """Delete a mask tool by ID"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.deleteMaskTool", {"toolId": tool_id}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@mask.command("add")
@click.argument("mask_type")
@click.option("--subtype", default=None, help="Mask subtype")
@click.pass_context
def mask_add(ctx, mask_type, subtype):
    """Add tool to current mask (brush/gradient/radial/range/ai)"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    params = {"maskType": mask_type}
    if subtype:
        params["maskSubtype"] = subtype

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.addToCurrentMask", params, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@mask.command("intersect")
@click.argument("mask_type")
@click.option("--subtype", default=None, help="Mask subtype")
@click.pass_context
def mask_intersect(ctx, mask_type, subtype):
    """Intersect tool with current mask"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    params = {"maskType": mask_type}
    if subtype:
        params["maskSubtype"] = subtype

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.intersectWithCurrentMask", params, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@mask.command("subtract")
@click.argument("mask_type")
@click.option("--subtype", default=None, help="Mask subtype")
@click.pass_context
def mask_subtract(ctx, mask_type, subtype):
    """Subtract tool from current mask"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    params = {"maskType": mask_type}
    if subtype:
        params["maskSubtype"] = subtype

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.subtractFromCurrentMask", params, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@mask.command("invert")
@click.argument("mask_id")
@click.pass_context
def mask_invert(ctx, mask_id):
    """Invert a mask by ID"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.invertMask", {"maskId": mask_id}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@mask.command("go-to")
@click.pass_context
def mask_go_to(ctx):
    """Go to masking view"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.goToMasking", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@mask.command("toggle-overlay")
@click.pass_context
def mask_toggle_overlay(ctx):
    """Toggle mask overlay"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.toggleOverlay", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@mask.command("activate")
@click.pass_context
def mask_activate(ctx):
    """Activate masking mode"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.activateMaskingMode", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


# --- Local adjustment commands ---


@develop.group("local")
def local_adj():
    """Local adjustment commands"""
    pass


@local_adj.command("get")
@click.argument("parameter")
@click.pass_context
def local_get(ctx, parameter):
    """Get a local adjustment parameter value"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "develop.getLocalValue", {"parameter": parameter}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@local_adj.command("set")
@click.argument("parameter")
@click.argument("value", type=float)
@click.pass_context
def local_set(ctx, parameter, value):
    """Set a local adjustment parameter value"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "develop.setLocalValue", {"parameter": parameter, "value": value}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@local_adj.command("apply")
@click.option("--settings", required=True, help="JSON string of local adjustment settings")
@click.pass_context
def local_apply(ctx, settings):
    """Apply multiple local adjustment settings from JSON"""
    import json
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

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
                "develop.applyLocalSettings", {"settings": parsed}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@local_adj.command("params")
@click.pass_context
def local_params(ctx):
    """List available local adjustment parameters"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "develop.getAvailableLocalParameters", {}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


# --- Filter creation commands ---


@develop.group("filter")
def filter_cmds():
    """Filter creation commands"""
    pass


@filter_cmds.command("graduated")
@click.pass_context
def filter_graduated(ctx):
    """Create a graduated filter"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.createGraduatedFilter", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@filter_cmds.command("radial")
@click.pass_context
def filter_radial(ctx):
    """Create a radial filter"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.createRadialFilter", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@filter_cmds.command("brush")
@click.pass_context
def filter_brush(ctx):
    """Create an adjustment brush"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.createAdjustmentBrush", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@filter_cmds.command("ai-select")
@click.option("--type", "selection_type", default=None,
              type=click.Choice(["subject", "sky", "background", "objects", "people", "landscape"]),
              help="AI selection type (subject/sky/background/objects/people/landscape)")
@click.pass_context
def filter_ai_select(ctx, selection_type):
    """Create an AI selection mask"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    params = {}
    if selection_type is not None:
        params["selectionType"] = selection_type

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.createAISelectionMask", params, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@filter_cmds.command("range")
@click.option("--type", "range_type", default=None,
              type=click.Choice(["luminance", "color", "depth"]),
              help="Range mask type (luminance/color/depth)")
@click.pass_context
def filter_range(ctx, range_type):
    """Create a range mask"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    params = {}
    if range_type is not None:
        params["rangeType"] = range_type

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.createRangeMask", params, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())
