"""Server bootstrap (separated to avoid import of fastmcp at module level)."""

from __future__ import annotations


def run_server():
    from fastmcp import FastMCP

    from mcp_server.instructions import INSTRUCTIONS
    from mcp_server.tool_registry import register_all_tools
    from mcp_server.connection import ConnectionManager

    mcp = FastMCP(
        name="lightroom-cli",
        instructions=INSTRUCTIONS,
    )

    connection = ConnectionManager()
    register_all_tools(mcp, connection)

    # lightroom://status リソース登録
    @mcp.resource("lightroom://status")
    async def lightroom_status():
        """Lightroom 接続状態を返す MCP リソース。
        connected: bool, state: str (disconnected/connecting/connected/reconnecting/shutdown)
        """
        return await connection.get_status()

    mcp.run()
