-- MessageProtocol.lua
-- JSON message encoding/decoding (plain Lua 5.1, no Lightroom dependency)

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

-- JSON arrays. Lua cannot tell an empty array from an empty object, so a table that must be
-- sent as an array even when it is empty carries this metatable (see MessageProtocol.array).
local ARRAY_MT = { __jsonArray = true }
local MAX_DEPTH = 200

-- Mark a table (or a new one) as a JSON array, so an empty one encodes as [] instead of {}
function MessageProtocol.array(t)
    return setmetatable(t or {}, ARRAY_MT)
end

-- JSON null inside an array. nil would leave a hole that ipairs and # stop at, so arrays keep
-- this value in its place. (In an object, null just leaves the key out.)
MessageProtocol.null = setmetatable({}, { __tostring = function() return "null" end })

local STRING_ESCAPES = {
    ['"'] = '\\"', ['\\'] = '\\\\', ['\b'] = '\\b', ['\f'] = '\\f',
    ['\n'] = '\\n', ['\r'] = '\\r', ['\t'] = '\\t',
}

local function escapeChar(c)
    return STRING_ESCAPES[c] or string.format("\\u%04x", string.byte(c))
end

local function encodeString(s)
    -- Every C0 control character must be escaped; %z is NUL in Lua 5.1 patterns
    return '"' .. (s:gsub('[%z\1-\31"\\]', escapeChar)) .. '"'
end

local function encodeNumber(n)
    if n ~= n or n == math.huge or n == -math.huge then
        return "null" -- JSON has no NaN or Infinity
    end
    if n == math.floor(n) and n >= -2^53 and n <= 2^53 then
        -- %.0f, not %d: %d goes through a C long, which is 32-bit on Windows
        return string.format("%.0f", n)
    end
    -- Shortest form that reads back as the same number
    for precision = 14, 17 do
        local text = string.format("%." .. precision .. "g", n)
        if tonumber(text) == n then
            return text
        end
    end
    return string.format("%.17g", n)
end

-- A table is encoded as an array when its keys are exactly 1..#t and it is non-empty or
-- marked. Any other key makes it an object, even when marked, so no field is ever dropped.
local function isArray(t)
    local n = #t
    local count = 0
    for _ in pairs(t) do
        count = count + 1
    end
    if count ~= n then
        return false
    end
    return n > 0 or getmetatable(t) == ARRAY_MT
end

