-- CommandRouter.lua
-- Dynamic command registration and dispatch system for Phase 3

local MessageProtocol = nil  -- Lazy load to avoid circular dependency
local LrTasks = import 'LrTasks'

-- Lazy load MessageProtocol
local function ensureMessageProtocol()
    -- Try global state first (loaded in PluginInit.lua)
    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.MessageProtocol then
        return _G.LightroomPythonBridge.MessageProtocol
    end
    
    -- Fall back to require
    if not MessageProtocol then
        MessageProtocol = require 'MessageProtocol'
    end
    return MessageProtocol
end

-- Get logger from global state (defensive)
local function getLogger()
    local LrLogger = import 'LrLogger'
    local logger = LrLogger('CommandRouter')
    logger:enable("logfile")
    
    -- Try to use global logger if available
    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.logger then
        return _G.LightroomPythonBridge.logger
    end
    
    return logger
end

local CommandRouter = {}

function CommandRouter:init()
    self.handlers = {}
    self.handlerModes = {}  -- Track execution mode for each handler
    self.pendingRequests = {}
    self.eventSubscribers = {}
    self.socketBridge = nil  -- Will be set during integration
    
    local logger = getLogger()
    logger:info("CommandRouter initialized")
end

-- Set socket bridge reference for sending messages
function CommandRouter:setSocketBridge(socketBridge)
    self.socketBridge = socketBridge
    local logger = getLogger()
    logger:debug("CommandRouter connected to SocketBridge")
end

-- Register a command handler with execution mode
-- mode: "sync" for catalog API handlers, "async" for network/file operations (default)
function CommandRouter:register(command, handler, mode)
    local logger = getLogger()
    
    if type(command) ~= "string" then
        logger:error("CommandRouter:register - command must be a string")
        return false
    end
    
    if type(handler) ~= "function" then
        logger:error("CommandRouter:register - handler must be a function")
        return false
    end
    
    -- Default to async mode for backward compatibility
    mode = mode or "async"
    if mode ~= "sync" and mode ~= "async" then
        logger:error("CommandRouter:register - mode must be 'sync' or 'async'")
        return false
    end
    
    self.handlers[command] = handler
    self.handlerModes[command] = mode
    logger:info("Registered " .. mode .. " handler for command: " .. command)
    return true
end

-- Unregister a command handler
function CommandRouter:unregister(command)
    local logger = getLogger()
    
    if self.handlers[command] then
        self.handlers[command] = nil
        self.handlerModes[command] = nil
        logger:info("Unregistered handler for command: " .. command)
        return true
    end
    return false
end

-- Dispatch incoming message to appropriate handler
function CommandRouter:dispatch(message)
    local logger = getLogger()
    
    if not message then
        logger:error("CommandRouter:dispatch - message is nil")
        return
    end
    
    logger:info("TRACE: CommandRouter:dispatch - Received message type: " .. 
        (message.command and "command:" .. message.command or 
         message.event and "event:" .. message.event or 
         (message.id and message.success ~= nil) and "response" or "unknown"))
    
    -- Handle different message types
    if message.command then
        logger:info("TRACE: CommandRouter:dispatch - Dispatching command: " .. message.command .. " with ID: " .. tostring(message.id))
        self:_dispatchCommand(message)
    elseif message.event then
        self:_dispatchEvent(message)
    elseif message.id and message.success ~= nil then
        self:_dispatchResponse(message)
    else
        logger:error("CommandRouter:dispatch - unknown message type")
    end
end

-- Dispatch command to handler
function CommandRouter:_dispatchCommand(message)
    local logger = getLogger()
    local protocol = ensureMessageProtocol()
    
    -- Validate request format
    local valid, error = protocol:validateRequest(message)
    if not valid then
        logger:error("Invalid request format: " .. error)
        self:_sendErrorResponse(message.id, "INVALID_REQUEST", error)
        return
    end
    
    local command = message.command
    local handler = self.handlers[command]
    local mode = self.handlerModes[command] or "async"
    
    if not handler then
        logger:warn("No handler registered for command: " .. command)
        self:_sendErrorResponse(message.id, "UNKNOWN_COMMAND", "No handler for: " .. command)
        return
    end
    
    logger:debug("Dispatching " .. mode .. " command: " .. command)
    
    -- Debug: Check what's in message.params
    logger:debug("CommandRouter message.params type: " .. type(message.params))
    if message.params then
        local count = 0
        for k, v in pairs(message.params) do
            logger:debug("  message.params[" .. tostring(k) .. "] = " .. tostring(v))
            count = count + 1
        end
        logger:debug("CommandRouter message.params count: " .. count)
    else
        logger:error("CommandRouter message.params is nil!")
    end
    
    -- All handlers execute in async task context (required for withReadAccessDo)
    self:_executeHandler(handler, message)
end

