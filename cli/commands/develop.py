import json

import click

from cli.decorators import json_input_options
from cli.helpers import execute_command
from cli.output import OutputFormatter


def _parse_pairs(pairs: tuple) -> dict:
    """可変長引数 (param, value, param, value, ...) を辞書に変換"""
    if len(pairs) % 2 != 0:
        raise click.BadParameter("Parameters must be in 'param value' pairs")
    result = {}
    for i in range(0, len(pairs), 2):
        try:
            result[pairs[i]] = float(pairs[i + 1])
        except ValueError:
            raise click.BadParameter(
                f"Invalid numeric value '{pairs[i + 1]}' for parameter '{pairs[i]}'. "
                f"Expected a number (e.g., 0.5, -1.0, 100)"
            )
    return result


@click.group()
def develop():
    """Develop commands (get-settings, get, set, apply, auto-tone, auto-wb, tool, reset)"""
    pass


from cli.commands.ai_mask import ai

develop.add_command(ai)


@develop.command("get-settings")
@json_input_options
@click.pass_context
def get_settings(ctx, **kwargs):
    """Get all current develop settings"""
    execute_command(ctx, "develop.getSettings", {})


@develop.command("set")
@click.argument("pairs", nargs=-1, required=True)
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def set_values(ctx, pairs, dry_run, **kwargs):
    """Set develop parameter(s): lr develop set <param> <value> [<param2> <value2> ...]"""
    try:
        parsed = _parse_pairs(pairs)
    except click.BadParameter as e:
        click.echo(
            OutputFormatter.format_error(
                str(e),
                ctx.obj.get("output", "text") if ctx.obj else "text",
                code="VALIDATION_ERROR",
            ),
            err=True,
        )
        ctx.exit(2)
        return
    if len(parsed) == 1:
        param, value = next(iter(parsed.items()))
        execute_command(ctx, "develop.setValue", {"parameter": param, "value": value})
    else:
        execute_command(ctx, "develop.batchApplySettings", {"settings": parsed})


@develop.command("auto-tone")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def auto_tone(ctx, dry_run, **kwargs):
    """Apply auto tone adjustments"""
    execute_command(ctx, "develop.setAutoTone", {})


@develop.command("get")
@click.argument("parameter")
@json_input_options
@click.pass_context
def get_value(ctx, parameter, **kwargs):
    """Get a single develop parameter value"""
    execute_command(ctx, "develop.getValue", {"param": parameter})


@develop.command("apply")
@click.option("--settings", required=True, help="JSON string of settings to apply")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def apply_settings(ctx, settings, dry_run, **kwargs):
    """Apply develop settings from JSON"""
    try:
        parsed = json.loads(settings)
    except json.JSONDecodeError as e:
        click.echo(
            OutputFormatter.format_error(
                f"Invalid JSON: {e}",
                ctx.obj.get("output", "text") if ctx.obj else "text",
                code="VALIDATION_ERROR",
            ),
            err=True,
        )
        ctx.exit(1)
        return
    execute_command(ctx, "develop.applySettings", {"settings": parsed})


@develop.command("auto-wb")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def auto_wb(ctx, dry_run, **kwargs):
    """Apply auto white balance"""
    execute_command(ctx, "develop.setAutoWhiteBalance", {})


@develop.command("tool")
@click.argument("tool_name")
@json_input_options
@click.pass_context
def select_tool(ctx, tool_name, **kwargs):
    """Select a develop tool (loupe/crop/dust/redeye/gradient/circularGradient/localized/upright)"""
    execute_command(ctx, "develop.selectTool", {"tool": tool_name})


@develop.command("reset")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def reset(ctx, dry_run, **kwargs):
    """Reset develop settings to defaults"""
    execute_command(ctx, "develop.resetAllDevelopAdjustments", {})


@develop.command("preset")
@click.argument("preset_name")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def preset(ctx, preset_name, dry_run, **kwargs):
    """Apply a develop preset by name"""
    execute_command(ctx, "catalog.applyDevelopPreset", {"presetName": preset_name})


@develop.command("snapshot")
@click.argument("name")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def snapshot(ctx, name, dry_run, **kwargs):
    """Create a develop snapshot"""
    execute_command(ctx, "catalog.createDevelopSnapshot", {"name": name})