local function encodeValue(obj, depth)
    local t = type(obj)
    if t == "string" then
        return encodeString(obj)
    elseif t == "number" then
        return encodeNumber(obj)
    elseif t == "boolean" then
        return obj and "true" or "false"
    elseif obj == nil or obj == MessageProtocol.null then
        return "null"
    elseif t ~= "table" then
        error("Cannot encode type: " .. t)
    end

    if depth > MAX_DEPTH then
        error("Cannot encode: nested deeper than " .. MAX_DEPTH .. " levels (cyclic table?)")
    end
    local parts = {}
    if isArray(obj) then
        for i = 1, #obj do
            parts[i] = encodeValue(obj[i], depth + 1)
        end
        return "[" .. table.concat(parts, ",") .. "]"
    end
    for k, v in pairs(obj) do
        parts[#parts + 1] = encodeString(tostring(k)) .. ":" .. encodeValue(v, depth + 1)
    end
    return "{" .. table.concat(parts, ",") .. "}"
end

function MessageProtocol:_encodeJSON(obj)
    return encodeValue(obj, 0)
end

-- Decode a JSON message (an object) from Python
function MessageProtocol:decode(jsonString)
    local logger = getLogger()
    
    if type(jsonString) ~= "string" then
        logger:error("MessageProtocol:decode - input must be a string")
        return nil
    end
    
    local success, message = pcall(self._decodeJSON, self, jsonString)
    if not success then
        logger:error("MessageProtocol:decode - JSON parsing failed: " .. tostring(message))
        logger:debug("Failed JSON string: " .. jsonString)
        return nil
    end
    if type(message) ~= "table" or getmetatable(message) == ARRAY_MT then
        logger:error("MessageProtocol:decode - message must be a JSON object")
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

-- JSON decoder following the JSON grammar (RFC 8259). Errors carry the byte position.
-- null decodes to nil in an object (the key is absent) and to MessageProtocol.null in an array.
local STRING_UNESCAPES = {
    ['"'] = '"', ['\\'] = '\\', ['/'] = '/', b = '\b', f = '\f', n = '\n', r = '\r', t = '\t',
}

local function decodeError(pos, message)
    error(string.format("invalid JSON at byte %d: %s", pos, message), 0)
end

local function skipWhitespace(str, pos)
    local _, last = str:find("^[ \t\r\n]*", pos)
    return last + 1
end

-- UTF-8 bytes for a code point (no bit operations: Lua 5.1)
local function utf8Char(cp)
    if cp < 0x80 then
        return string.char(cp)
    elseif cp < 0x800 then
        return string.char(0xC0 + math.floor(cp / 0x40), 0x80 + cp % 0x40)
    elseif cp < 0x10000 then
        return string.char(0xE0 + math.floor(cp / 0x1000), 0x80 + math.floor(cp / 0x40) % 0x40, 0x80 + cp % 0x40)
    end
    return string.char(
        0xF0 + math.floor(cp / 0x40000),
        0x80 + math.floor(cp / 0x1000) % 0x40,
        0x80 + math.floor(cp / 0x40) % 0x40,
        0x80 + cp % 0x40
    )
end

local function decodeString(str, pos)
    -- pos is at the opening quote
    local parts = {}
    local p = pos + 1
    while true do
        local special = str:find('[%z\1-\31"\\]', p)
        if not special then
            decodeError(pos, "unterminated string")
        end
        if special > p then
            parts[#parts + 1] = str:sub(p, special - 1)
        end
        local c = str:sub(special, special)
        if c == '"' then
            return table.concat(parts), special + 1
        elseif c ~= "\\" then
            decodeError(special, "unescaped control character in string")
        end
        local esc = str:sub(special + 1, special + 1)
        if STRING_UNESCAPES[esc] then
            parts[#parts + 1] = STRING_UNESCAPES[esc]
            p = special + 2
        elseif esc == "u" then
            local hex = str:match("^%x%x%x%x", special + 2)
            if not hex then
                decodeError(special, "invalid \\u escape")
            end
            local cp = tonumber(hex, 16)
            p = special + 6
            if cp >= 0xD800 and cp <= 0xDBFF then
                local low = str:match("^\\u(%x%x%x%x)", p)
                local lowCp = low and tonumber(low, 16)
                if lowCp and lowCp >= 0xDC00 and lowCp <= 0xDFFF then
                    cp = 0x10000 + (cp - 0xD800) * 0x400 + (lowCp - 0xDC00)
                    p = p + 6
                else
                    cp = 0xFFFD -- lone high surrogate
                end
            elseif cp >= 0xDC00 and cp <= 0xDFFF then
                cp = 0xFFFD -- lone low surrogate
            end
            parts[#parts + 1] = utf8Char(cp)
        else
            decodeError(special, "invalid escape \\" .. esc)
        end
    end
end

local function decodeNumber(str, pos)
    local p = pos
    if str:sub(p, p) == "-" then
        p = p + 1
    end
    local int = str:match("^%d+", p)
    if not int then
        decodeError(pos, "invalid number")
    end
    if #int > 1 and int:sub(1, 1) == "0" then
        decodeError(pos, "leading zero in number")
    end
    p = p + #int
    if str:sub(p, p) == "." then
        local frac = str:match("^%d+", p + 1)
        if not frac then
            decodeError(p, "digits expected after decimal point")
        end
        p = p + 1 + #frac
    end
    local e = str:sub(p, p)
    if e == "e" or e == "E" then
        p = p + 1
        local sign = str:sub(p, p)
        if sign == "+" or sign == "-" then
            p = p + 1
        end
        local exp = str:match("^%d+", p)
        if not exp then
            decodeError(p, "digits expected in exponent")
        end
        p = p + #exp
    end
    return tonumber(str:sub(pos, p - 1)), p
end

local LITERALS = { ["true"] = true, ["false"] = false, ["null"] = nil }

local decodeValue

local function decodeArray(str, pos, depth)
    local result = MessageProtocol.array()
    local n = 0
    local p = skipWhitespace(str, pos + 1)
    if str:sub(p, p) == "]" then
        return result, p + 1
    end
    while true do
        local value
        value, p = decodeValue(str, p, depth + 1)
        n = n + 1
        if value == nil then
            value = MessageProtocol.null
        end
        result[n] = value
        p = skipWhitespace(str, p)
        local c = str:sub(p, p)
        if c == "]" then
            return result, p + 1
        elseif c ~= "," then
            decodeError(p, "',' or ']' expected in array")
        end
        p = skipWhitespace(str, p + 1)
    end
end

local function decodeObject(str, pos, depth)
    local result = {}
    local p = skipWhitespace(str, pos + 1)
    if str:sub(p, p) == "}" then
        return result, p + 1
    end
    while true do
        if str:sub(p, p) ~= '"' then
            decodeError(p, "string key expected in object")
        end
        local key
        key, p = decodeString(str, p)
        p = skipWhitespace(str, p)
        if str:sub(p, p) ~= ":" then
            decodeError(p, "':' expected after object key")
        end
        local value
        value, p = decodeValue(str, skipWhitespace(str, p + 1), depth + 1)
        result[key] = value
        p = skipWhitespace(str, p)
        local c = str:sub(p, p)
        if c == "}" then
            return result, p + 1
        elseif c ~= "," then
            decodeError(p, "',' or '}' expected in object")
        end
        p = skipWhitespace(str, p + 1)
    end
end

decodeValue = function(str, pos, depth)
    if depth > MAX_DEPTH then
        decodeError(pos, "nested deeper than " .. MAX_DEPTH .. " levels")
    end
    local c = str:sub(pos, pos)
    if c == "{" then
        return decodeObject(str, pos, depth)
    elseif c == "[" then
        return decodeArray(str, pos, depth)
    elseif c == '"' then
        return decodeString(str, pos)
    elseif c == "-" or c:match("%d") then
        return decodeNumber(str, pos)
    end
    for word in pairs({ ["true"] = 1, ["false"] = 1, ["null"] = 1 }) do
        if str:sub(pos, pos + #word - 1) == word then
            return LITERALS[word], pos + #word
        end
    end
    if c == "" then
        decodeError(pos, "unexpected end of input")
    end
    decodeError(pos, "unexpected character '" .. c .. "'")
end

function MessageProtocol:_decodeJSON(str)
    local value, pos = decodeValue(str, skipWhitespace(str, 1), 0)
    pos = skipWhitespace(str, pos)
    if pos <= #str then
        decodeError(pos, "unexpected data after the JSON value")
    end
    return value
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