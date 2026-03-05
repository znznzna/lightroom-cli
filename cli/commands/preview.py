import click
from cli.helpers import execute_command


@click.group()
def preview():
    """Preview commands (generate, generate-current, generate-batch)"""
    pass


@preview.command("generate-current")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@click.pass_context
def generate_current(ctx, dry_run):
    """Generate preview for currently selected photo"""
    execute_command(ctx, "preview.generatePreview", {}, timeout=120.0)


@preview.command("generate")
@click.option("--size", default=1024, type=int, help="Preview size in pixels")
@click.option("--format", "fmt", default="jpeg", type=click.Choice(["jpeg", "png"]))
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@click.pass_context
def generate(ctx, size, fmt, dry_run):
    """Generate preview with specified size and format"""
    execute_command(ctx, "preview.generatePreview", {"size": size, "format": fmt}, timeout=120.0)


@preview.command("generate-batch")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@click.pass_context
def generate_batch(ctx, dry_run):
    """Generate batch previews (timeout: 300s)"""
    execute_command(ctx, "preview.generateBatchPreviews", {}, timeout=300.0)


@preview.command("info")
@click.argument("photo_id")
@click.pass_context
def preview_info(ctx, photo_id):
    """Get preview info for a photo"""
    execute_command(ctx, "preview.getPreviewInfo", {"photoId": photo_id})