@develop.command("copy-settings")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def copy_settings(ctx, dry_run, **kwargs):
    """Copy develop settings from selected photo"""
    execute_command(ctx, "catalog.copySettings", {})


@develop.command("paste-settings")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def paste_settings(ctx, dry_run, **kwargs):
    """Paste develop settings to selected photo"""
    execute_command(ctx, "catalog.pasteSettings", {})


@develop.command("range")
@click.argument("param")
@json_input_options
@click.pass_context
def get_range(ctx, param, **kwargs):
    """Get min/max range for a develop parameter"""
    execute_command(ctx, "develop.getRange", {"param": param})


@develop.command("reset-param")
@click.argument("param")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def reset_param(ctx, param, dry_run, **kwargs):
    """Reset a develop parameter to its default value"""
    execute_command(ctx, "develop.resetToDefault", {"param": param})


@develop.command("process-version")
@json_input_options
@click.pass_context
def process_version(ctx, **kwargs):
    """Get the current process version"""
    execute_command(ctx, "develop.getProcessVersion", {})


@develop.command("set-process-version")
@click.argument("version")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def set_process_version(ctx, version, dry_run, **kwargs):
    """Set the process version"""
    execute_command(ctx, "develop.setProcessVersion", {"version": version})


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
@json_input_options
@click.pass_context
def curve_get(ctx, channel, **kwargs):
    """Get tone curve points"""
    execute_command(ctx, "develop.getCurvePoints", {"param": CHANNEL_TO_PARAM.get(channel, channel)})


@curve.command("set")
@click.option("--points", required=True, help="JSON array of [x,y] points")
@click.option("--channel", default="RGB", help="Channel (RGB/Red/Green/Blue)")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def curve_set(ctx, points, channel, dry_run, **kwargs):
    """Set tone curve points"""
    try:
        parsed = json.loads(points)
    except json.JSONDecodeError as e:
        click.echo(
            OutputFormatter.format_error(
                f"Invalid JSON: {e}",
                ctx.obj.get("output", "text") if ctx.obj else "text",
                code="VALIDATION_ERROR",
            ),
            err=True,
        )
        ctx.exit(1)
        return
    curve_points = [{"x": p[0], "y": p[1]} if isinstance(p, list) else p for p in parsed]
    execute_command(
        ctx,
        "develop.setCurvePoints",
        {"param": CHANNEL_TO_PARAM.get(channel, channel), "points": curve_points},
    )


@curve.command("linear")
@click.option("--channel", default="RGB", help="Channel")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def curve_linear(ctx, channel, dry_run, **kwargs):
    """Reset curve to linear"""
    execute_command(ctx, "develop.setCurveLinear", {"param": CHANNEL_TO_PARAM.get(channel, channel)})


@curve.command("s-curve")
@click.option("--channel", default="RGB", help="Channel")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def curve_s_curve(ctx, channel, dry_run, **kwargs):
    """Apply S-curve preset"""
    execute_command(ctx, "develop.setCurveSCurve", {"param": CHANNEL_TO_PARAM.get(channel, channel)})


@curve.command("add-point")
@click.argument("x", type=float)
@click.argument("y", type=float)
@click.option("--channel", default="RGB", help="Channel")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def curve_add_point(ctx, x, y, channel, dry_run, **kwargs):
    """Add a point to the tone curve"""
    execute_command(
        ctx,
        "develop.addCurvePoint",
        {"param": CHANNEL_TO_PARAM.get(channel, channel), "x": x, "y": y},
    )


@curve.command("remove-point")
@click.argument("index", type=int)
@click.option("--channel", default="RGB", help="Channel")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def curve_remove_point(ctx, index, channel, dry_run, **kwargs):
    """Remove a point from the tone curve"""
    execute_command(
        ctx,
        "develop.removeCurvePoint",
        {"param": CHANNEL_TO_PARAM.get(channel, channel), "index": index},
    )


# --- Masking commands ---


@develop.group()
def mask():
    """Masking commands"""
    pass


@mask.command("list")
@json_input_options
@click.pass_context
def mask_list(ctx, **kwargs):
    """List all masks (DEPRECATED: use 'lr develop ai list')"""
    click.echo(
        "Warning: 'lr develop mask list' is deprecated. Use 'lr develop ai list' instead.",
        err=True,
    )
    execute_command(ctx, "develop.getAllMasks", {})


