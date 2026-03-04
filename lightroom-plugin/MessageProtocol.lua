-- MessageProtocol.lua
-- JSON-like message encoding/decoding using Lightroom's native capabilities

-- Safe import of LrTableUtils
local LrTableUtils = nil
local success, tableUtils = pcall(import, 'LrTableUtils')
if success then
    LrTableUtils = tableUtils
end

-- Get logger from global state (defensive)
local function getLogger()
    local LrLogger = import 'LrLogger'
    local logger = LrLogger('MessageProtocol')
    logger:enable("logfile")
    
    -- Try to use global logger if available
    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.logger then
        return _G.LightroomPythonBridge.logger
    end
    
    return logger
end

local MessageProtocol = {}

-- Generate unique message ID using simple approach
function MessageProtocol:generateId()
    -- Simple UUID-like generation using timestamp + random
    local template = 'xxxx-xxxx-xxxx-xxxx'
    math.randomseed(os.time() + math.random(1000, 9999))
    return string.gsub(template, 'x', function()
        return string.format('%x', math.random(0, 15))
    end)
end

-- Get current timestamp
function MessageProtocol:getTimestamp()
    return os.time()
end

-- Encode Lua table to JSON string (simple implementation)
function MessageProtocol:encode(message)
    local logger = getLogger()
    
    if type(message) ~= "table" then
        logger:error("MessageProtocol:encode - message must be a table")
        return nil
    end
    
    -- Add timestamp if not present
    if not message.timestamp then
        message.timestamp = self:getTimestamp()
    end
    
    -- Simple JSON encoder for our message format
    local success, result = pcall(self._encodeJSON, self, message)
    if not success then
        logger:error("MessageProtocol:encode - JSON encoding failed: " .. tostring(result))
        return nil
    end
    
    -- Truncate large messages for logging (like base64 image data)
    local logMessage = result
    if string.len(result) > 500 then
        logMessage = string.sub(result, 1, 200) .. "... [" .. string.len(result) .. " chars total] ..." .. string.sub(result, -100)
    end
    logger:debug("Encoded JSON message: " .. logMessage)
    return result
end

-- Simple JSON encoder for basic types
function MessageProtocol:_encodeJSON(obj)
    local t = type(obj)
    
    if t == "string" then
        -- Escape special characters
        local escaped = obj:gsub('"', '\\"'):gsub('\n', '\\n'):gsub('\r', '\\r')
        return '"' .. escaped .. '"'
    elseif t == "number" then
        return tostring(obj)
    elseif t == "boolean" then
        return obj and "true" or "false"
    elseif t == "table" then
        -- Check if it's an array or object
        local isArray = #obj > 0
        local parts = {}
        
        if isArray then
            -- Encode as array
            for i = 1, #obj do
                table.insert(parts, self:_encodeJSON(obj[i]))
            end
            return "[" .. table.concat(parts, ",") .. "]"
        else
            -- Encode as object
            for k, v in pairs(obj) do
                local key = self:_encodeJSON(tostring(k))
                local value = self:_encodeJSON(v)
                table.insert(parts, key .. ":" .. value)
            end
            return "{" .. table.concat(parts, ",") .. "}"
        end
    elseif obj == nil then
        return "null"
    else
        error("Cannot encode type: " .. t)
    end
end

