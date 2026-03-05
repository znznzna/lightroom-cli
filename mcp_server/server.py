"""FastMCP server for Lightroom CLI.

Requires: pip install lightroom-cli[mcp]
"""

from __future__ import annotations

import sys


def main():
    """MCP Server エントリポイント。fastmcp 未インストール時はガイダンス表示。"""
    try:
        from fastmcp import FastMCP  # noqa: F401
    except ImportError:
        print(
            "Error: fastmcp is not installed.\nInstall with: pip install lightroom-cli[mcp]\n",
            file=sys.stderr,
        )
        sys.exit(1)

    from mcp_server._run import run_server

    run_server()
