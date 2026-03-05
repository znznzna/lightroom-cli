-- SimpleSocketBridge.lua
-- Socket bridge with fixed ports, deferred restart, and Phase 3 command routing

local LrSocket = import 'LrSocket'
local LrTasks = import 'LrTasks'
local LrFunctionContext = import 'LrFunctionContext'
local LrDialogs = import 'LrDialogs'
local PlatformPaths = require("PlatformPaths")
local Config = require("Config")

-- Module-level state
local commandRouter = nil
local senderSocket = nil
local globalSender = nil
local bothSocketsReady = false
local messageQueue = {}
local restartPending = false

-- Fixed ports from Config
local SENDER_PORT = nil   -- set in startSocketServer
local RECEIVER_PORT = nil -- set in startSocketServer

local function getPhase3Modules()
    local bridge = _G.LightroomPythonBridge
    if not bridge or not bridge.phase3Loaded then
        return nil, nil
    end
    return bridge.MessageProtocol, bridge.CommandRouter
end

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

-- Forward declaration
local requestRestart

local function processQueuedMessages()
    local logger = getLogger()
    if #messageQueue > 0 then
        logger:info("Processing " .. #messageQueue .. " queued messages")
        local MessageProtocol, _ = getPhase3Modules()
        if MessageProtocol and commandRouter then
            for _, message in ipairs(messageQueue) do
                local decoded = MessageProtocol:decode(tostring(message))
                if decoded then
                    commandRouter:dispatch(decoded)
                else
                    logger:error("Failed to decode queued message: " .. tostring(message))
                end
            end
        end
        messageQueue = {}
    end
end

local function writePortFile(senderPort, receiverPort)
    local logger = getLogger()
    local success, err = LrTasks.pcall(function()
        local file = io.open(PlatformPaths.getPortFilePath(), "w")
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

-- Socket callbacks: request deferred restart on close, self-reconnect on timeout
local function onSocketClosed(socketName)
    local logger = getLogger()
    logger:info(socketName .. " socket closed")
    local bridge = _G.LightroomPythonBridge
    if bridge and bridge.shuttingDown then return end
    if bridge and bridge.socketServerRunning then
        requestRestart(socketName .. "_closed")
    end
end

local function onSocketError(socketName, socket, err)
    local logger = getLogger()
    logger:error(socketName .. " socket error: " .. err)
    local bridge = _G.LightroomPythonBridge
    if bridge and bridge.shuttingDown then return end
    if err == "timeout" and bridge and bridge.socketServerRunning then
        logger:info(socketName .. " timeout - self reconnect")
        socket:reconnect()
    end
end

local function startSocketServer()
    local logger = getLogger()

    -- Guard against multiple concurrent starts
    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning then
        logger:info("Socket server already running - skipping start")
        return
    end

    logger:info("Starting socket server with fixed ports")

    -- Read fixed ports from Config
    Config:init()
    SENDER_PORT = Config:get("pluginSendPort")
    RECEIVER_PORT = Config:get("pluginReceivePort")
    logger:info("Fixed ports: sender=" .. SENDER_PORT .. ", receiver=" .. RECEIVER_PORT)

    -- Initialize command router
    local MessageProtocol, CommandRouter = getPhase3Modules()
    if CommandRouter then
        commandRouter = CommandRouter
        commandRouter:init()
        _G.LightroomPythonBridge.commandRouter = commandRouter
        logger:info("Command router initialized")

        local bridge = _G.LightroomPythonBridge
        if bridge then
            if bridge.registerSystemCommands then
                bridge.registerSystemCommands()
            end
            if bridge.registerApiCommands and bridge.phase4Loaded then
                bridge.registerApiCommands()
            end
        end
    else
        logger:error("Phase 3 modules not available")
    end

    LrTasks.startAsyncTask(function()
        LrFunctionContext.callWithContext('lightroom_python_bridge', function(context)
            logger:info("Socket context created")

            local sender, receiver

            -- Create sender socket with FIXED port
            sender = LrSocket.bind {
                functionContext = context,
                address = "localhost",
                port = SENDER_PORT,
                mode = "send",
                plugin = _PLUGIN,

                onConnecting = function(socket, port)
                    logger:info("Sender socket listening on port " .. port)
                end,

                onConnected = function(socket, port)
                    logger:info("Python connected to sender socket")
                    senderSocket = socket
                    globalSender = socket

                    if commandRouter then
                        commandRouter:setSocketBridge({
                            send = function(jsonData)
                                if globalSender and jsonData then
                                    if type(jsonData) ~= "string" then
                                        logger:error("jsonData is not a string: " .. type(jsonData))
                                        return false
                                    end
                                    if not string.match(jsonData, "\n$") then
                                        jsonData = jsonData .. "\n"
                                    end
                                    local logData = jsonData
                                    if string.len(logData) > 500 then
                                        logData = string.sub(logData, 1, 200) .. "... [" .. string.len(logData) .. " chars] ..." .. string.sub(logData, -100)
                                    end
                                    logger:debug("Sending: " .. logData)
                                    globalSender:send(jsonData)
                                    return true
                                else
                                    logger:error("Cannot send - socket or data is nil")
                                    return false
                                end
                            end
                        })

                        bothSocketsReady = true
                        logger:info("Both sockets ready")
                        processQueuedMessages()

                        commandRouter:sendEvent("connection.established", {
                            senderPort = SENDER_PORT,
                            receiverPort = RECEIVER_PORT
                        })
                    end
                end,

                onClosed = function(socket)
                    onSocketClosed("Sender")
                end,

                onError = function(socket, err)
                    onSocketError("Sender", socket, err)
                end
            }

            -- Create receiver socket with FIXED port
            receiver = LrSocket.bind {
                functionContext = context,
                address = "localhost",
                port = RECEIVER_PORT,
                mode = "receive",
                plugin = _PLUGIN,

                onConnecting = function(socket, port)
                    logger:info("Receiver socket listening on port " .. port)
                end,

                onConnected = function(socket, port)
                    logger:info("Python connected to receiver socket")
                end,

                onMessage = function(socket, message)
                    logger:debug("Message received")

                    if not bothSocketsReady then
                        logger:warn("Sockets not ready - queuing message")
                        table.insert(messageQueue, message)
                        return
                    end

                    local MessageProtocol, _ = getPhase3Modules()
                    if MessageProtocol and commandRouter then
                        local decoded = MessageProtocol:decode(tostring(message))
                        if decoded then
                            commandRouter:dispatch(decoded)
                        else
                            logger:error("Failed to decode message: " .. tostring(message))
                        end
                    end
                end,

                onClosed = function(socket)
                    onSocketClosed("Receiver")
                end,

                onError = function(socket, err)
                    onSocketError("Receiver", socket, err)
                end
            }

            -- Write port file with fixed ports
            writePortFile(SENDER_PORT, RECEIVER_PORT)

            logger:info("Both sockets created - entering keep-alive loop")

            _G.LightroomPythonBridge.socketServerRunning = true

            if commandRouter then
                commandRouter:startCleanupTask()
            end

            while _G.LightroomPythonBridge.socketServerRunning do
                LrTasks.sleep(0.2)
            end

            logger:info("Socket server loop ended - cleaning up")

            if sender then sender:close() end
            if receiver then receiver:close() end

            -- Only remove port file on actual shutdown, not on restart
            local bridge = _G.LightroomPythonBridge
            if bridge and bridge.shuttingDown then
                pcall(function()
                    local LrFileUtils = import 'LrFileUtils'
                    local portFile = PlatformPaths.getPortFilePath()
                    if LrFileUtils.exists(portFile) then
                        LrFileUtils.delete(portFile)
                    end
                end)
                logger:info("Socket server stopped (shutdown)")
                LrDialogs.showBezel("CLI Bridge Disconnected", 2)
            else
                logger:info("Socket server stopped (restart pending)")
            end
        end)
    end)
end

-- Deferred restart: never called inside socket callbacks directly
-- Uses LrTasks.startAsyncTask to escape the callback context
requestRestart = function(reason)
    local logger = getLogger()

    if not (_G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning) then
        logger:info("Shutdown in progress - not restarting")
        return
    end

    if restartPending then
        logger:info("Restart already pending - skipping (" .. reason .. ")")
        return
    end

    restartPending = true
    logger:info("Restart requested: " .. reason)

    LrTasks.startAsyncTask(function()
        local logger = getLogger()

        if not (_G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning) then
            restartPending = false
            return
        end

        -- Stop current server loop
        _G.LightroomPythonBridge.socketServerRunning = false

        -- Reset state
        bothSocketsReady = false
        messageQueue = {}
        globalSender = nil
        senderSocket = nil

        -- Wait for old server loop (0.2s poll) to exit and sockets to close
        LrTasks.sleep(0.3)

        if _G.LightroomPythonBridge and _G.LightroomPythonBridge.shuttingDown then
            restartPending = false
            return
        end

        logger:info("Restarting socket server (fixed ports)...")
        startSocketServer()

        restartPending = false
        logger:info("Socket server restart completed")
    end)
end

local function stopSocketServer()
    local logger = getLogger()
    logger:info("Stopping socket server")

    -- Set flags immediately (non-blocking)
    if _G.LightroomPythonBridge then
        _G.LightroomPythonBridge.shuttingDown = true
        _G.LightroomPythonBridge.socketServerRunning = false
    end

    -- Best-effort shutdown event (no sleep/wait)
    if commandRouter and commandRouter.socketBridge then
        pcall(function()
            commandRouter:sendEvent("server.shutdown", { reason = "Lightroom closing" })
        end)
    end

    -- Reset state immediately
    bothSocketsReady = false
    messageQueue = {}
    restartPending = false
    globalSender = nil
    senderSocket = nil
    commandRouter = nil

    -- Remove port file
    pcall(function()
        local LrFileUtils = import 'LrFileUtils'
        local portFile = PlatformPaths.getPortFilePath()
        if LrFileUtils.exists(portFile) then
            LrFileUtils.delete(portFile)
        end
    end)

    logger:info("Socket server stopped")
end

local function isRunning()
    return _G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning
end

local function getCommandRouter()
    return commandRouter
end

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
    getRouter = getCommandRouter,
    send = sendMessage
}