@mask.command("selected")
@json_input_options
@click.pass_context
def mask_selected(ctx, **kwargs):
    """Get selected mask"""
    execute_command(ctx, "develop.getSelectedMask", {})


@mask.command("go-to")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def mask_go_to(ctx, dry_run, **kwargs):
    """Go to masking view"""
    execute_command(ctx, "develop.goToMasking", {})


@mask.command("toggle-overlay")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def mask_toggle_overlay(ctx, dry_run, **kwargs):
    """Toggle mask overlay"""
    execute_command(ctx, "develop.toggleOverlay", {})


# --- Local adjustment commands ---


@develop.group("local")
def local_adj():
    """Local adjustment commands"""
    pass


@local_adj.command("get")
@click.argument("parameter")
@json_input_options
@click.pass_context
def local_get(ctx, parameter, **kwargs):
    """Get a local adjustment parameter value"""
    execute_command(ctx, "develop.getLocalValue", {"parameter": parameter})


@local_adj.command("set")
@click.argument("parameter")
@click.argument("value", type=float)
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def local_set(ctx, parameter, value, dry_run, **kwargs):
    """Set a local adjustment parameter value"""
    execute_command(ctx, "develop.setLocalValue", {"parameter": parameter, "value": value})


@local_adj.command("apply")
@click.option("--settings", required=True, help="JSON string of local adjustment settings")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def local_apply(ctx, settings, dry_run, **kwargs):
    """Apply multiple local adjustment settings from JSON"""
    try:
        parsed = json.loads(settings)
    except json.JSONDecodeError as e:
        click.echo(
            OutputFormatter.format_error(
                f"Invalid JSON: {e}",
                ctx.obj.get("output", "text") if ctx.obj else "text",
                code="VALIDATION_ERROR",
            ),
            err=True,
        )
        ctx.exit(1)
        return
    execute_command(ctx, "develop.applyLocalSettings", {"settings": parsed})


@local_adj.command("params")
@json_input_options
@click.pass_context
def local_params(ctx, **kwargs):
    """List available local adjustment parameters"""
    execute_command(ctx, "develop.getAvailableLocalParameters", {})


@local_adj.command("create-mask")
@click.option("--tool", "mask_type", default=None, help="Mask type (brush/gradient/radial)")
@click.option("--settings", default=None, help="JSON local adjustment settings")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def local_create_mask(ctx, mask_type, settings, dry_run, **kwargs):
    """Create mask with local adjustments"""
    params = {}
    if mask_type:
        params["maskType"] = mask_type
    if settings:
        try:
            params["localSettings"] = json.loads(settings)
        except json.JSONDecodeError as e:
            click.echo(
                OutputFormatter.format_error(
                    f"Invalid JSON: {e}",
                    ctx.obj.get("output", "text") if ctx.obj else "text",
                    code="VALIDATION_ERROR",
                ),
                err=True,
            )
            ctx.exit(1)
            return
    execute_command(ctx, "develop.createMaskWithLocalAdjustments", params)


# --- Filter creation commands ---


@develop.group("filter")
def filter_cmds():
    """Filter creation commands"""
    pass


@filter_cmds.command("graduated")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def filter_graduated(ctx, dry_run, **kwargs):
    """Create a graduated filter"""
    execute_command(ctx, "develop.createGraduatedFilter", {})


@filter_cmds.command("radial")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def filter_radial(ctx, dry_run, **kwargs):
    """Create a radial filter"""
    execute_command(ctx, "develop.createRadialFilter", {})


@filter_cmds.command("brush")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def filter_brush(ctx, dry_run, **kwargs):
    """Create an adjustment brush"""
    execute_command(ctx, "develop.createAdjustmentBrush", {})


@filter_cmds.command("range")
@click.option(
    "--type",
    "range_type",
    default=None,
    type=click.Choice(["luminance", "color", "depth"]),
    help="Range mask type (luminance/color/depth)",
)
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def filter_range(ctx, range_type, dry_run, **kwargs):
    """Create a range mask"""
    params = {}
    if range_type is not None:
        params["rangeType"] = range_type
    execute_command(ctx, "develop.createRangeMask", params)


