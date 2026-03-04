import asyncio
import click
from pathlib import Path
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
def system():
    """System commands (ping, status, reconnect, check-connection)"""
    pass


@system.command()
@click.pass_context
def ping(ctx):
    """Test connection to Lightroom"""
    bridge = get_bridge()
    try:
        result = run_async(bridge.send_command("system.ping"))
        fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
        click.echo(OutputFormatter.format(result.get("result", result), fmt))
    except Exception as e:
        click.echo(OutputFormatter.format_error(str(e)))
    finally:
        run_async(bridge.disconnect())


@system.command()
@click.pass_context
def status(ctx):
    """Get Lightroom bridge status"""
    bridge = get_bridge()
    try:
        result = run_async(bridge.send_command("system.status"))
        fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
        click.echo(OutputFormatter.format(result.get("result", result), fmt))
    except Exception as e:
        click.echo(OutputFormatter.format_error(str(e)))
    finally:
        run_async(bridge.disconnect())


@system.command()
def reconnect():
    """Force reconnection to Lightroom"""
    bridge = get_bridge()
    try:
        run_async(bridge.disconnect())
        run_async(bridge.connect())
        click.echo("Reconnected")
    except Exception as e:
        click.echo(OutputFormatter.format_error(str(e)))
    finally:
        run_async(bridge.disconnect())


@system.command("check-connection")
@click.option("--port-file", default="/tmp/lightroom_ports.txt")
def check_connection(port_file):
    """Check if Lightroom is available"""
    port_path = Path(port_file)
    if not port_path.exists():
        click.echo("Lightroom connection unavailable: port file not found")
        return
    bridge = get_bridge()
    try:
        run_async(bridge.connect())
        run_async(bridge.send_command("system.ping", timeout=5.0))
        click.echo("Lightroom connection: ok")
    except Exception as e:
        click.echo(f"Lightroom connection unavailable: {e}")
    finally:
        run_async(bridge.disconnect())
