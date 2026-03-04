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
def catalog():
    """Catalog commands (list, search, find, get-selected, get-info, set-rating, add-keywords, set-flag, get-flag)"""
    pass


@catalog.command("get-selected")
@click.pass_context
def get_selected(ctx):
    """Get currently selected photos"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("catalog.getSelectedPhotos", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@catalog.command("list")
@click.option("--limit", default=50, type=int, help="Max photos to return")
@click.option("--offset", default=0, type=int, help="Offset for pagination")
@click.pass_context
def list_photos(ctx, limit, offset):
    """List photos in catalog"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.getAllPhotos", {"limit": limit, "offset": offset}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@catalog.command("search")
@click.argument("query")
@click.option("--limit", default=50, type=int)
@click.pass_context
def search(ctx, query, limit):
    """Search photos by keyword"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.searchPhotos", {"query": query, "limit": limit}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@catalog.command("get-info")
@click.argument("photo_id")
@click.pass_context
def get_info(ctx, photo_id):
    """Get detailed info for a photo"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.getPhotoMetadata", {"photoId": photo_id}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@catalog.command("set-rating")
@click.argument("photo_id")
@click.argument("rating", type=int)
@click.pass_context
def set_rating(ctx, photo_id, rating):
    """Set photo rating (0-5)"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.setRating", {"photoId": photo_id, "rating": rating}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@catalog.command("add-keywords")
@click.argument("photo_id")
@click.argument("keywords", nargs=-1, required=True)
@click.pass_context
def add_keywords(ctx, photo_id, keywords):
    """Add keywords to a photo"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.addKeywords", {"photoId": photo_id, "keywords": list(keywords)},
                timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@catalog.command("set-flag")
@click.argument("photo_id")
@click.argument("flag", type=click.Choice(["pick", "reject", "none"]))
@click.pass_context
def set_flag(ctx, photo_id, flag):
    """Set photo flag (pick/reject/none)"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
    flag_map = {"pick": 1, "reject": -1, "none": 0}

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.setFlag",
                {"photoId": photo_id, "flag": flag_map[flag]},
                timeout=timeout,
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@catalog.command("get-flag")
@click.argument("photo_id")
@click.pass_context
def get_flag(ctx, photo_id):
    """Get photo flag status"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.getFlag", {"photoId": photo_id}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@catalog.command("find")
@click.option("--flag", type=click.Choice(["pick", "reject", "none"]), help="Flag condition")
@click.option("--rating", type=int, help="Rating (0-5)")
@click.option("--rating-op", default="==", help="Rating comparison operator (==, >=, <=, >, <)")
@click.option("--color-label", help="Color label (red/yellow/green/blue/purple/none)")
@click.option("--keyword", multiple=True, help="Keyword (can be specified multiple times)")
@click.option("--has-adjustments", is_flag=True, help="Has develop adjustments")
@click.option("--camera", help="Camera model name")
@click.option("--limit", default=50, type=int, help="Max results")
@click.option("--offset", default=0, type=int, help="Offset for pagination")
@click.pass_context
def find_photos(ctx, flag, rating, rating_op, color_label, keyword, has_adjustments, camera, limit, offset):
    """Find photos by structured criteria"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    search_desc = {}
    if flag:
        search_desc["flag"] = flag
    if rating is not None:
        search_desc["rating"] = rating
        search_desc["ratingOp"] = rating_op
    if color_label:
        search_desc["colorLabel"] = color_label
    if keyword:
        search_desc["keywords"] = list(keyword)
    if has_adjustments:
        search_desc["hasAdjustments"] = True
    if camera:
        search_desc["camera"] = camera

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.findPhotos",
                {"searchDesc": search_desc, "limit": limit, "offset": offset},
                timeout=timeout,
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())
