import os
import click
import logging
from cli.middleware import resolve_output_format, resolve_timeout, resolve_fields
from cli.structured_group import StructuredErrorGroup


@click.group(cls=StructuredErrorGroup)
@click.version_option(version="0.3.0", prog_name="lr")
@click.option("--output", "-o", type=click.Choice(["json", "text", "table"]),
              default=None, help="Output format (default: json for non-TTY, text for TTY)")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--timeout", "-t", type=float, default=None,
              help="Default command timeout in seconds")
@click.option("--fields", "-f", default=None,
              help="Comma-separated response fields to include")
@click.pass_context
def cli(ctx, output, verbose, timeout, fields):
    """Lightroom Classic CLI - control Lightroom from the command line."""
    ctx.ensure_object(dict)
    ctx.obj["output"] = resolve_output_format(output)
    ctx.obj["verbose"] = verbose or bool(os.environ.get("LR_VERBOSE"))
    ctx.obj["timeout"] = resolve_timeout(timeout)
    ctx.obj["fields"] = resolve_fields(fields)

    if ctx.obj["verbose"]:
        logging.basicConfig(level=logging.DEBUG, force=True)
    elif ctx.obj["output"] == "json":
        logging.basicConfig(level=logging.ERROR, force=True)
    else:
        logging.basicConfig(level=logging.WARNING, force=True)


from cli.commands.system import system
from cli.commands.catalog import catalog
from cli.commands.develop import develop
from cli.commands.preview import preview
from cli.commands.selection import selection
from cli.commands.plugin import plugin
from cli.schema import schema_cmd
cli.add_command(system)
cli.add_command(catalog)
cli.add_command(develop)
cli.add_command(preview)
cli.add_command(selection)
cli.add_command(plugin)
cli.add_command(schema_cmd)
