-- PluginInit.lua
-- This file executes directly when the plugin initializes
-- It sets up global state accessible via _G throughout the plugin
-- Enhanced with comprehensive error handling and robustness

local LrLogger = import 'LrLogger'
local LrTasks = import 'LrTasks'

-- Initialize global plugin state in _G
-- This makes the plugin state accessible from all modules
_G.LightroomPythonBridge = {
    initialized = false,
    running = false,
    logger = nil,
    config = nil,
    socketBridge = nil,
    socketServerRunning = false  -- Simple flag for socket server control
}

-- Load and initialize core modules
local Logger = require 'Logger'
local Config = require 'Config'
local SimpleSocketBridge = require 'SimpleSocketBridge'

-- Initialize configuration system
Config:init()

-- Initialize logging with configuration
Logger:init("LightroomPythonBridge")

-- Store references in global state
_G.LightroomPythonBridge.logger = Logger
_G.LightroomPythonBridge.config = Config
_G.LightroomPythonBridge.socketBridge = SimpleSocketBridge

-- Create built-in ErrorUtils instead of loading external module
Logger:debug("Creating built-in ErrorUtils to avoid module loading issues")
local ErrorUtils = {
    CODES = {
        MISSING_PARAM = "MISSING_PARAM",
        MISSING_PHOTO_ID = "MISSING_PHOTO_ID",
        INVALID_PARAM = "INVALID_PARAM", 
        INVALID_PARAM_TYPE = "INVALID_PARAM_TYPE",
        INVALID_PARAM_VALUE = "INVALID_PARAM_VALUE",
        PHOTO_NOT_FOUND = "PHOTO_NOT_FOUND",
        INVALID_PHOTO_TYPE = "INVALID_PHOTO_TYPE",
        PHOTO_ACCESS_DENIED = "PHOTO_ACCESS_DENIED",
        CATALOG_ACCESS_FAILED = "CATALOG_ACCESS_FAILED",
        RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE",
        OPERATION_FAILED = "OPERATION_FAILED"
    },
    
    safeCall = function(func, ...)
        return LrTasks.pcall(func, ...)
    end,
    
    createError = function(code, message, details)
        -- Map error codes to severity levels
        local severity = "error"
        if code then
            if string.find(code, "WARNING") or string.find(code, "WARN") then
                severity = "warning"
            elseif string.find(code, "INFO") then
                severity = "info"
            end
        end
        
        return {
            success = false,
            error = {
                code = code or "ERROR",
                message = message or "An error occurred",
                severity = severity,
                details = details,
                timestamp = os.time()
            }
        }
    end,
    
    createSuccess = function(result, message)
        return {
            success = true,
            result = result or {},
            message = message,
            timestamp = os.time()
        }
    end,
    
    validateRequired = function(params, requiredFields)
        if not params then
            return false, "No parameters provided"
        end
        for _, field in ipairs(requiredFields) do
            if not params[field] or params[field] == "" then
                return false, string.format("Required parameter '%s' is missing", field)
            end
        end
        return true
    end,
    
    wrapCallback = function(callback, operation)
        -- Return callback as-is to avoid recursion issues
        -- Error handling is done at higher levels
        return callback
    end
}

_G.LightroomPythonBridge.ErrorUtils = ErrorUtils
Logger:info("Built-in ErrorUtils created successfully")

-- Get configuration
local config = Config:getAll()

-- Phase 3: Load command routing modules into global state
local function loadPhase3Modules()
    Logger:info("Loading Phase 3 modules into global state")

    -- Load MessageProtocol
    local success, MessageProtocol = LrTasks.pcall(require, 'MessageProtocol')
    if success then
        _G.LightroomPythonBridge.MessageProtocol = MessageProtocol
        Logger:info("MessageProtocol loaded successfully")
    else
        Logger:error("Failed to load MessageProtocol: " .. tostring(MessageProtocol))
        return false
    end

    -- Load CommandRouter
    success, CommandRouter = LrTasks.pcall(require, 'CommandRouter')
    if success then
        _G.LightroomPythonBridge.CommandRouter = CommandRouter
        Logger:info("CommandRouter loaded successfully")
    else
        Logger:error("Failed to load CommandRouter: " .. tostring(CommandRouter))
        return false
    end

    return true
end

