import click
from pathlib import Path
from cli.helpers import execute_command, get_bridge, run_async
from cli.output import OutputFormatter


@click.group()
def system():
    """System commands (ping, status, reconnect, check-connection)"""
    pass


@system.command()
@click.pass_context
def ping(ctx):
    """Test connection to Lightroom"""
    execute_command(ctx, "system.ping", {})


@system.command()
@click.pass_context
def status(ctx):
    """Get Lightroom bridge status"""
    execute_command(ctx, "system.status", {})


@system.command()
def reconnect():
    """Force reconnection to Lightroom"""
    async def _run():
        bridge = get_bridge()
        try:
            await bridge.connect()
            await bridge.disconnect()
            await bridge.connect()
            click.echo("Reconnected")
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)), err=True)
        finally:
            await bridge.disconnect()

    run_async(_run())


@system.command("check-connection")
@click.option("--port-file", default=None, help="Path to port file (default: auto-detect)")
@click.pass_context
def check_connection(ctx, port_file):
    """Check if Lightroom is available"""
    if port_file is None:
        from lightroom_sdk.paths import get_port_file
        port_path = get_port_file()
    else:
        port_path = Path(port_file)
    if not port_path.exists():
        click.echo("Lightroom connection unavailable: port file not found")
        return
    timeout = ctx.obj.get("timeout", 5.0) if ctx.obj else 5.0

    async def _run():
        bridge = get_bridge(port_file=port_file)
        try:
            await bridge.connect()
            await bridge.send_command("system.ping", timeout=timeout)
            click.echo("Lightroom connection: ok")
        except Exception as e:
            click.echo(f"Lightroom connection unavailable: {e}")
        finally:
            await bridge.disconnect()

    run_async(_run())
