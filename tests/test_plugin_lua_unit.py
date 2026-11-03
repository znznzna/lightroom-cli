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

Locally the whole module is skipped if ``lupa`` is not installed. On CI (``CI`` is set,
as GitHub Actions does) a missing ``lupa`` is a collection error instead: it is part of
``.[dev]``, so a skip there would silently drop these checks.
"""

import json
import os
from pathlib import Path

import pytest

if os.environ.get("CI"):
    import lupa  # noqa: F401  # must fail loudly on CI
else:
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


class TestConfigGet:
    """Config:get must keep an explicit false instead of falling back to the default."""

    @pytest.fixture
    def config(self):
        rt = _make_runtime()
        rt.execute(
            """
            PREFS = {}
            local permissive_import = import
            function import(name)
                if name == 'LrPrefs' then
                    return { prefsForPlugin = function() return PREFS end }
                end
                return permissive_import(name)
            end
            """
        )
        cfg = _load(rt, "Config")
        rt.eval("(require('Config')):init()")
        return rt, cfg

    def test_explicit_false_is_kept(self, config):
        rt, _ = config
        rt.execute("PREFS.autoStart = false")
        assert rt.eval("(require('Config')):get('autoStart')") is False
        assert rt.eval("(require('Config')):getAll().autoStart") is False

    def test_missing_value_uses_default(self, config):
        rt, _ = config
        rt.execute("PREFS.autoStart = nil")
        assert rt.eval("(require('Config')):get('autoStart')") is True

    def test_init_fills_defaults_but_keeps_false(self, config):
        rt, _ = config
        rt.execute("PREFS.enableDevelopSync = false; (require('Config')):init()")
        assert rt.eval("PREFS.enableDevelopSync") is False
        assert rt.eval("PREFS.serverPort") == 54321


class TestWriteAccess:
    """withWriteAccessDo returning "aborted" must not be reported as success (codex-overall #19)."""

    @pytest.fixture
    def rt(self):
        rt = _make_runtime()
        rt.execute(
            """
            -- A catalog whose write lock is either free ("executed") or held elsewhere ("aborted").
            -- withWriteAccessDo only runs the function when it gets the lock, like Lightroom does.
            WRITE_STATUS = "executed"
            WRITES = {}
            PHOTO = { setRawMetadata = function(self, key, value) WRITES[#WRITES + 1] = key end }
            CATALOG = {
                withWriteAccessDo = function(self, name, func, timeoutParams)
                    if WRITE_STATUS == "aborted" then return "aborted" end
                    func()
                    return "executed"
                end,
                getPhotoByLocalId = function(self, id) return PHOTO end,
                removePhoto = function(self, photo) WRITES[#WRITES + 1] = "removed" end,
            }
            local permissive_import = import
            function import(name)
                if name == 'LrApplication' then
                    return { activeCatalog = function() return CATALOG end }
                end
                if name == 'LrTasks' then
                    return { pcall = pcall, startAsyncTask = function(f) f() end, yield = function() end }
                end
                return permissive_import(name)
            end
            RESPONSES = {}
            function RECORD(response) RESPONSES[#RESPONSES + 1] = response end
            """
        )
        return rt

    def test_run_raises_when_aborted(self, rt):
        rt.execute("WRITE_STATUS = 'aborted'")
        ok, err = rt.eval(
            "(function() local W = require('WriteAccess'); "
            "return pcall(W.run, CATALOG, 'Set Rating', function() WRITES[1] = 'x' end, { timeout = 10 }) end)()"
        )
        assert ok is False
        assert err.startswith("WRITE_ACCESS_BLOCKED")
        assert rt.eval("#WRITES") == 0

    def test_run_returns_status_when_executed(self, rt):
        assert rt.eval("(require('WriteAccess').run(CATALOG, 'Set Rating', function() end, { timeout = 10 }))") == (
            "executed"
        )

    def test_set_rating_reports_error_when_aborted(self, rt):
        rt.execute("WRITE_STATUS = 'aborted'")
        rt.execute("require('CatalogModule').setRating({ photoId = '1', rating = 3 }, RECORD)")
        assert rt.eval("#RESPONSES") == 1
        assert rt.eval("RESPONSES[1].error ~= nil")
        assert "WRITE_ACCESS_BLOCKED" in rt.eval("RESPONSES[1].error.message")
        assert rt.eval("#WRITES") == 0

    def test_set_rating_succeeds_when_executed(self, rt):
        rt.execute("require('CatalogModule').setRating({ photoId = '1', rating = 3 }, RECORD)")
        assert rt.eval("#RESPONSES") == 1
        assert rt.eval("RESPONSES[1].error == nil")
        assert rt.eval("WRITES[1]") == "rating"

    def test_remove_from_catalog_raises_instead_of_never_answering(self, rt):
        """コールバックを書き込み関数の中だけで呼ぶ実装は、aborted だと応答しなかった。
        いまは例外になり、CommandRouter の pcall が HANDLER_ERROR として 1 回だけ応答する"""
        rt.execute("WRITE_STATUS = 'aborted'")
        ok, err = rt.eval(
            "(function() return pcall(require('CatalogModule').removeFromCatalog, { photoId = '1' }, RECORD) end)()"
        )
        assert ok is False
        assert "WRITE_ACCESS_BLOCKED" in err
        assert rt.eval("#RESPONSES") == 0
        assert rt.eval("#WRITES") == 0