-- Phase 4: Load real API wrapper modules
local function loadPhase4Modules()
    Logger:info("Loading Phase 4 API wrapper modules")

    -- Load DevelopModule
    local success, DevelopModule = LrTasks.pcall(require, 'DevelopModule')
    if success then
        _G.LightroomPythonBridge.DevelopModule = DevelopModule
        Logger:info("DevelopModule loaded successfully")
    else
        Logger:error("Failed to load DevelopModule: " .. tostring(DevelopModule))
        return false
    end

    -- Load CatalogModule
    success, CatalogModule = LrTasks.pcall(require, 'CatalogModule')
    if success then
        _G.LightroomPythonBridge.CatalogModule = CatalogModule
        Logger:info("CatalogModule loaded successfully")
    else
        Logger:error("Failed to load CatalogModule: " .. tostring(CatalogModule))
        return false
    end

    -- Load PreviewModule
    success, PreviewModule = LrTasks.pcall(require, 'PreviewModule')
    if success then
        _G.LightroomPythonBridge.PreviewModule = PreviewModule
        Logger:info("PreviewModule loaded successfully")
    else
        Logger:error("Failed to load PreviewModule: " .. tostring(PreviewModule))
        return false
    end

    return true
end

-- Phase 3: Register basic system commands
local function registerSystemCommands()
    local router = _G.LightroomPythonBridge.commandRouter
    if not router then
        Logger:warn("Command router not available yet")
        return
    end

    Logger:info("Registering basic system commands")

    -- System ping command
    router:register("system.ping", function(params, callback)
        Logger:debug("Received ping command")
        callback({
            result = {
                pong = true,
                timestamp = os.time(),
                version = "1.0.0"
            }
        })
    end)

    -- System status command
    router:register("system.status", function(params, callback)
        Logger:debug("Received status command")
        callback({
            result = {
                connected = SimpleSocketBridge.isRunning(),
                stats = router:getStats(),
                uptime = os.time() - (_G.LightroomPythonBridge.startTime or os.time())
            }
        })
    end)

    Logger:info("System commands registered successfully")
end

