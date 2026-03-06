"""FastMCP server for Lightroom CLI."""

from __future__ import annotations


def main():
    """MCP Server エントリポイント。"""
    from mcp_server._run import run_server

    run_server()
