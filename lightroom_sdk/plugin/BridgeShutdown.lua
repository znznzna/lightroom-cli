-- BridgeShutdown.lua
-- Shared shutdown logic for AppShutdown.lua (LrShutdownApp) and
-- PluginShutdown.lua (LrShutdownPlugin).
--
-- begin() runs immediately when Lightroom loads the shutdown script: it sets
-- the stop flags and closes the sockets directly, without sleeping. It then
-- returns the table Lightroom expects, whose LrShutdownFunction waits briefly
-- for the bridge's keep-alive loops to exit and then calls doneFunction, so
-- Lightroom always gets told the plugin is done.

local LrTasks = import 'LrTasks'

local WAIT_SECONDS = 2

local BridgeShutdown = {}

local function stopNow(reason)
    local bridge = _G.LightroomPythonBridge
    if not bridge then
        return nil
    end

    local socketBridge = bridge.socketBridge
    if socketBridge and socketBridge.stop then
        local ok, err = pcall(socketBridge.stop, { notifyClient = false, appQuitting = (reason == "app") })
        if not ok and bridge.logger then
            pcall(function() bridge.logger:error("Bridge stop failed during shutdown: " .. tostring(err)) end)
        end
    end

    -- Make sure the flags are set even if stop() was unavailable or failed
    bridge.shuttingDown = true
    bridge.socketServerRunning = false
    bridge.running = false
    if reason == "app" then
        bridge.appQuitting = true
    end
    return socketBridge
end

function BridgeShutdown.begin(reason)
    local socketBridge = stopNow(reason)

    return {
        LrShutdownFunction = function(doneFunction, progressFunction)
            local finished = false
            local function finish()
                if not finished then
                    finished = true
                    pcall(doneFunction)
                end
            end

            local ok = pcall(LrTasks.startAsyncTask, function()
                -- LrTasks.pcall (not pcall): waitForStop sleeps, and Lua 5.1
                -- cannot yield across a plain pcall.
                LrTasks.pcall(function()
                    if progressFunction then
                        progressFunction(0, "Stopping CLI Bridge...")
                    end
                    if socketBridge and socketBridge.waitForStop then
                        socketBridge.waitForStop(WAIT_SECONDS)
                    end
                    if progressFunction then
                        progressFunction(1, "CLI Bridge stopped")
                    end
                end)
                finish()
            end)
            if not ok then
                finish()
            end
        end,
    }
end

return BridgeShutdown