-- Phase 4: Register API wrapper commands
local function registerApiCommands()
    local router = _G.LightroomPythonBridge.commandRouter
    Logger:info("registerApiCommands called - router available: " .. tostring(router ~= nil))
    if not router then
        Logger:warn("Command router not available yet")
        return
    end

    Logger:info("Phase 4 loaded status: " .. tostring(_G.LightroomPythonBridge.phase4Loaded))
    if not _G.LightroomPythonBridge.phase4Loaded then
        Logger:warn("Phase 4 modules not loaded, skipping API command registration")
        return
    end

    Logger:info("Phase 4: Registering API wrapper commands")

    local DevelopModule = _G.LightroomPythonBridge.DevelopModule
    local CatalogModule = _G.LightroomPythonBridge.CatalogModule
    local PreviewModule = _G.LightroomPythonBridge.PreviewModule

    Logger:info("Module availability - Develop: " .. tostring(DevelopModule ~= nil) ..
                ", Catalog: " .. tostring(CatalogModule ~= nil) ..
                ", Preview: " .. tostring(PreviewModule ~= nil))

    if not DevelopModule or not CatalogModule or not PreviewModule then
        Logger:error("One or more Phase 4 modules are nil - cannot register commands")
        return
    end

    -- Develop module commands (registered as sync for catalog API access)
    Logger:info("Registering develop commands...")
    router:register("develop.getSettings", DevelopModule.getSettings, "sync")
    router:register("develop.applySettings", DevelopModule.applySettings, "sync")
    router:register("develop.batchApplySettings", DevelopModule.batchApplySettings, "sync")
    router:register("develop.getValue", DevelopModule.getValue, "sync")
    router:register("develop.setValue", DevelopModule.setValue, "sync")
    router:register("develop.getRange", DevelopModule.getRange, "sync")
    router:register("develop.resetToDefault", DevelopModule.resetToDefault, "sync")
    router:register("develop.setAutoTone", DevelopModule.setAutoTone, "sync")
    router:register("develop.setAutoWhiteBalance", DevelopModule.setAutoWhiteBalance, "sync")
    router:register("develop.getProcessVersion", DevelopModule.getProcessVersion, "sync")
    router:register("develop.setProcessVersion", DevelopModule.setProcessVersion, "sync")
    router:register("develop.resetAllDevelopAdjustments", DevelopModule.resetAllDevelopAdjustments, "sync")
    
    -- ToneCurve manipulation commands
    router:register("develop.getCurvePoints", DevelopModule.getCurvePoints, "sync")
    router:register("develop.setCurvePoints", DevelopModule.setCurvePoints, "sync")
    router:register("develop.setCurveLinear", DevelopModule.setCurveLinear, "sync")
    router:register("develop.setCurveSCurve", DevelopModule.setCurveSCurve, "sync")
    router:register("develop.addCurvePoint", DevelopModule.addCurvePoint, "sync")
    router:register("develop.removeCurvePoint", DevelopModule.removeCurvePoint, "sync")
    
    -- PointColors helper APIs
    router:register("develop.createGreenSwatch", DevelopModule.createGreenSwatch, "sync")
    router:register("develop.createCyanSwatch", DevelopModule.createCyanSwatch, "sync")
    router:register("develop.enhanceColors", DevelopModule.enhanceColors, "sync")
    
    -- Masking navigation and state commands
    router:register("develop.goToMasking", DevelopModule.goToMasking, "sync")
    router:register("develop.toggleOverlay", DevelopModule.toggleOverlay, "sync")
    router:register("develop.selectTool", DevelopModule.selectTool, "sync")
    
    -- Mask management commands
    router:register("develop.getAllMasks", DevelopModule.getAllMasks, "sync")
    router:register("develop.getSelectedMask", DevelopModule.getSelectedMask, "sync")
    router:register("develop.createNewMask", DevelopModule.createNewMask, "sync")
    router:register("develop.selectMask", DevelopModule.selectMask, "sync")
    router:register("develop.deleteMask", DevelopModule.deleteMask, "sync")
    
    -- Mask tool management commands
    router:register("develop.getSelectedMaskTool", DevelopModule.getSelectedMaskTool, "sync")
    router:register("develop.selectMaskTool", DevelopModule.selectMaskTool, "sync")
    router:register("develop.deleteMaskTool", DevelopModule.deleteMaskTool, "sync")
    
    -- Mask operations and boolean logic commands
    router:register("develop.addToCurrentMask", DevelopModule.addToCurrentMask, "sync")
    router:register("develop.intersectWithCurrentMask", DevelopModule.intersectWithCurrentMask, "sync")
    router:register("develop.subtractFromCurrentMask", DevelopModule.subtractFromCurrentMask, "sync")
    router:register("develop.invertMask", DevelopModule.invertMask, "sync")
    
    -- Legacy tool reset commands (for backward compatibility)
    router:register("develop.resetGradient", DevelopModule.resetGradient, "sync")
    router:register("develop.resetCircularGradient", DevelopModule.resetCircularGradient, "sync")
    router:register("develop.resetBrushing", DevelopModule.resetBrushing, "sync")
    router:register("develop.resetMasking", DevelopModule.resetMasking, "sync")
    
    -- Helper functions for common masking workflows
    router:register("develop.createGraduatedFilter", DevelopModule.createGraduatedFilter, "sync")
    router:register("develop.createRadialFilter", DevelopModule.createRadialFilter, "sync")
    router:register("develop.createAdjustmentBrush", DevelopModule.createAdjustmentBrush, "sync")
    router:register("develop.createAISelectionMask", DevelopModule.createAISelectionMask, "sync")
    router:register("develop.createRangeMask", DevelopModule.createRangeMask, "sync")
    router:register("develop.createComplexMask", DevelopModule.createComplexMask, "sync")
    
    -- Local adjustment parameter functions
    router:register("develop.activateMaskingMode", DevelopModule.activateMaskingMode, "sync")
    router:register("develop.getLocalValue", DevelopModule.getLocalValue, "sync")
    router:register("develop.setLocalValue", DevelopModule.setLocalValue, "sync")
    router:register("develop.applyLocalSettings", DevelopModule.applyLocalSettings, "sync")
    router:register("develop.getAvailableLocalParameters", DevelopModule.getAvailableLocalParameters, "sync")
    router:register("develop.createMaskWithLocalAdjustments", DevelopModule.createMaskWithLocalAdjustments, "sync")
    
    -- Reverse engineering / introspection functions
    router:register("develop.dumpLrDevelopController", DevelopModule.dumpLrDevelopController, "sync")
    router:register("develop.discoverGradientParameters", DevelopModule.discoverGradientParameters, "sync")
    router:register("develop.monitorParameterChanges", DevelopModule.monitorParameterChanges, "sync")
    router:register("develop.probeAllDevelopParameters", DevelopModule.probeAllDevelopParameters, "sync")

    -- Catalog module commands (registered as sync for catalog API access)
    Logger:info("Registering catalog commands...")
    router:register("catalog.searchPhotos", CatalogModule.searchPhotos, "sync")
    router:register("catalog.getPhotoMetadata", CatalogModule.getPhotoMetadata, "sync")
    router:register("catalog.getSelectedPhotos", CatalogModule.getSelectedPhotos, "sync")
    router:register("catalog.setSelectedPhotos", CatalogModule.setSelectedPhotos, "sync")
    router:register("catalog.getAllPhotos", CatalogModule.getAllPhotos, "sync")
    router:register("catalog.findPhotoByPath", CatalogModule.findPhotoByPath, "sync")
    router:register("catalog.findPhotos", CatalogModule.findPhotos, "sync")
    router:register("catalog.getCollections", CatalogModule.getCollections, "sync")
    router:register("catalog.getKeywords", CatalogModule.getKeywords, "sync")
    router:register("catalog.getFolders", CatalogModule.getFolders, "sync")
    router:register("catalog.batchGetFormattedMetadata", CatalogModule.batchGetFormattedMetadata, "sync")

    -- Preview module commands (registered as sync for catalog API access)
    Logger:info("Registering preview commands...")
    router:register("preview.generatePreview", PreviewModule.generatePreview, "sync")
    router:register("preview.generateBatchPreviews", PreviewModule.generateBatchPreviews, "sync")
    router:register("preview.getPreviewInfo", PreviewModule.getPreviewInfo, "sync")
    router:register("preview.getPreviewChunk", PreviewModule.getPreviewChunk, "sync")

    Logger:info("Phase 4: API wrapper commands registered successfully")
