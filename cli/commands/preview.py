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


@click.group()
def preview():
    """Preview commands (generate, generate-current, generate-batch)"""
    pass


@preview.command("generate-current")
@click.pass_context
def generate_current(ctx):
    """Generate preview for currently selected photo"""
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "preview.generatePreview", {}, timeout=120.0
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@preview.command("generate")
@click.option("--size", default=1024, type=int, help="Preview size in pixels")
@click.option("--format", "fmt", default="jpeg", type=click.Choice(["jpeg", "png"]))
@click.pass_context
def generate(ctx, size, fmt):
    """Generate preview with specified size and format"""
    output_fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "preview.generatePreview", {"size": size, "format": fmt}, timeout=120.0
            )
            click.echo(OutputFormatter.format(result.get("result", result), output_fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@preview.command("generate-batch")
@click.pass_context
def generate_batch(ctx):
    """Generate batch previews (timeout: 300s)"""
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "preview.generateBatchPreviews", {}, timeout=300.0
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@preview.command("info")
@click.argument("photo_id")
@click.pass_context
def preview_info(ctx, photo_id):
    """Get preview info for a photo"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "preview.getPreviewInfo", {"photoId": photo_id}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())
