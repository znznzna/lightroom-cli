-- MenuActions.lua
-- Handles "Start Python Bridge" menu action

local LrLogger = import 'LrLogger'
local LrDialogs = import 'LrDialogs'
local SimpleSocketBridge = require 'SimpleSocketBridge'

-- Access global plugin state
local bridge = _G.LightroomPythonBridge

-- Create logger directly for menu action
local myLogger = LrLogger('MenuActions')
myLogger:enable("logfile")

-- This code executes when the menu item is selected
myLogger:info("Start Python Bridge menu item selected")

-- Check if plugin is initialized
if not bridge or not bridge.initialized then
    LrDialogs.message("Python Bridge", "Plugin not properly initialized. Please restart Lightroom.", "critical")
    return
end

-- Use global logger if available
local logger = bridge.logger or myLogger

-- Check if socket server is already running
if SimpleSocketBridge.isRunning() then
    logger:info("Socket server already running")
    LrDialogs.message("Python Bridge", "Bridge is already running. Use Stop to disconnect first.", "info")
    return
end

if bridge.phase4Loaded then
    logger:info("Starting Python Bridge with full Phase 4 API support")
else
    logger:info("Starting Python Bridge with Phase 3 command routing (Phase 4 unavailable)")
end

-- Start the enhanced socket server (follows Adobe pattern with command routing)
SimpleSocketBridge.start()

-- Phase 3+4: Register commands after socket bridge starts
local LrTasks = import 'LrTasks'
LrTasks.startAsyncTask(function()
    -- Wait a moment for socket bridge to initialize command router
    LrTasks.sleep(1)

    logger:info("Attempting to register commands...")

    -- Register Phase 3 system commands
    if bridge.registerSystemCommands then
        bridge.registerSystemCommands()
        logger:info("System command registration completed")
    else
        logger:warn("System command registration function not available")
    end

    -- Register Phase 4 API commands
    if bridge.registerApiCommands and bridge.phase4Loaded then
        bridge.registerApiCommands()
        logger:info("API command registration completed")
    else
        logger:warn("API command registration function not available or Phase 4 not loaded")
    end

    -- Set up Phase 4 real-time develop sync
    if bridge.setupDevelopSync and bridge.phase4Loaded then
        -- bridge.setupDevelopSync()
        logger:info("Develop sync setup completed")
    else
        logger:warn("Develop sync setup function not available or Phase 4 not loaded")
    end
end)

logger:info("Socket server started with command routing - check logs for connection details")
LrDialogs.showBezel("Python Bridge Started", 2)