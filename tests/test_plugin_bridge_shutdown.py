"""Shutdown tests for the CLI bridge Lua plugin, run in a simulated Lightroom.

Lightroom Classic could hang on quit while the bridge was running. These tests
load the real plugin modules (SimpleSocketBridge, CommandRouter, BridgeShutdown,
AppShutdown, PluginShutdown) in embedded Lua via ``lupa``, with a small fake of
the Lightroom runtime:

* ``LrTasks`` is a cooperative scheduler on coroutines with a virtual clock.
  Tasks only run when the test calls ``run()``, so a test can model "Lightroom
  stopped scheduling plugin tasks during quit" simply by not running it.
* ``LrTasks.sleep`` raises if called inside a plain ``pcall``, as Lua 5.1
  (Lightroom's runtime) cannot yield across ``pcall``; ``LrTasks.pcall`` is fine.
* ``LrSocket.bind`` returns fake sockets that track open/closed state.

The module is skipped if ``lupa`` is not installed.
"""

from pathlib import Path

import pytest

lupa = pytest.importorskip("lupa")
from lupa import LuaRuntime  # noqa: E402

PLUGIN_DIR = Path(__file__).resolve().parent.parent / "lightroom_sdk" / "plugin"

SIM_LUA = r"""
Sim = { now = 0, tasks = {}, sockets = {}, logs = {}, errors = {}, bezels = 0, pcallDepth = 0 }

local rawpcall = pcall
pcall = function(f, ...)
    Sim.pcallDepth = Sim.pcallDepth + 1
    local r = table.pack(rawpcall(f, ...))
    Sim.pcallDepth = Sim.pcallDepth - 1
    return table.unpack(r, 1, r.n)
end

local function lrYield(wake)
    if Sim.pcallDepth > 0 then
        error("attempt to yield across pcall (use LrTasks.pcall)")
    end
    if not coroutine.isyieldable() then
        error("LrTasks.sleep called outside an async task")
    end
    coroutine.yield(wake)
end

local LrTasks = {
    startAsyncTask = function(fn)
        table.insert(Sim.tasks, { co = coroutine.create(fn), wake = Sim.now })
    end,
    sleep = function(s) lrYield(Sim.now + s) end,
    yield = function() lrYield(Sim.now) end,
    pcall = function(f, ...)
        -- yield-safe pcall: does not count as a plain pcall
        local depth = Sim.pcallDepth
        Sim.pcallDepth = 0
        local r = table.pack(rawpcall(f, ...))
        Sim.pcallDepth = depth
        return table.unpack(r, 1, r.n)
    end,
    currentTime = function() return Sim.now end,
}

local function makeLogger()
    local l = {}
    for _, lvl in ipairs({ "info", "debug", "warn", "error", "trace" }) do
        l[lvl] = function(self, msg) table.insert(Sim.logs, lvl .. ": " .. tostring(msg)) end
    end
    l.enable = function() end
    return l
end

local LrSocket = {
    bind = function(params)
        local s = { params = params, closed = false, mode = params.mode }
        function s:close()
            if not self.closed then
                self.closed = true
                if self.params.onClosed then self.params.onClosed(self) end
            end
        end
        function s:reconnect() end
        function s:send(data) end
        table.insert(Sim.sockets, s)
        return s
    end,
}

local modules = {
    LrTasks = LrTasks,
    LrSocket = LrSocket,
    LrFunctionContext = { callWithContext = function(name, fn) return fn({}) end },
    LrDialogs = { showBezel = function() Sim.bezels = Sim.bezels + 1 end, message = function() end },
    LrLogger = function() return makeLogger() end,
    LrFileUtils = {
        exists = function(p) local f = io.open(p, "r"); if f then f:close(); return true end; return false end,
        delete = function(p) os.remove(p) end,
    },
}

local function permissive()
    return setmetatable({}, {
        __index = function() return permissive() end,
        __call = function() return permissive() end,
    })
end

function import(name) return modules[name] or permissive() end

package.loaded["Config"] = {
    init = function() end,
    get = function(self, key)
        if key == "pluginSendPort" then return 54321 end
        if key == "pluginReceivePort" then return 54322 end
    end,
}
package.loaded["PlatformPaths"] = { getPortFilePath = function() return Sim.portFile end }

-- Run the scheduler until the virtual clock passes `untilTime`.
function Sim.run(duration)
    local untilTime = Sim.now + duration
    while true do
        local nextWake = nil
        for _, t in ipairs(Sim.tasks) do
            if coroutine.status(t.co) ~= "dead" and (nextWake == nil or t.wake < nextWake) then
                nextWake = t.wake
            end
        end
        if nextWake == nil or nextWake > untilTime then break end
        if nextWake > Sim.now then Sim.now = nextWake end
        local snapshot = {}
        for _, t in ipairs(Sim.tasks) do snapshot[#snapshot + 1] = t end
        for _, t in ipairs(snapshot) do
            if coroutine.status(t.co) ~= "dead" and t.wake <= Sim.now then
                local ok, wake = coroutine.resume(t.co)
                if not ok then
                    table.insert(Sim.errors, tostring(wake))
                elseif coroutine.status(t.co) ~= "dead" then
                    t.wake = wake or Sim.now
                end
            end
        end
    end
    Sim.now = untilTime
end

function Sim.liveTasks()
    local n = 0
    for _, t in ipairs(Sim.tasks) do
        if coroutine.status(t.co) ~= "dead" then n = n + 1 end
    end
    return n
end

function Sim.openSockets()
    local n = 0
    for _, s in ipairs(Sim.sockets) do
        if not s.closed then n = n + 1 end
    end
    return n
end

function Sim.countLogs(pattern)
    local n = 0
    for _, l in ipairs(Sim.logs) do
        if string.find(l, pattern, 1, true) then n = n + 1 end
    end
    return n
end

-- The CLI connects to both open sockets.
function Sim.connectClient()
    for _, s in ipairs(Sim.sockets) do
        if not s.closed and s.params.onConnected then s.params.onConnected(s, s.params.port) end
    end
end

-- The CLI process exits: the peer closes the connection on both open sockets.
function Sim.disconnectClient()
    for _, s in ipairs(Sim.sockets) do
        if not s.closed then
            s.closed = true
            if s.params.onClosed then s.params.onClosed(s) end
        end
    end
end
"""


