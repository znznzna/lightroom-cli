"""AI Mask CLI commands — lr develop ai <type>"""

import asyncio
import json
import click
from cli.output import OutputFormatter


def get_bridge():
    """ResilientSocketBridge インスタンスを取得（遅延 import）"""
    from lightroom_sdk.resilient_bridge import ResilientSocketBridge
    return ResilientSocketBridge()


def run_async(coro):
    """CLI から async 関数を実行するヘルパー"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


AI_SELECTION_TYPES = ["subject", "sky", "background", "objects", "people", "landscape"]


@click.group("ai")
def ai():
    """AI mask commands (subject, sky, background, people, landscape, objects)"""
    pass


def _make_ai_type_command(selection_type: str, has_part: bool = False, part_choices: list[str] | None = None):
    """各 AI マスクタイプコマンドのファクトリ関数"""

    params = [
        click.Option(["--adjust"], default=None, help="JSON adjustment settings"),
        click.Option(["--adjust-preset"], default=None, help="Named preset (darken-sky, brighten-subject, etc)"),
    ]
    if has_part and part_choices:
        params.insert(0, click.Option(
            ["--part"], default=None,
            type=click.Choice(part_choices),
            help="Specific part to mask",
        ))

    @click.pass_context
    def command_func(ctx, **kwargs):
        adjust = kwargs.get("adjust")
        adjust_preset = kwargs.get("adjust_preset")
        part = kwargs.get("part")
        timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
        fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

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

        async def _run():
            bridge = get_bridge()
            try:
                result = await bridge.send_command(
                    "develop.createAIMaskWithAdjustments",
                    cmd_params,
                    timeout=max(timeout, 60.0),
                )
                click.echo(OutputFormatter.format(result.get("result", result), fmt))
            except Exception as e:
                click.echo(OutputFormatter.format_error(str(e)))
            finally:
                await bridge.disconnect()

        run_async(_run())

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
ai.add_command(_make_ai_type_command(
    "people", has_part=True,
    part_choices=["eyes", "hair", "skin", "lips", "teeth", "clothes"],
))
ai.add_command(_make_ai_type_command(
    "landscape", has_part=True,
    part_choices=["mountain", "tree", "water", "building", "road"],
))
