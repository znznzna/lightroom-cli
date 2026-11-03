"""MCP exposes only commands that Lightroom actually has (codex-overall #20).

The plugin's command table is read from its Lua source (`router:register("name", ...)` in
PluginInit.lua), so a schema entry that the plugin does not implement fails here instead of
returning UNKNOWN_COMMAND to an agent at run time.
"""

import re
from pathlib import Path

import pytest

from lightroom_sdk.schema import COMMAND_SCHEMAS
from mcp_server.instructions import INSTRUCTIONS
from mcp_server.tool_registry import register_all_tools, sanitize_tool_name

PLUGIN_INIT = Path(__file__).resolve().parent.parent / "lightroom_sdk" / "plugin" / "PluginInit.lua"


def _lua_commands() -> set[str]:
    source = PLUGIN_INIT.read_text(encoding="utf-8")
    return set(re.findall(r"""router:register\(\s*["']([\w.]+)["']""", source))


class _ToolCollector:
    """Stands in for FastMCP: records the names register_all_tools asks for"""

    def __init__(self):
        self.names: list[str] = []

    def tool(self, name, description):
        def decorator(fn):
            self.names.append(name)
            return fn

        return decorator


@pytest.fixture(scope="module")
def registered_tools() -> list[str]:
    collector = _ToolCollector()
    register_all_tools(collector, connection=None)
    return collector.names


def test_lua_command_table_is_found():
    # Guards the regex: an empty or tiny set would make the checks below pass vacuously
    commands = _lua_commands()
    assert len(commands) > 100
    assert {"system.ping", "develop.createAIMaskWithAdjustments", "develop.resetMasking"} <= commands


def test_every_exposed_command_exists_in_lightroom():
    exposed = {name for name, schema in COMMAND_SCHEMAS.items() if not schema.cli_only}
    missing = sorted(exposed - _lua_commands())
    assert missing == [], f"MCP would expose commands the plugin does not register: {missing}"


def test_cli_only_commands_are_not_in_lightroom():
    """cli_only must mean it: a command Lightroom does have should not be hidden from MCP"""
    cli_only = {name for name, schema in COMMAND_SCHEMAS.items() if schema.cli_only}
    assert sorted(cli_only & _lua_commands()) == []


@pytest.mark.parametrize(
    "command",
    [
        "develop.ai.sky",
        "develop.ai.subject",
        "develop.ai.people",
        "develop.ai.presets",
        "develop.ai.reset",
        "develop.ai.list",
        "system.reconnect",
        "system.checkConnection",
        "plugin.install",
    ],
)
def test_cli_aliases_are_not_registered_as_tools(registered_tools, command):
    assert sanitize_tool_name(command) not in registered_tools


def test_bridge_equivalents_of_the_aliases_are_registered(registered_tools):
    for command in ["develop.createAIMaskWithAdjustments", "develop.resetMasking", "develop.getAllMasks"]:
        assert sanitize_tool_name(command) in registered_tools


def test_instructions_only_mention_registered_tools(registered_tools):
    mentioned = set(re.findall(r"\blr_[a-z0-9_]+", INSTRUCTIONS))
    assert mentioned, "the instructions should name some tools"
    assert sorted(mentioned - set(registered_tools)) == []