class Plugin:
    def __init__(self, tmp_path: Path):
        self.port_file = tmp_path / "lightroom_ports.txt"
        rt = LuaRuntime(unpack_returned_tuples=True)
        rt.execute(SIM_LUA)
        rt.execute(f'package.path = "{PLUGIN_DIR.as_posix()}/?.lua;" .. package.path')
        rt.globals().Sim.portFile = str(self.port_file)
        rt.execute(
            """
            _G.LightroomPythonBridge = {
                initialized = true, running = true, socketServerRunning = false,
                phase3Loaded = true, phase4Loaded = false,
            }
            local bridge = _G.LightroomPythonBridge
            bridge.logger = import('LrLogger')('test')
            bridge.MessageProtocol = require('MessageProtocol')
            bridge.CommandRouter = require('CommandRouter')
            bridge.socketBridge = require('SimpleSocketBridge')
            """
        )
        self.rt = rt
        self.sim = rt.globals().Sim

    def lua(self, code: str):
        return self.rt.execute(code)

    def eval(self, expr: str):
        return self.rt.eval(expr)

    def run(self, seconds: float):
        self.sim.run(seconds)

    def start(self):
        self.lua("_G.LightroomPythonBridge.socketBridge.start()")

    def app_quit(self):
        """Lightroom loads AppShutdown.lua. Returns the shutdown table (or None)."""
        return self.eval("(dofile([[" + (PLUGIN_DIR / "AppShutdown.lua").as_posix() + "]]))")

    def plugin_shutdown(self):
        return self.eval("(dofile([[" + (PLUGIN_DIR / "PluginShutdown.lua").as_posix() + "]]))")

    def call_shutdown_function(self, table):
        """Call LrShutdownFunction the way Lightroom does; returns a list that gets True when done."""
        done = []
        self.lua("function _testDone() _testDoneCount = (_testDoneCount or 0) + 1 end")
        table["LrShutdownFunction"](self.eval("_testDone"), self.eval("function() end"))
        return done

    @property
    def done_count(self):
        return self.eval("_testDoneCount or 0")

    @property
    def running(self):
        return self.eval("_G.LightroomPythonBridge.socketServerRunning") is True

    @property
    def live_tasks(self):
        return self.sim.liveTasks()

    @property
    def open_sockets(self):
        return self.sim.openSockets()

    @property
    def errors(self):
        return list(self.sim.errors.values())

    def live_cleanup_tasks(self):
        return self.sim.countLogs("Starting request cleanup task") - self.sim.countLogs("Request cleanup task stopped")


