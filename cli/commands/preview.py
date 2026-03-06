import click

from cli.decorators import json_input_options
from cli.helpers import execute_command


@click.group()
def preview():
    """Preview commands (generate, generate-current, generate-batch)"""
    pass


@preview.command("generate-current")
@click.argument("photo_id")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def generate_current(ctx, photo_id, dry_run, **kwargs):
    """Generate preview for a photo"""
    execute_command(ctx, "preview.generatePreview", {"photoId": photo_id}, timeout=120.0)


@preview.command("generate")
@click.argument("photo_id")
@click.option("--size", default=None, type=str, help="Preview size: small, medium, large, or custom number")
@click.option("--format", "fmt", default=None, type=str, help="Output format (default: jpeg)")
@click.option("--quality", default=None, type=int, help="JPEG quality (default: 90)")
@click.option("--base64/--no-base64", default=None, help="Base64 encode output (default: true)")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def generate(ctx, photo_id, size, fmt, quality, base64, dry_run, **kwargs):
    """Generate preview with specified size and format"""
    params = {"photoId": photo_id}
    if size is not None:
        params["size"] = size
    if fmt is not None:
        params["format"] = fmt
    if quality is not None:
        params["quality"] = quality
    if base64 is not None:
        params["base64"] = base64
    execute_command(ctx, "preview.generatePreview", params, timeout=120.0)


@preview.command("generate-batch")
@click.option("--photo-ids", required=True, help="Comma-separated photo IDs")
@click.option("--size", default=None, type=str, help="Preview size: small, medium, large, or custom number")
@click.option("--quality", default=None, type=int, help="JPEG quality (default: 90)")
@click.option("--base64/--no-base64", default=None, help="Base64 encode output (default: true)")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def generate_batch(ctx, photo_ids, size, quality, base64, dry_run, **kwargs):
    """Generate batch previews (timeout: 300s)"""
    params = {"photoIds": [pid.strip() for pid in photo_ids.split(",")]}
    if size is not None:
        params["size"] = size
    if quality is not None:
        params["quality"] = quality
    if base64 is not None:
        params["base64"] = base64
    execute_command(ctx, "preview.generateBatchPreviews", params, timeout=300.0)


@preview.command("info")
@click.argument("photo_id")
@json_input_options
@click.pass_context
def preview_info(ctx, photo_id, **kwargs):
    """Get preview info for a photo"""
    execute_command(ctx, "preview.getPreviewInfo", {"photoId": photo_id})
