import click
import logging


@click.group()
@click.version_option(version="0.2.0", prog_name="lr")
@click.option("--output", "-o", type=click.Choice(["json", "text", "table"]),
              default="text", help="Output format")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--timeout", "-t", type=float, default=30.0,
              help="Default command timeout in seconds")
@click.pass_context
def cli(ctx, output, verbose, timeout):
    """Lightroom Classic CLI - control Lightroom from the command line."""
    ctx.ensure_object(dict)
    ctx.obj["output"] = output
    ctx.obj["verbose"] = verbose
    ctx.obj["timeout"] = timeout

    if verbose:
        logging.basicConfig(level=logging.DEBUG)
