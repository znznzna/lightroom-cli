"""AI Mask CLI commands — lr develop ai <type>"""

import json

import click

from cli.decorators import json_input_options
from cli.helpers import execute_command
from cli.output import OutputFormatter

AI_SELECTION_TYPES = ["subject", "sky", "background", "objects", "people", "landscape"]


@click.group("ai")
def ai():
    """AI mask commands (subject, sky, background, people, landscape, objects)"""
    pass


def _make_ai_type_command(selection_type: str, has_part: bool = False, part_choices: list[str] | None = None):
    """各 AI マスクタイプコマンドのファクトリ関数"""

    params = [
        click.Option(["--adjust"], default=None, help="JSON adjustment settings"),
        click.Option(
            ["--adjust-preset"],
            default=None,
            help="Named preset (darken-sky, brighten-subject, etc)",
        ),
        click.Option(["--dry-run"], is_flag=True, default=False, help="Preview without executing"),
        click.Option(["--json", "json_str"], default=None, help="JSON string with all parameters"),
        click.Option(
            ["--json-stdin", "json_stdin"],
            is_flag=True,
            default=False,
            help="Read JSON parameters from stdin",
        ),
    ]
    # --part is hidden until SDK support is verified
    if has_part and part_choices:
        params.insert(
            0,
            click.Option(
                ["--part"],
                default=None,
                type=click.Choice(part_choices),
                help="Specific part to mask",
                hidden=True,
            ),
        )

    @click.pass_context
    def command_func(ctx, **kwargs):
        adjust = kwargs.get("adjust")
        adjust_preset = kwargs.get("adjust_preset")
        part = kwargs.get("part")

        # Build params
        cmd_params: dict = {"selectionType": selection_type}
        if part:
            cmd_params["part"] = part

        # Resolve adjustments
        adjustments = _resolve_adjustments(adjust, adjust_preset)
        if isinstance(adjustments, str):
            # Error message
            click.echo(OutputFormatter.format_error(adjustments))
            return
        if adjustments:
            cmd_params["adjustments"] = adjustments

        execute_command(ctx, "develop.createAIMaskWithAdjustments", cmd_params, timeout=60.0)

    cmd = click.Command(
        name=selection_type,
        callback=command_func,
        params=params,
        help=f"Create AI {selection_type} mask",
    )
    return cmd


def _resolve_adjustments(adjust_json: str | None, adjust_preset: str | None) -> dict | str | None:
    """--adjust JSON と --adjust-preset を解決する。エラー時は文字列を返す。"""
    if adjust_json and adjust_preset:
        return "Cannot use both --adjust and --adjust-preset"

    if adjust_preset:
        from lightroom_sdk.presets import get_preset

        preset = get_preset(adjust_preset)
        if preset is None:
            from lightroom_sdk.presets import list_presets

            available = ", ".join(list_presets())
            return f"Unknown preset '{adjust_preset}'. Available: {available}"
        return preset

    if adjust_json:
        try:
            parsed = json.loads(adjust_json)
            if not isinstance(parsed, dict):
                return "--adjust must be a JSON object"
            return parsed
        except json.JSONDecodeError as e:
            return f"Invalid JSON in --adjust: {e}"

    return None


# Register type commands
ai.add_command(_make_ai_type_command("subject"))
ai.add_command(_make_ai_type_command("sky"))
ai.add_command(_make_ai_type_command("background"))
ai.add_command(_make_ai_type_command("objects"))
ai.add_command(
    _make_ai_type_command(
        "people",
        has_part=True,
        part_choices=["eyes", "hair", "skin", "lips", "teeth", "clothes"],
    )
)
ai.add_command(
    _make_ai_type_command(
        "landscape",
        has_part=True,
        part_choices=["mountain", "tree", "water", "building", "road"],
    )
)


@ai.command("presets")
@click.pass_context
def ai_presets(ctx):
    """List available adjustment presets"""
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
    from lightroom_sdk.presets import AI_MASK_PRESETS

    click.echo(OutputFormatter.format(AI_MASK_PRESETS, fmt))


@ai.command("reset")
@click.option(
    "--confirm",
    is_flag=True,
    default=False,
    help="Required confirmation flag (removes all masks)",
)
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def ai_reset(ctx, confirm, dry_run, **kwargs):
    """Remove all masks from the current photo (requires --confirm)"""
    if not confirm and not dry_run:
        fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
        click.echo(
            OutputFormatter.format_error(
                "This will remove all masks. Pass --confirm to proceed.",
                fmt,
                code="CONFIRMATION_REQUIRED",
                suggestions=[
                    "Add --confirm flag: lr develop ai reset --confirm",
                    "Use --dry-run first to preview: lr develop ai reset --dry-run",
                ],
            ),
            err=True,
        )
        ctx.exit(2)
        return
    execute_command(ctx, "develop.resetMasking", {})


@ai.command("list")
@json_input_options
@click.pass_context
def ai_list(ctx, **kwargs):
    """List all masks on the current photo"""
    execute_command(ctx, "develop.getAllMasks", {})


@ai.command("batch")
@click.argument("type", type=click.Choice(AI_SELECTION_TYPES))
@click.option("--photos", default=None, help="Comma-separated photo IDs")
@click.option("--all-selected", is_flag=True, help="Apply to all selected photos")
@click.option("--adjust", default=None, help="JSON adjustment settings")
@click.option("--adjust-preset", default=None, help="Named preset")
@click.option("--dry-run", is_flag=True, help="Show targets without applying")
@click.option("--continue-on-error", is_flag=True, default=False, help="Continue on errors")
@json_input_options
@click.pass_context
def ai_batch(
    ctx,
    type,
    photos,
    all_selected,
    adjust,
    adjust_preset,
    dry_run,
    continue_on_error,
    **kwargs,
):
    """Apply AI mask to multiple photos"""
    if not photos and not all_selected:
        click.echo(OutputFormatter.format_error("Specify --photos or --all-selected"))
        return

    if dry_run:
        target = "all selected photos" if all_selected else f"photos: {photos}"
        click.echo(f"Dry run: would apply AI {type} mask to {target}")
        return

    # Resolve adjustments
    adjustments = _resolve_adjustments(adjust, adjust_preset)
    if isinstance(adjustments, str):
        click.echo(OutputFormatter.format_error(adjustments))
        return

    cmd_params: dict = {
        "selectionType": type,
        "allSelected": all_selected,
        "continueOnError": continue_on_error,
    }
    if photos:
        cmd_params["photoIds"] = [p.strip() for p in photos.split(",")]
    if adjustments:
        cmd_params["adjustments"] = adjustments

    execute_command(ctx, "develop.batchAIMask", cmd_params, timeout=300.0)
