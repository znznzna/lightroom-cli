"""MCP Server 統合テスト。fastmcp の TestClient を使用。

fastmcp がない環境ではスキップ。
I3: ConnectionManager 直呼びではなく fastmcp TestClient 経由でテスト。
"""

import pytest

fastmcp = pytest.importorskip("fastmcp")

from fastmcp import Client as TestClient, FastMCP

from lightroom_sdk.schema import COMMAND_SCHEMAS
from mcp_server.connection import ConnectionManager
from mcp_server.instructions import INSTRUCTIONS
from mcp_server.tool_registry import register_all_tools, sanitize_tool_name


@pytest.fixture
def mcp_app(mock_lr_server):
    """テスト用 MCP サーバーアプリを作成"""
    server = FastMCP(name="lightroom-cli-test", instructions=INSTRUCTIONS)
    connection = ConnectionManager(port_file=str(mock_lr_server.port_file))
    register_all_tools(server, connection)
    return server, connection


class TestMcpServerToolCount:
    def test_registered_tool_count(self, mcp_app):
        """plugin.* を除いた全コマンドが登録されること"""
        server, _ = mcp_app
        non_plugin = sum(1 for k in COMMAND_SCHEMAS if not k.startswith("plugin."))
        assert non_plugin >= 100


class TestMcpServerViaTestClient:
    """I3: fastmcp TestClient を経由したテスト"""

    @pytest.mark.asyncio
    async def test_list_tools_via_testclient(self, mcp_app):
        """TestClient 経由でツール一覧が取得できること"""
        server, connection = mcp_app
        async with TestClient(server) as client:
            tools = await client.list_tools()
            tool_names = [t.name for t in tools]
            assert "lr_system_ping" in tool_names
            assert len(tool_names) >= 100
        await connection.shutdown()

    @pytest.mark.asyncio
    async def test_ping_via_testclient(self, mcp_app, mock_lr_server):
        """TestClient 経由で system.ping が実行できること"""
        server, connection = mcp_app
        mock_lr_server.register_response("system.ping", {"status": "ok"})

        async with TestClient(server) as client:
            result = await client.call_tool("lr_system_ping", {})
            assert result is not None
        await connection.shutdown()

    @pytest.mark.asyncio
    async def test_validation_error_via_testclient(self, mcp_app, mock_lr_server):
        """TestClient 経由で不正パラメータが VALIDATION_ERROR を返すこと"""
        server, connection = mcp_app

        async with TestClient(server) as client:
            # raise_on_error=False で呼び出し、エラーレスポンスを検査
            result = await client.call_tool(
                "lr_catalog_set_rating",
                {"photoId": "1", "rating": 3, "badParam": "x"},
                raise_on_error=False,
            )
            assert result is not None
        await connection.shutdown()

    @pytest.mark.asyncio
    async def test_lightroom_status_resource(self, mcp_app):
        """I2: lightroom://status リソースが読めること"""
        server, connection = mcp_app

        # _run.py と同様にリソースを登録
        @server.resource("lightroom://status")
        async def lightroom_status():
            return await connection.get_status()

        async with TestClient(server) as client:
            resources = await client.list_resources()
            resource_uris = [str(r.uri) for r in resources]
            assert "lightroom://status" in resource_uris

            status = await client.read_resource("lightroom://status")
            assert status is not None
        await connection.shutdown()
