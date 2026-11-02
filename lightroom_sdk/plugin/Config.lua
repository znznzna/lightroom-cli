-- Config.lua
local LrPrefs = import 'LrPrefs'

local Config = {}

-- Default configuration values
local defaults = {
    -- Server Connection
    serverHost = "localhost",
    serverPort = 54321,         -- Server's listening port
    pluginSendPort = 54322,     -- Plugin's send socket port
    pluginReceivePort = 54323,  -- Plugin's receive socket port
    connectionTimeout = 30000,  -- 30 seconds
    reconnectDelay = 5000,      -- 5 seconds
    maxReconnectAttempts = 5,

    -- Logging
    logLevel = "debug",
    logFileMaxSize = 10485760,  -- 10MB
    logFileMaxAge = 604800,     -- 1 week in seconds

    -- Plugin Behavior
    autoStart = true,
    enableDevelopSync = true,
    enableCatalogSync = true,
    enablePreviewSync = true,

    -- Performance
    batchSize = 50,
    requestTimeout = 10000,     -- 10 seconds
}

function Config:init()
    self.prefs = LrPrefs.prefsForPlugin()

    -- Initialize defaults if not set
    for key, value in pairs(defaults) do
        if self.prefs[key] == nil then
            self.prefs[key] = value
        end
    end
end

function Config:get(key)
    -- Only a missing value falls back to the default; an explicit false must stay false
    local value = self.prefs[key]
    if value == nil then
        return defaults[key]
    end
    return value
end

function Config:set(key, value)
    self.prefs[key] = value
end

function Config:getAll()
    local config = {}
    for key, _ in pairs(defaults) do
        config[key] = self:get(key)
    end
    return config
end

return Config