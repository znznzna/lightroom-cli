-- SimpleSocketBridge.lua
-- Enhanced socket bridge with Phase 3 JSON protocol and command routing

local LrSocket = import 'LrSocket'
local LrTasks = import 'LrTasks'
local LrFunctionContext = import 'LrFunctionContext'
local LrDialogs = import 'LrDialogs'

-- Module-level variables for Phase 3
local commandRouter = nil
local senderSocket = nil
local globalSender = nil  -- Store sender socket reference
local bothSocketsReady = false  -- Track when both sockets are connected
local messageQueue = {}  -- Queue messages until both sockets ready
local isRestarting = false  -- Flag to prevent multiple concurrent restarts

-- Get Phase 3 modules from global state (loaded in PluginInit.lua)
local function getPhase3Modules()
    local bridge = _G.LightroomPythonBridge
    if not bridge or not bridge.phase3Loaded then
        return nil, nil
    end
    return bridge.MessageProtocol, bridge.CommandRouter
end

-- Get logger from global state
local function getLogger()
    local bridge = _G.LightroomPythonBridge
    if bridge and bridge.logger then
        return bridge.logger
    end
    local LrLogger = import 'LrLogger'
    local logger = LrLogger('SimpleSocketBridge')
    logger:enable("logfile")
    return logger
end

-- Forward declaration for restart function (defined after startSocketServer)
local restartSocketServer