end

-- Phase 4: Set up real-time develop change monitoring
local function setupDevelopSync()
    local router = _G.LightroomPythonBridge.commandRouter
    local DevelopModule = _G.LightroomPythonBridge.DevelopModule

    if not router or not DevelopModule then
        Logger:warn("Cannot setup develop sync - router or DevelopModule not available")
        return
    end

    local config = _G.LightroomPythonBridge.config
    if not config:get('enableDevelopSync') then
        Logger:info("Real-time develop sync disabled in configuration")
        return
    end

    Logger:info("Setting up real-time develop sync")

    -- Check if watchChanges is available
    if not DevelopModule.watchChanges then
        Logger:warn("DevelopModule.watchChanges not available - skipping develop sync")
        return
    end

    local unsubscribe = DevelopModule.watchChanges(function(photo, changes)
        if photo and changes then
            router:sendEvent("develop.changed", {
                photoId = photo:getFormattedMetadata("uuid"),
                changes = changes,
                filename = photo:getFormattedMetadata("fileName")
            })
        elseif photo then
            -- Photo change event
            router:sendEvent("photo.changed", {
                photoId = photo:getFormattedMetadata("uuid"),
                filename = photo:getFormattedMetadata("fileName")
            })
        end
    end)

    -- Store unsubscribe function for cleanup
    _G.LightroomPythonBridge.developChangeUnsubscribe = unsubscribe
    Logger:info("Real-time develop sync enabled")
end

-- Load Phase 3 modules
_G.LightroomPythonBridge.phase3Loaded = loadPhase3Modules()

-- Load Phase 4 modules
_G.LightroomPythonBridge.phase4Loaded = loadPhase4Modules()

-- Store functions for use after socket bridge starts
_G.LightroomPythonBridge.registerSystemCommands = registerSystemCommands
_G.LightroomPythonBridge.registerApiCommands = registerApiCommands
_G.LightroomPythonBridge.setupDevelopSync = setupDevelopSync
_G.LightroomPythonBridge.startTime = os.time()

-- Mark as initialized
_G.LightroomPythonBridge.initialized = true
_G.LightroomPythonBridge.running = true

if _G.LightroomPythonBridge.phase3Loaded and _G.LightroomPythonBridge.phase4Loaded then
    Logger:info("Plugin initialized via LrInitPlugin with Phase 3+4 (Full API support)")
elseif _G.LightroomPythonBridge.phase3Loaded then
    Logger:info("Plugin initialized via LrInitPlugin with Phase 3 command routing (Phase 4 failed)")
else
    Logger:error("Plugin initialization failed - Phase 3 modules could not be loaded")
end
Logger:debug("Configuration loaded: serverHost=" .. config.serverHost .. ", pluginSendPort=" .. config.pluginSendPort .. ", pluginReceivePort=" .. config.pluginReceivePort)

-- Auto-start connection if configured
if config.autoStart then
    Logger:info("Auto-start enabled - will connect to server when menu action is triggered")
    -- Note: Actual connection happens in MenuActions.lua to ensure proper context
end