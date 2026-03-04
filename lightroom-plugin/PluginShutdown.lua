-- PluginShutdown.lua
-- Handles plugin shutdown when plugin is disabled
-- This file executes directly when shutdown occurs

local LrLogger = import 'LrLogger'
local SimpleSocketBridge = require 'SimpleSocketBridge'

-- Access global plugin state
local bridge = _G.LightroomPythonBridge

-- Create fallback logger if needed
local myLogger = LrLogger('PluginShutdown')
myLogger:enable("logfile")

if bridge then
    local logger = bridge.logger or myLogger

    -- 二重実行防止
    if bridge.shuttingDown then
        logger:info("Plugin shutdown already in progress - skipping")
        return
    end

    logger:info("Plugin shutdown initiated")
    bridge.shuttingDown = true  -- ソケット再起動を防止
    bridge.running = false

    -- Stop socket server if running
    if SimpleSocketBridge.isRunning() then
        logger:info("Stopping socket server...")
        SimpleSocketBridge.stop()
    end

    logger:info("Plugin shutdown complete")
else
    myLogger:warn("Plugin global state not found during shutdown")
end