-- Execute handler in async task context (required for withReadAccessDo)
function CommandRouter:_executeHandler(handler, message)
    local logger = getLogger()
    
    LrTasks.startAsyncTask(function()
        logger:info("TRACE: CommandRouter - About to call handler for: " .. message.command)
        
        local success, result = LrTasks.pcall(handler, message.params, function(response)
            logger:info("TRACE: CommandRouter - Handler callback invoked for: " .. message.command)
            logger:info("TRACE: CommandRouter - Response type: " .. type(response))
            if response and response.error then
                logger:info("TRACE: CommandRouter - Response contains error: " .. (response.error.code or "unknown"))
            end
            self:_sendResponse(message.id, response)
        end)
        
        if not success then
            logger:error("Handler error for " .. message.command .. ": " .. tostring(result))
            self:_sendErrorResponse(message.id, "HANDLER_ERROR", tostring(result))
        else
            logger:info("TRACE: CommandRouter - Handler completed successfully for: " .. message.command)
        end
    end)
end

-- Send command to remote server
function CommandRouter:sendCommand(command, params, callback)
    local logger = getLogger()
    local protocol = ensureMessageProtocol()
    local request = protocol:createRequest(command, params)
    
    -- Store callback for response correlation
    if callback then
        self.pendingRequests[request.id] = {
            callback = callback,
            timestamp = os.time(),
            command = command
        }
    end
    
    -- Send via socket bridge
    local encoded = protocol:encode(request)
    if encoded and self.socketBridge then
        local success = self.socketBridge.send(encoded)
        if success then
            logger:debug("Sent command: " .. command .. " (ID: " .. request.id .. ")")
            return request.id
        else
            logger:error("Failed to send command via socket: " .. command)
            -- Remove from pending if send failed
            if callback then
                self.pendingRequests[request.id] = nil
            end
            return nil
        end
    else
        logger:error("Failed to encode command or no socket bridge: " .. command)
        return nil
    end
end

-- Handle response from remote server
function CommandRouter:_dispatchResponse(message)
    local logger = getLogger()
    local protocol = ensureMessageProtocol()
    
    local valid, error = protocol:validateResponse(message)
    if not valid then
        logger:error("Invalid response format: " .. error)
        return
    end
    
    local requestId = message.id
    local pendingRequest = self.pendingRequests[requestId]
    
    if not pendingRequest then
        logger:warn("Received response for unknown request ID: " .. requestId)
        return
    end
    
    -- Remove from pending requests
    self.pendingRequests[requestId] = nil
    
    logger:debug("Received response for command: " .. pendingRequest.command)
    
    -- Execute callback
    if pendingRequest.callback then
        LrTasks.startAsyncTask(function()
            local success, result = pcall(pendingRequest.callback, message)
            if not success then
                logger:error("Response callback error: " .. tostring(result))
            end
        end)
    end
end

-- Send response to command
function CommandRouter:_sendResponse(requestId, response)
    local logger = getLogger()
    logger:info("TRACE: CommandRouter:_sendResponse - START for requestId: " .. tostring(requestId))
    
    local protocol = ensureMessageProtocol()
    local message
    
    if response.error then
        logger:info("TRACE: CommandRouter:_sendResponse - Creating error response")
        message = protocol:createResponse(requestId, false, nil, response.error)
    else
        logger:info("TRACE: CommandRouter:_sendResponse - Creating success response")
        message = protocol:createResponse(requestId, true, response.result or response, nil)
    end
    
    logger:info("TRACE: CommandRouter:_sendResponse - About to encode message")
    local encoded = protocol:encode(message)
    logger:info("TRACE: CommandRouter:_sendResponse - Message encoded successfully")
    logger:debug("CommandRouter:_sendResponse - encoded type: " .. type(encoded))
    logger:debug("CommandRouter:_sendResponse - encoded length: " .. string.len(encoded or ""))
    -- Check if rating is in the encoded JSON
    if encoded and string.find(encoded, "rating") then
        logger:debug("CommandRouter:_sendResponse - rating field found in JSON")
    else
        logger:debug("CommandRouter:_sendResponse - rating field NOT found in JSON")
    end
    
    if encoded and self.socketBridge then
        logger:debug("CommandRouter:_sendResponse - self.socketBridge type: " .. type(self.socketBridge))
        logger:debug("CommandRouter:_sendResponse - self.socketBridge.send type: " .. type(self.socketBridge.send))
        logger:debug("CommandRouter:_sendResponse - about to call socketBridge:send with type: " .. type(encoded))
        logger:info("TRACE: CommandRouter:_sendResponse - About to send via socket")
        local success = self.socketBridge.send(encoded)
        if success then
            logger:info("TRACE: CommandRouter:_sendResponse - Socket send SUCCESS for request: " .. requestId)
        else
            logger:error("TRACE: CommandRouter:_sendResponse - Socket send FAILED for request: " .. requestId)
        end
    else
        logger:error("Failed to encode response for request: " .. requestId)
    end
end

