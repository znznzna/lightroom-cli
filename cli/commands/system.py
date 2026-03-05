import click
from pathlib import Path
from cli.helpers import execute_command, get_bridge, handle_error, run_async
from cli.output import OutputFormatter
from cli.decorators import json_input_options


@click.group()
def system():
    """System commands (ping, status, reconnect, check-connection)"""
    pass


@system.command()
@json_input_options
@click.pass_context
def ping(ctx, **kwargs):
    """Test connection to Lightroom"""
    execute_command(ctx, "system.ping", {})


@system.command()
@json_input_options
@click.pass_context
def status(ctx, **kwargs):
    """Get Lightroom bridge status"""
    def _add_cli_metadata(data):
        from lightroom_sdk.schema import get_schema_hash
        if isinstance(data, dict):
            data["schema_hash"] = get_schema_hash()
            data["cli_version"] = _get_cli_version()
        return data

    execute_command(ctx, "system.status", {}, post_process=_add_cli_metadata)


def _get_cli_version() -> str:
    try:
        from importlib.metadata import version
        return version("lightroom-cli")
    except Exception:
        return "dev"


@system.command()
@click.pass_context
def reconnect(ctx):
    """Force reconnection to Lightroom"""
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            await bridge.connect()
            await bridge.disconnect()
            await bridge.connect()
            click.echo("Reconnected")
        except Exception as e:
            handle_error(ctx, e, fmt)
        finally:
            await bridge.disconnect()

    run_async(_run())


@system.command("check-connection")
@click.option("--port-file", default=None, help="Path to port file (default: auto-detect)")
@click.pass_context
def check_connection(ctx, port_file):
    """Check if Lightroom is available"""
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    if port_file is None:
        from lightroom_sdk.paths import get_port_file
        port_path = get_port_file()
    else:
        port_path = Path(port_file)
    if not port_path.exists():
        click.echo(
            OutputFormatter.format(
                {"status": "unavailable", "reason": "port file not found"},
                fmt,
            ),
            err=True,
        )
        ctx.exit(3)
        return
    timeout = ctx.obj.get("timeout", 5.0) if ctx.obj else 5.0

    async def _run():
        bridge = get_bridge(port_file=port_file)
        try:
            await bridge.connect()
            await bridge.send_command("system.ping", timeout=timeout)
            click.echo(OutputFormatter.format({"status": "ok"}, fmt))
        except Exception as e:
            handle_error(ctx, e, fmt)
        finally:
            await bridge.disconnect()

    run_async(_run())