-- Decode JSON string to Lua table using loadstring (for JSON from Python)
function MessageProtocol:decode(jsonString)
    local logger = getLogger()
    
    if type(jsonString) ~= "string" then
        logger:error("MessageProtocol:decode - input must be a string")
        return nil
    end
    
    -- Remove any trailing whitespace/newlines
    jsonString = jsonString:gsub("%s+$", "")
    
    -- This is JSON from Python, so we need to handle JSON format
    -- Use improved JSON parser for nested objects and arrays
    local success, message = pcall(self._parseSimpleJSON, self, jsonString)
    if not success then
        logger:error("MessageProtocol:decode - JSON parsing failed: " .. tostring(message))
        logger:debug("Failed JSON string: " .. jsonString)
        return nil
    end
    
    logger:debug("Decoded message: " .. tostring(message.command or message.event or "unknown"))
    if message.params then
        local paramCount = 0
        for k, v in pairs(message.params) do
            paramCount = paramCount + 1
            -- Truncate long values for display but show full type info
            local displayValue = tostring(v)
            if string.len(displayValue) > 50 then
                displayValue = string.sub(displayValue, 1, 50) .. "... (length: " .. string.len(displayValue) .. ")"
            end
            logger:debug("  decoded param[" .. tostring(k) .. "] = " .. displayValue .. " (type: " .. type(v) .. ")")
        end
        logger:debug("Total decoded params: " .. paramCount)
    end
    return message
end

