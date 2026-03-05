"""lr plugin — Lightroom プラグインの管理コマンド"""

import shutil

import click

from lightroom_sdk.paths import (
    PLUGIN_NAME,
    get_lightroom_modules_dir,
    get_plugin_source_dir,
)


@click.group()
def plugin():
    """Manage Lightroom plugin installation."""
    pass


@plugin.command()
@click.option("--dev", is_flag=True, help="Use symlink instead of copy (development mode)")
@click.option("--quiet", "-q", is_flag=True, help="Suppress output")
def install(dev, quiet):
    """Install the Lightroom plugin."""
    source = get_plugin_source_dir()
    dest_dir = get_lightroom_modules_dir()
    dest = dest_dir / PLUGIN_NAME

    if not source.exists():
        click.echo(f"Error: Plugin source not found at {source}", err=True)
        raise SystemExit(1)

    dest_dir.mkdir(parents=True, exist_ok=True)

    if dest.exists() or dest.is_symlink():
        if dest.is_symlink():
            dest.unlink()
        else:
            shutil.rmtree(dest)

    if dev:
        try:
            dest.symlink_to(source)
        except OSError:
            # Windows で symlink 権限がない場合は copytree にフォールバック
            click.echo(
                "Warning: Symlink creation failed. Falling back to copy.",
                err=True,
            )
            shutil.copytree(source, dest)
            if not quiet:
                click.echo(f"Plugin installed (copy fallback) to {dest}")
        else:
            if not quiet:
                click.echo(f"Plugin symlinked: {dest} -> {source}")
    else:
        shutil.copytree(source, dest)
        if not quiet:
            click.echo(f"Plugin installed to {dest}")


@plugin.command()
@click.option("--quiet", "-q", is_flag=True, help="Suppress output")
def uninstall(quiet):
    """Uninstall the Lightroom plugin."""
    dest = get_lightroom_modules_dir() / PLUGIN_NAME

    if not dest.exists() and not dest.is_symlink():
        if not quiet:
            click.echo("Plugin is not installed.")
        return

    if dest.is_symlink():
        dest.unlink()
    else:
        shutil.rmtree(dest)

    if not quiet:
        click.echo("Plugin uninstalled.")


@plugin.command()
def status():
    """Show plugin installation status."""
    dest = get_lightroom_modules_dir() / PLUGIN_NAME
    source = get_plugin_source_dir()

    click.echo(f"Plugin source:  {source}")
    click.echo(f"Install target: {dest}")

    if dest.is_symlink():
        target = dest.resolve()
        click.echo(f"Status:         Installed (symlink -> {target})")
    elif dest.exists():
        click.echo("Status:         Installed (copy)")
    else:
        click.echo("Status:         Not installed")
