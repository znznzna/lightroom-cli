"""lr mcp -- MCP Server 管理コマンド"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import click


def _resolve_lr_mcp_command() -> str:
    """lr-mcp コマンドの絶対パスを解決する。

    Claude Desktop は限られた PATH しか持たないため、
    venv 内の lr-mcp を見つけられない。絶対パスで登録する。
    """
    resolved = shutil.which("lr-mcp")
    if resolved:
        return resolved
    return "lr-mcp"


def _get_claude_config_path() -> Path:
    """Claude Desktop 設定ファイルのパスを返す。"""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif sys.platform == "win32":
        import os

        appdata = os.environ.get("APPDATA", "")
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    else:
        return Path.home() / ".config" / "claude" / "claude_desktop_config.json"


def _get_port_file_for_test() -> str | None:
    """テスト用のポートファイルパスを返す。"""
    return None


def _create_test_client():
    """テスト用の LightroomClient を生成する。テストではこの関数をモックする。"""
    from lightroom_sdk.client import LightroomClient

    port_file = _get_port_file_for_test()
    return LightroomClient(port_file=port_file)


def _read_config(config_path: Path) -> dict:
    """設定ファイルを読み込む。存在しない場合は空 dict。"""
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))
    return {}


def _write_config(config_path: Path, config: dict) -> None:
    """設定ファイルを書き込む。親ディレクトリも作成。"""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _build_mcp_server_entry() -> dict:
    """MCP Server エントリを生成する。コマンドは絶対パスで解決。"""
    return {
        "command": _resolve_lr_mcp_command(),
        "args": [],
    }


@click.group()
def mcp():
    """Manage MCP Server for Claude Desktop / Cowork."""
    pass


@mcp.command()
@click.option("--force", is_flag=True, help="Overwrite existing MCP server entry")
def install(force):
    """Install lightroom-cli MCP server into Claude Desktop config."""
    config_path = _get_claude_config_path()
    config = _read_config(config_path)

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    if "lightroom-cli" in config["mcpServers"] and not force:
        click.echo("lightroom-cli is already installed in the config.\nUse --force to overwrite the existing entry.")
        return

    config["mcpServers"]["lightroom-cli"] = _build_mcp_server_entry()
    _write_config(config_path, config)

    click.echo(f"MCP server installed to {config_path}")
    click.echo("Restart Claude Desktop / Cowork to activate.")


@mcp.command()
def uninstall():
    """Remove lightroom-cli MCP server from Claude Desktop config."""
    config_path = _get_claude_config_path()
    config = _read_config(config_path)

    servers = config.get("mcpServers", {})
    if "lightroom-cli" not in servers:
        click.echo("MCP server is not installed.")
        return

    del servers["lightroom-cli"]
    _write_config(config_path, config)
    click.echo("MCP server uninstalled.")


@mcp.command()
def status():
    """Show MCP server installation status."""
    config_path = _get_claude_config_path()
    config = _read_config(config_path)

    click.echo(f"Config file: {config_path}")

    servers = config.get("mcpServers", {})
    if "lightroom-cli" in servers:
        entry = servers["lightroom-cli"]
        click.echo("Status: Installed")
        click.echo(f"Command: {entry.get('command', 'N/A')}")
    else:
        click.echo("Status: Not installed")
        click.echo("Run 'lr mcp install' to set up.")

    click.echo("fastmcp: Available")


@mcp.command()
def test():
    """Test MCP server by connecting to Lightroom and sending a ping."""
    click.echo("Testing MCP server connection...")
    try:
        import asyncio

        async def _test():
            client = _create_test_client()
            try:
                await client.connect()
                click.echo("Connected to Lightroom.")

                result = await client.ping()
                click.echo(f"Ping response: {result}")
                click.echo("MCP server test: OK")
            finally:
                await client.disconnect()

        asyncio.run(_test())
    except Exception as e:
        click.echo(f"Test failed: {e}", err=True)
        raise SystemExit(1)
