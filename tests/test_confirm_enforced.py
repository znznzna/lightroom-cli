"""Destructive commands need explicit confirmation on every entry point (codex-overall #3).

The check used to live in two CLI commands only: the deprecated `lr develop reset-masking` and
the MCP tools sent the same destructive command without it. Here every path is driven against a
mock Lightroom and must not reach it unconfirmed.
"""

import asyncio
import json

import pytest
import pytest_asyncio
from click.testing import CliRunner

from cli.main import cli
from lightroom_sdk.schema import COMMAND_SCHEMAS
from lightroom_sdk.validation import ConfirmationRequiredError, check_confirmation

DESTRUCTIVE = sorted(
    name for name, schema in COMMAND_SCHEMAS.items() if schema.requires_confirm and not schema.cli_only
)

# Every CLI command that sends a destructive command, and what it sends
CLI_PATHS = [
    (["develop", "ai", "reset"], "develop.resetMasking"),
    (["develop", "reset-masking"], "develop.resetMasking"),  # deprecated alias: used to skip the check
    (["catalog", "remove-from-catalog", "123"], "catalog.removeFromCatalog"),
]


def test_destructive_commands_are_known():
    # Guards the parametrization below: a new destructive command needs its entry points listed
    assert DESTRUCTIVE == ["catalog.removeFromCatalog", "develop.resetMasking"]
    assert sorted({command for _, command in CLI_PATHS}) == DESTRUCTIVE


class TestCheckConfirmation:
    @pytest.mark.parametrize("command", DESTRUCTIVE)
    def test_refuses_unconfirmed(self, command):
        with pytest.raises(ConfirmationRequiredError) as info:
            check_confirmation(command, confirmed=False)
        assert info.value.code == "CONFIRMATION_REQUIRED"
        assert command in str(info.value)

    @pytest.mark.parametrize("command", DESTRUCTIVE)
    def test_allows_confirmed(self, command):
        check_confirmation(command, confirmed=True)

    @pytest.mark.parametrize("command", ["catalog.setRating", "develop.resetAllDevelopAdjustments", "unknown.cmd"])
    def test_other_commands_need_nothing(self, command):
        check_confirmation(command, confirmed=False)


def _cli(args):
    return CliRunner().invoke(cli, ["-o", "json", *args])


def _json(text: str) -> dict:
    """The JSON document in the output (the deprecated alias also prints a warning line first)"""
    start = next(i for i, line in enumerate(text.splitlines(keepends=True)) if line.startswith("{"))
    body = "".join(text.splitlines(keepends=True)[start:])
    return json.JSONDecoder().raw_decode(body)[0]


class TestCli:
    @pytest.mark.parametrize("args, command", CLI_PATHS, ids=[" ".join(a) for a, _ in CLI_PATHS])
    async def test_unconfirmed_is_refused_before_sending(self, mock_lr_server, monkeypatch, args, command):
        monkeypatch.setenv("LR_PORT_FILE", str(mock_lr_server.port_file))
        result = await asyncio.to_thread(_cli, args)
        assert result.exit_code == 2, result.output
        error = _json(result.stderr or result.output)["error"]
        assert error["code"] == "CONFIRMATION_REQUIRED"
        assert any("--confirm" in s for s in error["suggestions"])
        assert mock_lr_server.received == []

    @pytest.mark.parametrize("args, command", CLI_PATHS, ids=[" ".join(a) for a, _ in CLI_PATHS])
    async def test_confirmed_is_sent(self, mock_lr_server, monkeypatch, args, command):
        mock_lr_server.register_response(command, {"ok": True})
        monkeypatch.setenv("LR_PORT_FILE", str(mock_lr_server.port_file))
        result = await asyncio.to_thread(_cli, [*args, "--confirm"])
        assert result.exit_code == 0, result.output
        assert mock_lr_server.received == [command]

    @pytest.mark.parametrize("args, command", CLI_PATHS, ids=[" ".join(a) for a, _ in CLI_PATHS])
    async def test_dry_run_needs_no_confirm_and_sends_nothing(self, mock_lr_server, monkeypatch, args, command):
        monkeypatch.setenv("LR_PORT_FILE", str(mock_lr_server.port_file))
        result = await asyncio.to_thread(_cli, [*args, "--dry-run"])
        assert result.exit_code == 0, result.output
        assert _json(result.output)["dry_run"] is True
        assert mock_lr_server.received == []


@pytest_asyncio.fixture
async def mcp(mock_lr_server):
    fastmcp = pytest.importorskip("fastmcp")

    from mcp_server.connection import ConnectionManager
    from mcp_server.tool_registry import register_all_tools

    server = fastmcp.FastMCP(name="confirm-test")
    connection = ConnectionManager(port_file=str(mock_lr_server.port_file))
    register_all_tools(server, connection)
    async with fastmcp.Client(server) as client:
        yield client
    await connection.shutdown()


TOOLS = {
    "develop.resetMasking": "lr_develop_reset_masking",
    "catalog.removeFromCatalog": "lr_catalog_remove_from_catalog",
}
TOOL_ARGS = {"develop.resetMasking": {}, "catalog.removeFromCatalog": {"photoId": "123"}}


class TestMcp:
    @pytest.mark.parametrize("command", DESTRUCTIVE)
    async def test_tool_offers_confirm(self, mcp, command):
        tools = {t.name: t for t in await mcp.list_tools()}
        assert "confirm" in tools[TOOLS[command]].input_schema["properties"]

    async def test_non_destructive_tools_have_no_confirm(self, mcp):
        destructive_tools = set(TOOLS.values())
        offending = [
            t.name
            for t in await mcp.list_tools()
            if t.name not in destructive_tools and "confirm" in t.input_schema.get("properties", {})
        ]
        assert offending == []

    @pytest.mark.parametrize("command", DESTRUCTIVE)
    async def test_unconfirmed_is_refused_before_sending(self, mcp, mock_lr_server, command):
        result = await mcp.call_tool(TOOLS[command], TOOL_ARGS[command], raise_on_error=False)
        assert result.structured_content["code"] == "CONFIRMATION_REQUIRED"
        assert mock_lr_server.received == []

    @pytest.mark.parametrize("command", DESTRUCTIVE)
    async def test_confirmed_is_sent(self, mcp, mock_lr_server, command):
        mock_lr_server.register_response(command, {"ok": True})
        result = await mcp.call_tool(TOOLS[command], {**TOOL_ARGS[command], "confirm": True}, raise_on_error=False)
        assert result.structured_content == {"result": {"ok": True}}
        assert mock_lr_server.received == [command]

    @pytest.mark.parametrize("command", DESTRUCTIVE)
    async def test_dry_run_needs_no_confirm_and_sends_nothing(self, mcp, mock_lr_server, command):
        result = await mcp.call_tool(TOOLS[command], {**TOOL_ARGS[command], "dry_run": True}, raise_on_error=False)
        assert result.structured_content["dry_run"] is True
        assert mock_lr_server.received == []
