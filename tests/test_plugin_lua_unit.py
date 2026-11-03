"""Real unit tests for the plugin's Lua modules, executed in-process via embedded Lua.

These exercise the *actual* plugin Lua functions — no Lightroom required — using
``lupa``'s bundled Lua 5.1 runtime (``lupa.lua51``), the same language version as
Lightroom Classic's embedded Lua 5.1.4, so 5.2+ features (``goto``, integer division,
bitwise operators, ``utf8``) fail here exactly as they would in Lightroom. The Lightroom SDK
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
# Lightroom Classic embeds Lua 5.1, so the plugin is tested on the same version
from lupa.lua51 import LuaRuntime  # noqa: E402

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

    def test_every_c0_control_char_roundtrips(self, mp):
        value = "".join(chr(c) for c in range(0x20)) + "bell\x07char\x7f"
        assert json.loads(self._encode(mp, value)) == value


class TestMessageProtocolJSON:
    """JSON grammar for both directions (codex-overall #4 #5): escapes, numbers, nesting, empties."""

    @pytest.fixture
    def mp(self):
        rt = _make_runtime()
        module = _load(rt, "MessageProtocol")
        rt.execute(
            """
            MP = require('MessageProtocol')
            function ROUNDTRIP(text) return MP:_encodeJSON(MP:_decodeJSON(text)) end
            function DECODE_FAILS(text)
                local ok, err = pcall(MP._decodeJSON, MP, text)
                return (not ok) and tostring(err) or nil
            end
            """
        )
        return rt, module

    def _roundtrip(self, rt, value, **dumps_kwargs):
        return json.loads(rt.globals().ROUNDTRIP(json.dumps(value, **dumps_kwargs)))

    @pytest.mark.parametrize(
        "value",
        [
            {"id": "abc", "command": "catalog.search", "params": {"query": "x", "limit": 10}},
            {"s": 'quote " backslash \\ slash / tab \t nl \n cr \r bs \b ff \f'},
            {"s": "C:\\Users\\Ken\\photo.jpg"},
            {"s": "日本語の文字列 🎞️ and emoji"},
            {"s": "".join(chr(c) for c in range(0x20))},
            {"n": -1, "f": 0.5, "neg": -12.75, "e": 1.5e-7, "big": 1e300, "zero": 0, "int": 9007199254740992},
            {"n": 0.1, "m": 1 / 3, "p": 3.141592653589793},
            {"nested": {"a": [1, [2, [3, {"b": [True, False]}]]], "c": {"d": {"e": "deep"}}}},
            {"photoIds": ["1", "2", "3"], "settings": {"Exposure": 0.5, "Contrast": -20}},
            {"empty_list": [], "empty_obj": {}, "list_of_empty": [[], {}]},
            {"t": True, "f": False},
            {'key with "quotes" and \\': "v", "": "empty key"},
        ],
    )
    @pytest.mark.parametrize("ensure_ascii", [True, False], ids=["ascii-escaped", "raw-utf8"])
    def test_python_json_roundtrips_through_lua(self, mp, value, ensure_ascii):
        rt, _ = mp
        assert self._roundtrip(rt, value, ensure_ascii=ensure_ascii) == value

    def test_whitespace_between_tokens(self, mp):
        rt, _ = mp
        text = ' \t\r\n{ "a" : [ 1 , 2 ] ,\n "b" : { } , "c" : [ ] } \n'
        assert json.loads(rt.globals().ROUNDTRIP(text)) == {"a": [1, 2], "b": {}, "c": []}

    def test_null_drops_object_key(self, mp):
        rt, _ = mp
        rt.execute('DECODED = MP:_decodeJSON(\'{"a": null, "b": 1}\')')
        assert rt.eval("DECODED.a == nil")
        assert rt.eval("DECODED.b") == 1

    def test_null_in_array_keeps_length_and_order(self, mp):
        rt, _ = mp
        rt.execute("DECODED = MP:_decodeJSON('[1, null, 3]')")
        assert rt.eval("#DECODED") == 3
        assert rt.eval("DECODED[2] == MP.null")
        assert rt.eval("(function() local n = 0; for _ in ipairs(DECODED) do n = n + 1 end; return n end)()") == 3

    @pytest.mark.parametrize(
        "text, expected",
        [
            ("[1,null,3]", [1, None, 3]),
            ("[null]", [None]),
            ("[null,null]", [None, None]),
            ('{"a":[null,{"b":null}]}', {"a": [None, {}]}),  # null in an object drops the key
        ],
    )
    def test_null_in_array_roundtrips(self, mp, text, expected):
        rt, _ = mp
        assert json.loads(rt.globals().ROUNDTRIP(text)) == expected

    def test_surrogate_pair_decodes_to_utf8(self, mp):
        rt, _ = mp
        decode = rt.eval("function(text) return MP:_decodeJSON(text) end")
        assert decode(r'"\ud83c\udf9e"') == "\U0001f39e"
        assert decode(r'"\u00e9\u65e5"') == "é日"

    def test_lone_surrogate_becomes_replacement_char(self, mp):
        rt, _ = mp
        decode = rt.eval("function(text) return MP:_decodeJSON(text) end")
        assert decode(r'"a\ud83cb"') == "a\ufffdb"
        assert decode(r'"\udf9e"') == "\ufffd"

    def test_number_types(self, mp):
        rt, _ = mp
        assert rt.eval("MP:_decodeJSON('-0.25')") == -0.25
        assert rt.eval("MP:_decodeJSON('1E3')") == 1000
        assert rt.eval("MP:_decodeJSON('2e-2')") == 0.02
        assert rt.eval("MP:_decodeJSON('0')") == 0

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "   ",
            "{",
            '{"a": 1',
            '{"a" 1}',
            '{"a": 1,}',
            "[1, 2,]",
            "[1 2]",
            "{a: 1}",
            "{'a': 1}",
            '"unterminated',
            '"bad escape \\x"',
            '"bad unicode \\u12g4"',
            '"raw\ttab"',
            '"raw\nnewline"',
            "01",
            "-",
            "1.",
            ".5",
            "1e",
            "+1",
            "NaN",
            "Infinity",
            "tru",
            "nul",
            '{"a": 1} trailing',
            "[1] [2]",
            "[" * 300 + "]" * 300,
        ],
    )
    def test_invalid_json_is_rejected(self, mp, text):
        rt, _ = mp
        err = rt.globals().DECODE_FAILS(text)
        assert err is not None, f"accepted invalid JSON: {text!r}"
        assert "invalid JSON at byte" in err

    def test_decode_rejects_non_object_message(self, mp):
        rt, _ = mp
        assert rt.eval("MP:decode('[1, 2]')") is None
        assert rt.eval("MP:decode('\"text\"')") is None
        assert rt.eval('MP:decode(\'{"id": "x", "command": "c"}\').command') == "c"

    def test_non_finite_numbers_encode_as_null(self, mp):
        rt, _ = mp
        encoded = rt.eval("MP:_encodeJSON({ nan = 0/0, inf = math.huge, ninf = -math.huge, ok = 1 })")
        assert json.loads(encoded) == {"nan": None, "inf": None, "ninf": None, "ok": 1}

    def test_numbers_encode_exactly(self, mp):
        rt, _ = mp
        values = [0.1, 1 / 3, -0.5, 1e300, 5e-324, 9007199254740992, 3763624, -42, 123456789012345.6]
        lua_list = "{" + ",".join(repr(v) for v in values) + "}"
        assert json.loads(rt.eval(f"MP:_encodeJSON({lua_list})")) == values
        assert rt.eval("MP:_encodeJSON(3763624)") == "3763624"
        assert rt.eval("MP:_encodeJSON(0.5)") == "0.5"

    def test_marked_empty_array_encodes_as_array(self, mp):
        rt, _ = mp
        assert rt.eval("MP:_encodeJSON({ photos = MP.array(), result = {} })") in (
            '{"photos":[],"result":{}}',
            '{"result":{},"photos":[]}',
        )
        assert rt.eval("MP:_encodeJSON(MP.array({ 'a', 'b' }))") == '["a","b"]'

    def test_decoded_empty_array_stays_array(self, mp):
        rt, _ = mp
        assert rt.globals().ROUNDTRIP('{"ids": []}') == '{"ids":[]}'

    def test_table_with_array_and_hash_part_encodes_as_object(self, mp):
        rt, _ = mp
        encoded = rt.eval("MP:_encodeJSON({ 'first', 'second', extra = true })")
        assert json.loads(encoded) == {"1": "first", "2": "second", "extra": True}

    def test_marked_table_with_extra_keys_keeps_them(self, mp):
        rt, _ = mp
        encoded = rt.eval("(function() local t = MP.array({ 'a' }); t.total = 1; return MP:_encodeJSON(t) end)()")
        assert json.loads(encoded) == {"1": "a", "total": 1}

    def test_cyclic_table_fails_instead_of_overflowing(self, mp):
        rt, _ = mp
        ok, err = rt.eval("(function() local t = {}; t.self = t; return pcall(MP._encodeJSON, MP, t) end)()")
        assert ok is False
        assert "nested deeper" in err

    def test_encode_failure_returns_nil(self, mp):
        rt, _ = mp
        assert rt.eval("MP:encode({ f = function() end })") is None


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


