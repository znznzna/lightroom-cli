"""Real unit tests for the plugin's Lua modules, executed in-process via embedded Lua.

These exercise the *actual* plugin Lua functions — no Lightroom required — using
``lupa`` (an embedded Lua runtime; Lua 5.5 in this environment). The string-escaping
and flag logic under test behaves identically across Lua 5.1–5.5, so this faithfully
covers Lightroom Classic's embedded Lua 5.1.4 plugin code. The Lightroom SDK
``import`` mechanism is replaced with a permissive mock so the modules load outside LR.

Covers two Windows-only bugs found during live CLI testing (2026-06-07):

  1. ``MessageProtocol._encodeJSON`` did not escape backslashes, so Windows paths
     produced invalid JSON: ``C:\\Users`` was emitted as ``"C:\\Users"`` and the
     illegal ``\\U`` escape made the Python side reject the whole response (then
     time out). Fix: escape ``\\`` first, before the other escapes.

  2. ``SimpleSocketBridge.startSocketServer`` never reset ``shuttingDown``, so after
     a Stop->Start the socket reconnect logic (gated on that flag) stayed disabled
     and the plugin never reconnected to the CLI listener. Fix: reset the flag on
     start.

The whole module is skipped if ``lupa`` is not installed (e.g. a minimal CI image),
so it never blocks the existing suite.
"""

import json
from pathlib import Path

import pytest

lupa = pytest.importorskip("lupa")
from lupa import LuaRuntime  # noqa: E402

PLUGIN_DIR = Path(__file__).resolve().parent.parent / "lightroom_sdk" / "plugin"


def _make_runtime() -> LuaRuntime:
    """A LuaRuntime with the LR SDK ``import`` stubbed and ``require`` pointed at the plugin."""
    rt = LuaRuntime(unpack_returned_tuples=True)
    rt.execute(
        """
        -- Permissive mock standing in for any Lightroom SDK object: it is callable
        -- and every field access returns another permissive mock (also callable).
        -- Enough for the modules to load and for getLogger()/Config/LrPrefs to no-op.
        local function permissive()
            return setmetatable({}, {
                __index = function() return permissive() end,
                __call  = function() return permissive() end,
            })
        end
        function import(_name) return permissive() end
        """
    )
    rt.execute(f'package.path = "{PLUGIN_DIR.as_posix()}/?.lua;" .. package.path')
    return rt


def _load(rt: LuaRuntime, module_name: str):
    # Parenthesise so require's (possibly multi-value) return is truncated to the
    # single module table — otherwise lupa unpacks it into a Python tuple.
    return rt.eval(f'(require("{module_name}"))')


class TestMessageProtocolEncodeJSON:
    """JSON-escape fix: _encodeJSON must emit valid JSON for Windows paths."""

    @pytest.fixture
    def mp(self):
        rt = _make_runtime()
        return rt, _load(rt, "MessageProtocol")

    def _encode(self, mp, value):
        rt, module = mp
        return module["_encodeJSON"](module, value)

    @pytest.mark.parametrize(
        "value",
        [
            "C:\\Users\\Ken\\2009\\photo.jpg",
            "D:\\Ken\\2009\\2009-06\\2009.06.25 01.39.15.000097 PM.jpg",  # the real selected photo
            "\\\\nas\\share\\file.jpg",  # UNC path
            "plain string, no escapes",
            "",
            'embedded "double quotes"',
            "tab\there",
            "newline\nhere",
            "carriage\rreturn",
            'C:\\dir\\f "q" \t end\n',  # backslash + quote + tab + newline together
        ],
    )
    def test_string_roundtrips_as_valid_json(self, mp, value):
        encoded = self._encode(mp, value)
        # Must parse as JSON (this is what failed pre-fix) and round-trip exactly.
        assert json.loads(encoded) == value

    def test_windows_path_was_the_exact_bug(self, mp):
        # Pre-fix this emitted  "C:\\Users"  -> illegal \\U escape -> json.loads raised.
        encoded = self._encode(mp, "C:\\Users")
        assert encoded == '"C:\\\\Users"'  # backslash doubled
        assert json.loads(encoded) == "C:\\Users"

    def test_object_with_windows_path_value(self, mp):
        """Faithful repro: the real get-selected response was an object with a C:\\ path value."""
        rt, module = mp
        obj = rt.table_from({"path": "D:\\Ken\\2009\\x.jpg", "id": 3763624, "isVirtualCopy": False})
        decoded = json.loads(module["_encodeJSON"](module, obj))
        assert decoded == {"path": "D:\\Ken\\2009\\x.jpg", "id": 3763624, "isVirtualCopy": False}

    def test_array_of_strings(self, mp):
        rt, module = mp
        arr = rt.table("C:\\a\\b.jpg", "plain", 'has "q"')
        assert json.loads(module["_encodeJSON"](module, arr)) == ["C:\\a\\b.jpg", "plain", 'has "q"']

    def test_number_and_boolean(self, mp):
        assert json.loads(self._encode(mp, 42)) == 42
        assert json.loads(self._encode(mp, True)) is True
        assert json.loads(self._encode(mp, False)) is False

    @pytest.mark.xfail(
        reason="encoder escapes only \\n\\r\\t among control chars; other C0 controls (<0x20) "
        "are emitted raw -> invalid JSON. Latent gap, out of scope for the Windows-path fix.",
        strict=False,
    )
    def test_control_char_roundtrips(self, mp):
        value = "bell\x07char"
        assert json.loads(self._encode(mp, value)) == value


class TestSocketBridgeShutdownReset:
    """Reconnect fix: startSocketServer must clear ``shuttingDown`` left by a prior Stop."""

    def test_start_clears_shutting_down(self):
        rt = _make_runtime()
        # Simulate post-Stop state: bridge present, flagged shuttingDown, server stopped.
        rt.execute("_G.LightroomPythonBridge = { shuttingDown = true, socketServerRunning = false }")
        _load(rt, "SimpleSocketBridge")
        # start() resets the flag synchronously, before the LR-dependent socket setup;
        # pcall swallows the expected downstream error from the stubbed SDK.
        rt.execute("pcall(require('SimpleSocketBridge').start)")
        assert rt.eval("_G.LightroomPythonBridge.shuttingDown") is False

    def test_guard_skips_reset_when_already_running(self):
        """When the server is already running the guard returns early — before the reset."""
        rt = _make_runtime()
        rt.execute("_G.LightroomPythonBridge = { shuttingDown = true, socketServerRunning = true }")
        _load(rt, "SimpleSocketBridge")
        rt.execute("pcall(require('SimpleSocketBridge').start)")
        assert rt.eval("_G.LightroomPythonBridge.shuttingDown") is True
