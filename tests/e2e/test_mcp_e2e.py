"""MCP Server E2E テスト。Lightroom Classic 実機が必要。

実行方法: pytest tests/e2e/test_mcp_e2e.py -v --run-e2e
CI では除外される。
"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.fixture
def mcp_connection():
    """実機接続用の ConnectionManager"""
    from mcp_server.connection import ConnectionManager

    cm = ConnectionManager()
    yield cm
    import asyncio

    asyncio.get_event_loop().run_until_complete(cm.shutdown())


@pytest.mark.asyncio
async def test_e2e_mcp_ping(mcp_connection):
    """E2E: MCP 経由で Lightroom に ping"""
    result = await mcp_connection.execute("system.ping", {}, timeout=10.0, mutating=False)
    assert result.get("isError") is not True
    assert "result" in result


@pytest.mark.asyncio
async def test_e2e_mcp_catalog_list(mcp_connection):
    """E2E: MCP 経由でカタログ一覧取得"""
    result = await mcp_connection.execute("catalog.list", {}, timeout=30.0, mutating=False)
    assert result.get("isError") is not True


@pytest.mark.asyncio
async def test_e2e_mcp_validation_error(mcp_connection):
    """E2E: バリデーションエラーが MCP 形式で返ること"""
    result = await mcp_connection.execute(
        "catalog.setRating",
        {"photoId": "1", "rating": 99},
        timeout=10.0,
        mutating=True,
    )
    assert result["isError"] is True
    assert result["code"] == "VALIDATION_ERROR"