-- Send error response
function CommandRouter:_sendErrorResponse(requestId, errorCode, errorMessage)
    local logger = getLogger()
    local protocol = ensureMessageProtocol()
    
    local errorObj = {
        code = errorCode,
        message = errorMessage,
        severity = "error",
        details = {}
    }
    
    local message = protocol:createResponse(requestId, false, nil, errorObj)
    local encoded = protocol:encode(message)
    
    if encoded and self.socketBridge then
        local success = self.socketBridge.send(encoded)
        if success then
            logger:debug("Sent error response: " .. errorCode)
        else
            logger:error("Failed to send error response via socket")
        end
    else
        logger:error("Failed to encode error response")
    end
end

-- Event handling
function CommandRouter:_dispatchEvent(message)
    local logger = getLogger()
    local protocol = ensureMessageProtocol()
    
    local valid, error = protocol:validateEvent(message)
    if not valid then
        logger:error("Invalid event format: " .. error)
        return
    end
    
    local eventType = message.event
    local subscribers = self.eventSubscribers[eventType] or {}
    
    logger:debug("Dispatching event: " .. eventType .. " to " .. #subscribers .. " subscribers")
    
    for _, subscriber in ipairs(subscribers) do
        LrTasks.startAsyncTask(function()
            local success, result = pcall(subscriber, message.data)
            if not success then
                logger:error("Event subscriber error: " .. tostring(result))
            end
        end)
    end
end

-- Subscribe to events
function CommandRouter:subscribe(eventType, callback)
    local logger = getLogger()
    
    if not self.eventSubscribers[eventType] then
        self.eventSubscribers[eventType] = {}
    end
    
    table.insert(self.eventSubscribers[eventType], callback)
    logger:debug("Subscribed to event: " .. eventType)
    
    -- Return unsubscribe function
    return function()
        local subscribers = self.eventSubscribers[eventType]
        if subscribers then
            for i, subscriber in ipairs(subscribers) do
                if subscriber == callback then
                    table.remove(subscribers, i)
                    logger:debug("Unsubscribed from event: " .. eventType)
                    break
                end
            end
        end
    end
end

-- Send event notification
function CommandRouter:sendEvent(eventType, data)
    local logger = getLogger()
    local protocol = ensureMessageProtocol()
    local event = protocol:createEvent(eventType, data)
    local encoded = protocol:encode(event)
    logger:debug("CommandRouter:sendEvent - encoded type: " .. type(encoded))
    logger:debug("CommandRouter:sendEvent - encoded value: " .. tostring(encoded))
    
    if encoded and self.socketBridge then
        logger:debug("CommandRouter:sendEvent - self.socketBridge type: " .. type(self.socketBridge))
        logger:debug("CommandRouter:sendEvent - self.socketBridge.send type: " .. type(self.socketBridge.send))
        logger:debug("CommandRouter:sendEvent - about to call socketBridge:send with type: " .. type(encoded))
        local success = self.socketBridge.send(encoded)
        if success then
            logger:debug("Sent event: " .. eventType)
            return true
        else
            logger:error("Failed to send event via socket: " .. eventType)
            return false
        end
    else
        logger:error("Failed to encode event: " .. eventType)
        return false
    end
end

-- Cleanup expired requests
function CommandRouter:_cleanupExpiredRequests()
    local logger = getLogger()
    local currentTime = os.time()
    local timeout = 30  -- 30 seconds timeout
    
    for requestId, request in pairs(self.pendingRequests) do
        if currentTime - request.timestamp > timeout then
            logger:warn("Request timed out: " .. request.command .. " (ID: " .. requestId .. ")")
            
            -- Call callback with timeout error
            if request.callback then
                local protocol = ensureMessageProtocol()
                local timeoutResponse = protocol:createResponse(requestId, false, nil, {
                    code = "TIMEOUT",
                    message = "Request timed out after " .. timeout .. " seconds"
                })
                
                LrTasks.startAsyncTask(function()
                    pcall(request.callback, timeoutResponse)
                end)
            end
            
            self.pendingRequests[requestId] = nil
        end
    end
end

-- Get statistics
function CommandRouter:getStats()
    local handlerCount = 0
    local pendingCount = 0
    local subscriberCount = 0
    
    -- Count handlers
    for _ in pairs(self.handlers) do
        handlerCount = handlerCount + 1
    end
    
    -- Count pending requests
    for _ in pairs(self.pendingRequests) do
        pendingCount = pendingCount + 1
    end
    
    -- Count event subscribers
    for _ in pairs(self.eventSubscribers) do
        subscriberCount = subscriberCount + 1
    end
    
    return {
        registeredHandlers = handlerCount,
        pendingRequests = pendingCount,
        eventSubscriberTypes = subscriberCount
    }
end

-- Start periodic cleanup task
function CommandRouter:startCleanupTask()
    local logger = getLogger()
    logger:info("Starting request cleanup task")

    LrTasks.startAsyncTask(function()
        while _G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning do
            self:_cleanupExpiredRequests()
            -- Sleep in small increments for faster shutdown response
            -- 20 x 0.5s = 10 seconds total, but can exit within 500ms during shutdown
            for i = 1, 20 do
                if not (_G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning) then
                    break
                end
                LrTasks.sleep(0.5)
            end
        end
        logger:info("Request cleanup task stopped")
    end)
end

return CommandRouter