@pytest.fixture
def plugin(tmp_path):
    return Plugin(tmp_path)


def _started(plugin: Plugin) -> Plugin:
    plugin.start()
    plugin.run(1)
    assert plugin.running
    assert plugin.open_sockets == 2
    assert plugin.port_file.exists()
    return plugin


class TestAppQuit:
    def test_quit_closes_sockets_immediately_without_scheduler(self, plugin):
        """Sockets must close as soon as AppShutdown.lua loads, even if no task ever runs again."""
        _started(plugin)
        plugin.app_quit()
        # No plugin.run(): Lightroom may stop scheduling plugin tasks while quitting.
        assert plugin.open_sockets == 0
        assert not plugin.running
        assert not plugin.port_file.exists()

    def test_shutdown_function_calls_done_and_all_tasks_end(self, plugin):
        _started(plugin)
        plugin.sim.connectClient()
        table = plugin.app_quit()
        assert table is not None and table["LrShutdownFunction"] is not None
        plugin.call_shutdown_function(table)
        plugin.run(5)
        assert plugin.done_count == 1
        assert plugin.live_tasks == 0
        assert plugin.open_sockets == 0
        assert plugin.errors == []
        assert plugin.sim.bezels == 0  # no UI while Lightroom is quitting

    def test_shutdown_function_calls_done_when_bridge_never_started(self, plugin):
        table = plugin.app_quit()
        plugin.call_shutdown_function(table)
        plugin.run(5)
        assert plugin.done_count == 1
        assert plugin.errors == []

    def test_shutdown_function_calls_done_without_bridge_global(self, plugin):
        plugin.lua("_G.LightroomPythonBridge = nil")
        table = plugin.app_quit()
        plugin.call_shutdown_function(table)
        plugin.run(5)
        assert plugin.done_count == 1
        assert plugin.errors == []

    def test_quit_before_server_task_runs(self, plugin):
        """Quit lands after start() queued the server task but before it bound the sockets."""
        plugin.start()
        plugin.app_quit()
        plugin.run(5)
        assert not plugin.running
        assert plugin.live_tasks == 0
        assert plugin.open_sockets == 0
        assert plugin.errors == []

    @pytest.mark.parametrize("offset", [round(i * 0.05, 2) for i in range(0, 15)])
    def test_quit_at_any_point_of_a_restart(self, plugin, offset):
        """The CLI disconnects after each command, which restarts the sockets. Quit during that window."""
        _started(plugin)
        plugin.sim.connectClient()
        plugin.sim.disconnectClient()  # triggers requestRestart
        plugin.run(offset)
        table = plugin.app_quit()
        plugin.call_shutdown_function(table)
        plugin.run(5)
        assert not plugin.running
        assert plugin.live_tasks == 0, f"tasks still alive after quit at +{offset}s"
        assert plugin.open_sockets == 0
        assert plugin.done_count == 1
        assert plugin.errors == []


class TestPluginShutdown:
    def test_plugin_shutdown_stops_everything(self, plugin):
        _started(plugin)
        table = plugin.plugin_shutdown()
        assert plugin.open_sockets == 0
        plugin.call_shutdown_function(table)
        plugin.run(5)
        assert plugin.done_count == 1
        assert plugin.live_tasks == 0
        assert plugin.errors == []


class TestRestarts:
    def test_restarts_do_not_accumulate_tasks(self, plugin):
        _started(plugin)
        for _ in range(20):
            plugin.sim.connectClient()
            plugin.sim.disconnectClient()
            plugin.run(1)
            assert plugin.running
        assert plugin.open_sockets == 2
        assert plugin.live_cleanup_tasks() == 1
        # keep-alive loop + cleanup task
        assert plugin.live_tasks == 2
        assert plugin.errors == []

    def test_stop_menu_then_start_again(self, plugin):
        _started(plugin)
        plugin.lua("_G.LightroomPythonBridge.socketBridge.stop()")
        assert plugin.open_sockets == 0
        plugin.run(2)
        assert plugin.live_tasks == 0
        plugin.start()
        plugin.run(1)
        assert plugin.running
        assert plugin.open_sockets == 2
        assert plugin.live_tasks == 2
        assert plugin.errors == []