-- Process queued messages when both sockets are ready
local function processQueuedMessages()
    local logger = getLogger()

    if #messageQueue > 0 then
        logger:info("Processing " .. #messageQueue .. " queued messages")

        local MessageProtocol, _ = getPhase3Modules()
        if MessageProtocol and commandRouter then
            for _, message in ipairs(messageQueue) do
                local decoded = MessageProtocol:decode(tostring(message))
                if decoded then
                    logger:debug("Processing queued message: " .. (decoded.command or "unknown"))
                    commandRouter:dispatch(decoded)
                else
                    logger:error("Failed to decode queued message: " .. tostring(message))
                end
            end
        end

        -- Clear the queue
        messageQueue = {}
        logger:info("Message queue processed and cleared")
    end
end

-- Write port info for Python client
local function writePortFile(senderPort, receiverPort)
    local logger = getLogger()
    local success, err = LrTasks.pcall(function()
        local file = io.open("/tmp/lightroom_ports.txt", "w")
        if file then
            file:write(string.format("%d,%d", senderPort, receiverPort))
            file:close()
            logger:info("Port file written: send=" .. senderPort .. ", receive=" .. receiverPort)
        else
            logger:error("Failed to create port file")
        end
    end)

    if not success then
        logger:error("Error writing port file: " .. tostring(err))
    end
end

-- Enhanced socket server with Phase 3 command routing
local function startSocketServer()
    local logger = getLogger()

    logger:info("Starting enhanced socket server with Phase 3 command routing")

    -- Phase 3: Get modules from global state and initialize command router
    local MessageProtocol, CommandRouter = getPhase3Modules()
    if CommandRouter then
        commandRouter = CommandRouter
        commandRouter:init()
        _G.LightroomPythonBridge.commandRouter = commandRouter
        logger:info("Phase 3 command router initialized")
        
        -- Register commands on router initialization/restart
        local bridge = _G.LightroomPythonBridge
        if bridge then
            if bridge.registerSystemCommands then
                logger:info("Registering system commands on restart")
                bridge.registerSystemCommands()
            end
            
            if bridge.registerApiCommands and bridge.phase4Loaded then
                logger:info("Registering API commands on restart")
                bridge.registerApiCommands()
            end
        end
    else
        logger:error("Phase 3 modules not available - falling back to basic mode")
    end

    -- Use the exact same pattern as Adobe's working sample
    LrTasks.startAsyncTask(function()

        LrFunctionContext.callWithContext('lightroom_python_bridge', function(context)
            logger:info("Socket context created")

            local senderPort, receiverPort
            local sender, receiver

            -- Create sender socket (Python connects to send TO Lightroom)
            sender = LrSocket.bind {
                functionContext = context,
                address = "localhost",
                port = 0,  -- AUTO_PORT - let OS assign
                mode = "send",
                plugin = _PLUGIN,

                onConnecting = function(socket, port)
                    logger:info("Sender socket listening on port " .. port)
                    senderPort = port

                    -- Write port file when both ports are available
                    if senderPort and receiverPort then
                        writePortFile(senderPort, receiverPort)
                    end
                end,

                onConnected = function(socket, port)
                    logger:info("Python connected to sender socket")

                    -- Phase 3: Store socket and connect command router
                    senderSocket = socket
                    globalSender = socket  -- Store the connected socket object

                    if commandRouter then
                        commandRouter:setSocketBridge({
                            send = function(jsonData)
                                if globalSender and jsonData then
                                    logger:debug("Send function received jsonData type: " .. type(jsonData))
                                    -- Truncate large messages for logging (like base64 image data)
                                    local logMessage = tostring(jsonData)
                                    if string.len(logMessage) > 500 then
                                        logMessage = string.sub(logMessage, 1, 200) .. "... [" .. string.len(logMessage) .. " chars total] ..." .. string.sub(logMessage, -100)
                                    end
                                    logger:debug("Send function received jsonData value: " .. logMessage)

                                    -- Ensure jsonData is a string
                                    if type(jsonData) ~= "string" then
                                        logger:error("ERROR: jsonData is not a string! Type: " .. type(jsonData))
                                        return false
                                    end

                                    -- Ensure jsonData ends with newline for socket protocol
                                    if not string.match(jsonData, "\n$") then
                                        jsonData = jsonData .. "\n"
                                    end
                                    -- Truncate large messages for logging (like base64 image data)
                                    local logData = jsonData
                                    if string.len(logData) > 500 then
                                        logData = string.sub(logData, 1, 200) .. "... [" .. string.len(logData) .. " chars total] ..." .. string.sub(logData, -100)
                                    end
                                    logger:debug("Sending JSON string via socket: " .. logData)
                                    globalSender:send(jsonData)
                                    return true
                                else
                                    logger:error("Cannot send - socket or jsonData is nil")
                                    return false
                                end
                            end
                        })

                        -- Mark both sockets as ready and process queued messages
                        bothSocketsReady = true
                        logger:info("Both sockets now ready - processing any queued messages")
                        processQueuedMessages()

                        -- Send connection established event
                        commandRouter:sendEvent("connection.established", {
                            senderPort = senderPort,
                            receiverPort = receiverPort
                        })
                    end
                end,

                onClosed = function(socket)
                    logger:info("Sender socket closed - client disconnected")
                    local bridge = _G.LightroomPythonBridge
                    if bridge and bridge.shuttingDown then
                        logger:info("shuttingDown=true, not restarting")
                        return
                    end
                    if bridge and bridge.socketServerRunning then
                        restartSocketServer()
                    else
                        logger:info("Socket closed during shutdown - not restarting")
                    end
                end,

                onError = function(socket, err)
                    logger:error("Sender socket error: " .. err)
                    local bridge = _G.LightroomPythonBridge
                    if bridge and bridge.shuttingDown then
                        logger:info("shuttingDown=true, not reconnecting")
                        return
                    end
                    if err == "timeout" and bridge and bridge.socketServerRunning then
                        logger:info("Attempting sender socket reconnect")
                        socket:reconnect()
                    else
                        logger:info("Sender socket error during shutdown - not reconnecting")
                    end
                end
            }

            -- Create receiver socket (Python connects to receive FROM Lightroom)
            receiver = LrSocket.bind {
                functionContext = context,
                address = "localhost",
                port = 0,  -- AUTO_PORT - let OS assign
                mode = "receive",
                plugin = _PLUGIN,

                onConnecting = function(socket, port)
                    logger:info("Receiver socket listening on port " .. port)
                    receiverPort = port

                    -- Write port file when both ports are available
                    if senderPort and receiverPort then
                        writePortFile(senderPort, receiverPort)
                    end
                end,

                onConnected = function(socket, port)
                    logger:info("Python connected to receiver socket")
                    logger:info("Receiver socket ready to receive messages")
                end,

                onMessage = function(socket, message)
                    logger:info("\n\n")
                    logger:info("*** JSON MESSAGE RECEIVED ***")
                    logger:debug("Raw message: " .. tostring(message))

                    -- Check if both sockets are ready before processing
                    if not bothSocketsReady then
                        logger:warn("Both sockets not ready yet - queuing message")
                        table.insert(messageQueue, message)
                        return
                    end

                    -- Phase 3: Decode JSON and dispatch to command router
                    local MessageProtocol, _ = getPhase3Modules()
                    if MessageProtocol and commandRouter then
                        local decoded = MessageProtocol:decode(tostring(message))
                        if decoded then
                            logger:debug("Decoded JSON message - dispatching to command router")
                            commandRouter:dispatch(decoded)
                        else
                            logger:error("Failed to decode JSON message: " .. tostring(message))
                        end
                    else
                        logger:warn("Phase 3 not available - ignoring message")
                    end
                end,

                onClosed = function(socket)
                    logger:info("*** RECEIVER SOCKET CLOSED - CLIENT DISCONNECTED ***")
                    local bridge = _G.LightroomPythonBridge
                    if bridge and bridge.shuttingDown then
                        logger:info("shuttingDown=true, not restarting receiver")
                        return
                    end
                    if bridge and bridge.socketServerRunning then
                        restartSocketServer()
                    else
                        logger:info("Receiver socket closed during shutdown - not restarting")
                    end
                end,

                onError = function(socket, err)
                    logger:error("*** RECEIVER SOCKET ERROR: " .. err)
                    local bridge = _G.LightroomPythonBridge
                    if bridge and bridge.shuttingDown then
                        logger:info("shuttingDown=true, not reconnecting receiver")
                        return
                    end
                    if err == "timeout" and bridge and bridge.socketServerRunning then
                        logger:info("Receiver socket timeout - attempting reconnect")
                        socket:reconnect()
                    else
                        logger:info("Receiver socket error during shutdown - not reconnecting")
                    end
                end
            }

            logger:info("Both sockets created - entering keep-alive loop")

            -- Phase 3: Start command router cleanup task
            if commandRouter then
                commandRouter:startCleanupTask()
            end

            -- Use exact Adobe pattern: global control variable + simple loop
            _G.LightroomPythonBridge.socketServerRunning = true

            while _G.LightroomPythonBridge.socketServerRunning do
                LrTasks.sleep(0.2)  -- 200ms - faster shutdown response (was 500ms)
            end

            logger:info("Socket server loop ended - cleaning up")

            -- Cleanup
            if sender then
                sender:close()
            end
            if receiver then
                receiver:close()
            end

            -- Remove port file
            pcall(function()
                local LrFileUtils = import 'LrFileUtils'
                if LrFileUtils.exists("/tmp/lightroom_ports.txt") then
                    LrFileUtils.delete("/tmp/lightroom_ports.txt")
                end
            end)

            logger:info("Socket server stopped")
            LrDialogs.showBezel("Python Bridge Disconnected", 2)
        end)
    end)
end

-- Function to restart socket server after client disconnect
restartSocketServer = function()
    local logger = getLogger()

    -- FIRST CHECK: Don't restart if shutting down (before spawning async task)
    if not (_G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning) then
        logger:info("Shutdown in progress - not restarting socket server")
        return
    end

    -- Prevent multiple concurrent restarts
    if isRestarting then
        logger:info("Socket server restart already in progress - skipping")
        return
    end

    isRestarting = true
    logger:info("Initiating socket server restart after client disconnect...")

    LrTasks.startAsyncTask(function()
        -- SECOND CHECK: Verify still running inside async task
        if not (_G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning) then
            logger:info("Shutdown detected in restart task - aborting restart")
            isRestarting = false
            return
        end

        -- Reset state for clean restart
        bothSocketsReady = false
        messageQueue = {}
        globalSender = nil
        senderSocket = nil

        -- Small delay to allow socket cleanup
        LrTasks.sleep(2)

        -- THIRD CHECK: Verify still running after sleep
        if not (_G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning) then
            logger:info("Shutdown detected after sleep - aborting restart")
            isRestarting = false
            return
        end

        logger:info("Restarting socket server...")
        startSocketServer()

        isRestarting = false
        logger:info("Socket server restart completed")
    end)
end

-- Stop the socket server
local function stopSocketServer()
    local logger = getLogger()
    logger:info("Stopping socket server - initiating shutdown")

    if _G.LightroomPythonBridge then
        _G.LightroomPythonBridge.socketServerRunning = false
        logger:info("Socket server shutdown flag set")
    end

    -- Send shutdown notification to Python client before closing sockets
    if commandRouter and commandRouter.socketBridge then
        logger:info("Sending shutdown notification to Python client")
        pcall(function()
            commandRouter:sendEvent("server.shutdown", { reason = "Lightroom closing" })
        end)
        -- Give Python client 500ms to disconnect gracefully
        LrTasks.sleep(0.5)
    end

    -- Reset socket state
    bothSocketsReady = false
    messageQueue = {}
    isRestarting = false  -- Reset restart flag

    -- Force cleanup of global socket references
    globalSender = nil
    senderSocket = nil

    -- Clean up command router
    if commandRouter then
        logger:info("Cleaning up command router")
        commandRouter = nil
    end

    -- Remove port file immediately
    pcall(function()
        local LrFileUtils = import 'LrFileUtils'
        if LrFileUtils.exists("/tmp/lightroom_ports.txt") then
            LrFileUtils.delete("/tmp/lightroom_ports.txt")
            logger:info("Port file removed")
        end
    end)

    logger:info("Socket server stop initiated - waiting for cleanup")
end

-- Check if server is running
local function isRunning()
    return _G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning
end

-- Phase 3: Expose command router functionality
local function getCommandRouter()
    return commandRouter
end

-- Send message via socket bridge (for command router)
local function sendMessage(message)
    if senderSocket then
        senderSocket:send(message)
        return true
    end
    return false
end

return {
    start = startSocketServer,
    stop = stopSocketServer,
    isRunning = isRunning,
    -- Phase 3: Command routing interface
    getRouter = getCommandRouter,
    send = sendMessage
}