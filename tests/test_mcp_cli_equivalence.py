"""CLI と MCP でバリデーション結果が一致することを確認。"""

import pytest
import pytest_asyncio

from lightroom_sdk.validation import ValidationError, validate_params


class TestValidationEquivalence:
    """CLI と MCP は同一の validate_params を使うため、結果は同一であること。"""

    def test_valid_params_pass(self):
        """正常パラメータが通ること"""
        result = validate_params("catalog.setRating", {"photoId": "1", "rating": 3})
        assert result["photoId"] == "1"
        assert result["rating"] == 3

    def test_unknown_param_raises(self):
        """不明パラメータでエラー"""
        with pytest.raises(ValidationError) as exc_info:
            validate_params("catalog.setRating", {"photoId": "1", "rating": 3, "bad": "x"})
        assert "bad" in str(exc_info.value)

    def test_missing_required_raises(self):
        """必須パラメータ欠落でエラー"""
        with pytest.raises(ValidationError):
            validate_params("catalog.setRating", {"photoId": "1"})

    def test_type_coercion(self):
        """文字列 -> 数値の型変換"""
        result = validate_params("catalog.setRating", {"photoId": "1", "rating": "3"})
        assert result["rating"] == 3

    def test_range_validation(self):
        """範囲外でエラー"""
        with pytest.raises(ValidationError):
            validate_params("catalog.setRating", {"photoId": "1", "rating": 10})

    def test_enum_validation(self):
        """ENUM のバリデーション"""
        result = validate_params("catalog.setColorLabel", {"photoId": "1", "label": "red"})
        assert result["label"] == "red"

        with pytest.raises(ValidationError):
            validate_params("catalog.setColorLabel", {"photoId": "1", "label": "orange"})

    def test_unknown_command_passes_through(self):
        """スキーマ未定義のコマンドはバリデーションスキップ"""
        result = validate_params("unknown.command", {"any": "param"})
        assert result == {"any": "param"}


def _cli(args: list[str]):
    """Run the real CLI entry point (it owns its event loop, so call it from a worker thread)"""
    from click.testing import CliRunner

    from cli.main import cli

    return CliRunner().invoke(cli, ["-o", "json", *args])


@pytest_asyncio.fixture
async def mcp_server(mock_lr_server):
    """The public MCP entry point: FastMCP tools as registered for agents"""
    fastmcp = pytest.importorskip("fastmcp")

    from mcp_server.connection import ConnectionManager
    from mcp_server.tool_registry import register_all_tools

    server = fastmcp.FastMCP(name="equivalence-test")
    connection = ConnectionManager(port_file=str(mock_lr_server.port_file))
    register_all_tools(server, connection)
    yield server
    await connection.shutdown()


async def _call_mcp_tool(server, tool: str, arguments: dict):
    from fastmcp import Client

    async with Client(server) as client:
        # An unknown tool is also an error result: make sure a rejection is about the input
        assert tool in {t.name for t in await client.list_tools()}, f"{tool} is not registered"
        return await client.call_tool(tool, arguments, raise_on_error=False)


def _mcp_rejected(result) -> bool:
    """Rejected either by FastMCP's argument check or by the server's own validation"""
    if result.is_error:
        return True
    payload = result.structured_content or {}
    return payload.get("isError") is True and payload.get("code") == "VALIDATION_ERROR"


class TestSameInputSameOutcome:
    """The same parameters through the CLI and the public MCP tools lead to the same outcome
    (codex-tests #11).

    Replaces a check that both imported the same validate_params: that stayed green even if an
    entry point stopped calling it. The error text differs by design (FastMCP rejects some input
    before the server's validation runs), so the outcome compared is: rejected without reaching
    Lightroom, or the exact params Lightroom receives.
    """

    @pytest.mark.parametrize(
        "command, tool, cli_path, params",
        [
            (
                "catalog.setRating",
                "lr_catalog_set_rating",
                ["catalog", "set-rating", "1", "0"],
                {"photoId": "1", "rating": 10},
            ),
            ("catalog.setRating", "lr_catalog_set_rating", ["catalog", "set-rating", "1", "0"], {"photoId": "1"}),
            (
                "catalog.setRating",
                "lr_catalog_set_rating",
                ["catalog", "set-rating", "1", "0"],
                {"photoId": "1", "rating": 3, "bad": "x"},
            ),
            (
                "catalog.setColorLabel",
                "lr_catalog_set_color_label",
                ["catalog", "set-color-label", "1", "red"],
                {"photoId": "1", "label": "orange"},
            ),
        ],
        ids=["out-of-range", "missing-required", "unknown-param", "bad-enum"],
    )
    async def test_invalid_input_is_rejected_by_both(
        self, mock_lr_server, mcp_server, monkeypatch, command, tool, cli_path, params
    ):
        import asyncio
        import json

        monkeypatch.setenv("LR_PORT_FILE", str(mock_lr_server.port_file))
        cli_result = await asyncio.to_thread(_cli, [*cli_path, "--json", json.dumps(params)])
        mcp_result = await _call_mcp_tool(mcp_server, tool, params)

        assert cli_result.exit_code == 2, cli_result.output
        assert "VALIDATION_ERROR" in (cli_result.stderr or cli_result.output)
        assert _mcp_rejected(mcp_result), mcp_result
        assert command not in mock_lr_server.received, "invalid input must not reach Lightroom"

    @pytest.mark.parametrize(
        "command, tool, cli_path, params, sent",
        [
            # "3" is coerced to 3 by both entry points
            (
                "catalog.setRating",
                "lr_catalog_set_rating",
                ["catalog", "set-rating", "1", "0"],
                {"photoId": "1", "rating": "3"},
                {"photoId": "1", "rating": 3},
            ),
            (
                "catalog.setColorLabel",
                "lr_catalog_set_color_label",
                ["catalog", "set-color-label", "1", "red"],
                {"photoId": "1", "label": "blue"},
                {"photoId": "1", "label": "blue"},
            ),
        ],
        ids=["set-rating", "set-color-label"],
    )
    async def test_valid_input_reaches_lightroom_identically(
        self, mock_lr_server, mcp_server, monkeypatch, command, tool, cli_path, params, sent
    ):
        """Every tool used by the rejection cases also works with valid input, so those cases cannot
        pass just because the tool or the CLI command is broken"""
        import asyncio
        import json

        mock_lr_server.register_response(command, {"ok": True})
        monkeypatch.setenv("LR_PORT_FILE", str(mock_lr_server.port_file))

        cli_result = await asyncio.to_thread(_cli, [*cli_path, "--json", json.dumps(params)])
        assert cli_result.exit_code == 0, cli_result.output
        mcp_result = await _call_mcp_tool(mcp_server, tool, params)
        assert not mcp_result.is_error, mcp_result
        assert (mcp_result.structured_content or {}).get("result") == {"ok": True}

        assert [r["params"] for r in mock_lr_server.requests if r["command"] == command] == [sent, sent]
