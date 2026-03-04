-- AppShutdown.lua
-- Handles application shutdown cleanup
-- This file executes directly when Lightroom shuts down

local LrLogger = import 'LrLogger'
local SimpleSocketBridge = require 'SimpleSocketBridge'

-- Access global plugin state
local bridge = _G.LightroomPythonBridge

-- Create fallback logger if needed
local myLogger = LrLogger('AppShutdown')
myLogger:enable("logfile")

if bridge then
    local logger = bridge.logger or myLogger

    -- 二重実行防止
    if bridge.shuttingDown then
        logger:info("App shutdown already in progress - skipping")
        return
    end

    logger:info("Application shutdown initiated")
    bridge.shuttingDown = true  -- ソケット再起動を防止
    bridge.running = false

    -- Stop socket server if running
    if SimpleSocketBridge.isRunning() then
        logger:info("Stopping socket server on app shutdown...")
        SimpleSocketBridge.stop()
    end

    logger:info("Application shutdown complete")
else
    myLogger:warn("Plugin global state not found during app shutdown")
end