class TestEmptyResultsAreArrays:
    """Real handlers: an empty list result must reach Python as [] (a list), not {} (codex-overall #5)."""

    @pytest.fixture
    def rt(self):
        rt = _make_runtime()
        rt.execute(
            """
            CATALOG = {
                withReadAccessDo = function(self, func) func() end,
                getChildCollections = function(self) return {} end,
                getKeywords = function(self) return {} end,
                getAllPhotos = function(self) return {} end,
            }
            local permissive_import = import
            function import(name)
                if name == 'LrApplication' then
                    return { activeCatalog = function() return CATALOG end }
                end
                if name == 'LrTasks' then
                    return { pcall = pcall, yield = function() end }
                end
                return permissive_import(name)
            end
            RESPONSES = {}
            function RECORD(response) RESPONSES[#RESPONSES + 1] = response end
            MP = require('MessageProtocol')
            """
        )
        return rt

    @pytest.mark.parametrize(
        "handler, field, count_field",
        [
            ("getCollections", "collections", "count"),
            ("getKeywords", "keywords", "count"),
            ("findPhotos", "photos", "total"),
        ],
    )
    def test_empty_catalog_lists_encode_as_arrays(self, rt, handler, field, count_field):
        rt.execute(f"require('CatalogModule').{handler}({{}}, RECORD)")
        encoded = json.loads(rt.eval("MP:_encodeJSON(RESPONSES[1])"))
        assert encoded["result"][field] == []
        assert encoded["result"][count_field] == 0