-- Simple JSON parser for basic cases (handles the messages we're sending)
function MessageProtocol:_parseSimpleJSON(jsonStr)
    -- Very basic JSON parsing for our specific message format
    -- This handles: {"id": "...", "command": "...", "params": {...}, "timestamp": 123}
    
    local result = {}
    
    -- Remove outer braces
    jsonStr = jsonStr:gsub("^%s*{%s*", ""):gsub("%s*}%s*$", "")
    
    -- Simple state machine for proper comma splitting
    local fields = {}
    local current = ""
    local braceDepth = 0
    local bracketDepth = 0  -- Track square brackets for arrays
    local inString = false
    local escapeNext = false
    
    for i = 1, #jsonStr do
        local char = jsonStr:sub(i, i)
        
        if escapeNext then
            current = current .. char
            escapeNext = false
        elseif char == '\\' and inString then
            current = current .. char
            escapeNext = true
        elseif char == '"' then
            current = current .. char
            inString = not inString
        elseif not inString then
            if char == '{' then
                braceDepth = braceDepth + 1
                current = current .. char
            elseif char == '}' then
                braceDepth = braceDepth - 1
                current = current .. char
            elseif char == '[' then
                bracketDepth = bracketDepth + 1
                current = current .. char
            elseif char == ']' then
                bracketDepth = bracketDepth - 1
                current = current .. char
            elseif char == ',' and braceDepth == 0 and bracketDepth == 0 then
                -- Top-level comma - split here (not inside braces or brackets)
                table.insert(fields, current)
                current = ""
            else
                current = current .. char
            end
        else
            current = current .. char
        end
    end
    
    -- Add the last field
    if current ~= "" then
        table.insert(fields, current)
    end
    
    -- Parse each field
    for _, field in ipairs(fields) do
        field = field:gsub("^%s+", ""):gsub("%s+$", "")
        
        -- Extract key-value pairs
        local key, value = field:match('"([^"]+)"%s*:%s*(.+)')
        if key and value then
            value = value:gsub("^%s+", ""):gsub("%s+$", "")
            
            if value:match('^".*"$') then
                -- String value
                result[key] = value:gsub('^"', ''):gsub('"$', '')
            elseif value:match('^%d+$') then
                -- Number value
                result[key] = tonumber(value)
            elseif value:match('^{.*}$') then
                -- Object value - parse nested object recursively
                result[key] = self:_parseSimpleJSON(value)
            elseif value:match('^%[.*%]$') then
                -- Array value - improved array parsing
                local arrayContent = value:gsub("^%[%s*", ""):gsub("%s*%]$", "")
                local arrayResult = {}
                -- logger:debug("Parsing array content: [" .. arrayContent .. "]")  -- Temporarily disabled
                if arrayContent ~= "" then
                    -- Better array parsing that handles nested structures
                    local items = {}
                    local current = ""
                    local depth = 0
                    local inString = false
                    local escapeNext = false
                    
                    for i = 1, #arrayContent do
                        local char = arrayContent:sub(i, i)
                        
                        if escapeNext then
                            current = current .. char
                            escapeNext = false
                        elseif char == '\\' and inString then
                            current = current .. char
                            escapeNext = true
                        elseif char == '"' then
                            current = current .. char
                            inString = not inString
                        elseif not inString then
                            if char == '{' or char == '[' then
                                depth = depth + 1
                                current = current .. char
                            elseif char == '}' or char == ']' then
                                depth = depth - 1
                                current = current .. char
                            elseif char == ',' and depth == 0 then
                                table.insert(items, current)
                                current = ""
                            else
                                current = current .. char
                            end
                        else
                            current = current .. char
                        end
                    end
                    
                    if current ~= "" then
                        table.insert(items, current)
                    end
                    
                    -- logger:debug("Array items found: " .. #items)
                    -- for i, item in ipairs(items) do
                    --     logger:debug("  item[" .. i .. "] = '" .. item .. "'")
                    -- end
                    
                    -- Parse each item
                    for _, item in ipairs(items) do
                        item = item:gsub("^%s+", ""):gsub("%s+$", "")
                        -- logger:debug("  parsing item: '" .. item .. "'")
                        if item:match('^".*"$') then
                            local stringValue = item:gsub('^"', ''):gsub('"$', '')
                            table.insert(arrayResult, stringValue)
                            -- logger:debug("    -> string: '" .. stringValue .. "'")
                        elseif item:match('^%d+$') then
                            local numValue = tonumber(item)
                            table.insert(arrayResult, numValue)
                            -- logger:debug("    -> number: " .. numValue)
                        elseif item:match('^{.*}$') then
                            local objValue = self:_parseSimpleJSON(item)
                            table.insert(arrayResult, objValue)
                            -- logger:debug("    -> object")
                        else
                            table.insert(arrayResult, item)
                            -- logger:debug("    -> other: '" .. item .. "'")
                        end
                    end
                end
                -- logger:debug("Final array result for '" .. key .. "': length=" .. #arrayResult)
                result[key] = arrayResult
            elseif value == "true" then
                result[key] = true
            elseif value == "false" then
                result[key] = false
            elseif value == "null" then
                result[key] = nil
            else
                -- Try as number, fallback to string
                local num = tonumber(value)
                result[key] = num or value
            end
        end
    end
    
    return result
end

-- Create request message
function MessageProtocol:createRequest(command, params)
    return {
        id = self:generateId(),
        command = command,
        params = params or {},
        timestamp = self:getTimestamp()
    }
end

-- Create response message
function MessageProtocol:createResponse(requestId, success, result, error)
    return {
        id = requestId,
        success = success,
        result = result,
        error = error,
        timestamp = self:getTimestamp()
    }
end

-- Create event message (for push notifications)
function MessageProtocol:createEvent(eventType, data)
    return {
        event = eventType,
        data = data or {},
        timestamp = self:getTimestamp()
    }
end

-- Validate message format
function MessageProtocol:validateRequest(message)
    if type(message) ~= "table" then
        return false, "Message must be a table"
    end
    
    if not message.id or type(message.id) ~= "string" then
        return false, "Message must have string ID"
    end
    
    if not message.command or type(message.command) ~= "string" then
        return false, "Message must have string command"
    end
    
    if message.params and type(message.params) ~= "table" then
        return false, "Message params must be a table"
    end
    
    return true, nil
end

function MessageProtocol:validateResponse(message)
    if type(message) ~= "table" then
        return false, "Response must be a table"
    end
    
    if not message.id or type(message.id) ~= "string" then
        return false, "Response must have string ID"
    end
    
    if type(message.success) ~= "boolean" then
        return false, "Response must have boolean success field"
    end
    
    return true, nil
end

function MessageProtocol:validateEvent(message)
    if type(message) ~= "table" then
        return false, "Event must be a table"
    end
    
    if not message.event or type(message.event) ~= "string" then
        return false, "Event must have string event type"
    end
    
    if message.data and type(message.data) ~= "table" then
        return false, "Event data must be a table"
    end
    
    return true, nil
end

return MessageProtocol