# --- Debug/introspection commands ---


@develop.group("debug")
def debug_cmds():
    """Debug/introspection commands"""
    pass


@debug_cmds.command("dump")
@json_input_options
@click.pass_context
def debug_dump(ctx, **kwargs):
    """Dump LrDevelopController info"""
    execute_command(ctx, "develop.dumpLrDevelopController", {})


@debug_cmds.command("gradient-params")
@json_input_options
@click.pass_context
def debug_gradient_params(ctx, **kwargs):
    """Discover gradient parameters"""
    execute_command(ctx, "develop.discoverGradientParameters", {})


@debug_cmds.command("monitor")
@click.option("--duration", default=10, type=int, help="Monitor duration in seconds")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def debug_monitor(ctx, duration, dry_run, **kwargs):
    """Monitor parameter changes"""
    execute_command(ctx, "develop.monitorParameterChanges", {"duration": duration})


@debug_cmds.command("probe")
@json_input_options
@click.pass_context
def debug_probe(ctx, **kwargs):
    """Probe all develop parameters"""
    execute_command(ctx, "develop.probeAllDevelopParameters", {})


# --- Color operation commands ---


@develop.group("color")
def color_cmds():
    """Color operation commands"""
    pass


@color_cmds.command("green-swatch")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def color_green_swatch(ctx, dry_run, **kwargs):
    """Create green color swatch"""
    execute_command(ctx, "develop.createGreenSwatch", {})


@color_cmds.command("cyan-swatch")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def color_cyan_swatch(ctx, dry_run, **kwargs):
    """Create cyan color swatch"""
    execute_command(ctx, "develop.createCyanSwatch", {})


@color_cmds.command("enhance")
@click.option("--preset", default=None, help="Enhancement preset (natural/vivid/muted)")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def color_enhance(ctx, preset, dry_run, **kwargs):
    """Enhance colors"""
    params = {"preset": preset} if preset else {}
    execute_command(ctx, "develop.enhanceColors", params)


# --- Mask/filter reset commands ---


@develop.command("reset-gradient")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def reset_gradient(ctx, dry_run, **kwargs):
    """Reset gradient filter"""
    execute_command(ctx, "develop.resetGradient", {})


@develop.command("reset-circular")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def reset_circular(ctx, dry_run, **kwargs):
    """Reset circular gradient filter"""
    execute_command(ctx, "develop.resetCircularGradient", {})


@develop.command("reset-brush")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def reset_brush(ctx, dry_run, **kwargs):
    """Reset adjustment brush"""
    execute_command(ctx, "develop.resetBrushing", {})


@develop.command("reset-masking")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def reset_masking(ctx, dry_run, **kwargs):
    """Reset masking (DEPRECATED: use 'lr develop ai reset')"""
    click.echo(
        "Warning: 'lr develop reset-masking' is deprecated. Use 'lr develop ai reset' instead.",
        err=True,
    )
    execute_command(ctx, "develop.resetMasking", {})


# --- LrDevelopController reset/edit commands ---


@develop.command("reset-crop")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def reset_crop(ctx, dry_run, **kwargs):
    """Reset crop"""
    execute_command(ctx, "develop.resetCrop", {})


@develop.command("reset-transforms")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def reset_transforms(ctx, dry_run, **kwargs):
    """Reset transforms"""
    execute_command(ctx, "develop.resetTransforms", {})


@develop.command("reset-spot")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def reset_spot(ctx, dry_run, **kwargs):
    """Reset spot removal"""
    execute_command(ctx, "develop.resetSpotRemoval", {})


@develop.command("reset-redeye")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def reset_redeye(ctx, dry_run, **kwargs):
    """Reset red eye removal"""
    execute_command(ctx, "develop.resetRedeye", {})


@develop.command("reset-healing")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def reset_healing(ctx, dry_run, **kwargs):
    """Reset healing"""
    execute_command(ctx, "develop.resetHealing", {})


@develop.command("edit-in-photoshop")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def edit_in_photoshop(ctx, dry_run, **kwargs):
    """Open current photo in Photoshop"""
    execute_command(ctx, "develop.editInPhotoshop", {})
