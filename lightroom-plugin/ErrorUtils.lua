-- ErrorUtils.lua
-- Lightweight error handling utilities for Lightroom Python Bridge
-- Designed to work within Lightroom's module system without external dependencies

-- Lazy load LrTasks to avoid import issues during module loading
local LrTasks = nil
local function getLrTasks()
    if not LrTasks then
        LrTasks = import 'LrTasks'
    end
    return LrTasks
end

local ErrorUtils = {}

-- Standard error codes
ErrorUtils.CODES = {
    -- Parameter validation
    MISSING_PARAM = "MISSING_PARAM",
    MISSING_PHOTO_ID = "MISSING_PHOTO_ID",
    INVALID_PARAM = "INVALID_PARAM",
    INVALID_PARAM_TYPE = "INVALID_PARAM_TYPE",
    INVALID_PARAM_VALUE = "INVALID_PARAM_VALUE",
    
    -- Photo/Catalog errors
    PHOTO_NOT_FOUND = "PHOTO_NOT_FOUND",
    INVALID_PHOTO_TYPE = "INVALID_PHOTO_TYPE",
    PHOTO_ACCESS_DENIED = "PHOTO_ACCESS_DENIED",
    CATALOG_ACCESS_FAILED = "CATALOG_ACCESS_FAILED",
    
    -- Develop errors
    DEVELOP_PARAM_NOT_FOUND = "DEVELOP_PARAM_NOT_FOUND",
    DEVELOP_SET_FAILED = "DEVELOP_SET_FAILED",
    DEVELOP_GET_FAILED = "DEVELOP_GET_FAILED",
    
    -- Masking errors
    MASK_NOT_FOUND = "MASK_NOT_FOUND",
    MASKING_MODE_REQUIRED = "MASKING_MODE_REQUIRED",
    LOCAL_PARAM_NOT_AVAILABLE = "LOCAL_PARAM_NOT_AVAILABLE",
    
    -- Network errors
    CONNECTION_FAILED = "CONNECTION_FAILED",
    TIMEOUT = "TIMEOUT",
    
    -- System errors
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE",
    OPERATION_FAILED = "OPERATION_FAILED",
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
}

-- Safe call wrapper that uses LrTasks.pcall for Lightroom compatibility
function ErrorUtils.safeCall(func, ...)
    local args = {...}
    local tasks = getLrTasks()
    return tasks.pcall(function()
        return func(unpack(args))
    end)
end

-- Create standardized error response
function ErrorUtils.createError(code, message, details, severity)
    -- Determine severity based on error code if not provided
    local errorSeverity = severity
    if not errorSeverity then
        -- Map error codes to appropriate severity levels
        if code == ErrorUtils.CODES.MISSING_PARAM or 
           code == ErrorUtils.CODES.MISSING_PHOTO_ID or
           code == ErrorUtils.CODES.INVALID_PARAM or
           code == ErrorUtils.CODES.INVALID_PARAM_TYPE or
           code == ErrorUtils.CODES.INVALID_PARAM_VALUE then
            errorSeverity = "error"
        elseif code == ErrorUtils.CODES.PHOTO_NOT_FOUND or
               code == ErrorUtils.CODES.MASK_NOT_FOUND or
               code == ErrorUtils.CODES.DEVELOP_PARAM_NOT_FOUND then
            errorSeverity = "error"
        elseif code == ErrorUtils.CODES.CONNECTION_FAILED or
               code == ErrorUtils.CODES.TIMEOUT then
            errorSeverity = "warning"
        elseif code == ErrorUtils.CODES.RESOURCE_UNAVAILABLE or
               code == ErrorUtils.CODES.OPERATION_FAILED then
            errorSeverity = "error"
        else
            errorSeverity = "error" -- Default to error for unknown codes
        end
    end

    return {
        success = false,
        error = {
            code = code or ErrorUtils.CODES.UNKNOWN_ERROR,
            message = message or "An error occurred",
            severity = errorSeverity,
            details = details,
            timestamp = os.time()
        }
    }
end

-- Create standardized success response
function ErrorUtils.createSuccess(result, message)
    return {
        success = true,
        result = result or {},
        message = message,
        timestamp = os.time()
    }
end

-- Basic parameter validation
function ErrorUtils.validateRequired(params, requiredFields)
    if not params then
        return false, "No parameters provided"
    end
    
    for _, field in ipairs(requiredFields) do
        if not params[field] or params[field] == "" then
            return false, string.format("Required parameter '%s' is missing", field)
        end
    end
    
    return true
end

-- Validate parameter types
function ErrorUtils.validateTypes(params, typeMap)
    if not params then
        return true -- No params to validate
    end
    
    for field, expectedType in pairs(typeMap) do
        local value = params[field]
        if value ~= nil and type(value) ~= expectedType then
            return false, string.format("Parameter '%s' must be %s, got %s", 
                field, expectedType, type(value))
        end
    end
    
    return true
end

-- Retry operation with exponential backoff
function ErrorUtils.retry(operation, maxAttempts, baseDelay)
    maxAttempts = maxAttempts or 3
    baseDelay = baseDelay or 0.5
    
    for attempt = 1, maxAttempts do
        local success, result = ErrorUtils.safeCall(operation)
        
        if success then
            return true, result
        end
        
        if attempt < maxAttempts then
            local delay = baseDelay * (2 ^ (attempt - 1))
            getLrTasks().sleep(delay)
        end
    end
    
    return false, "Operation failed after " .. maxAttempts .. " attempts"
end

-- Execute operation with timeout
function ErrorUtils.withTimeout(operation, timeoutSeconds)
    timeoutSeconds = timeoutSeconds or 10
    
    local completed = false
    local result = nil
    local success = false
    
    -- Start operation in async task
    getLrTasks().startAsyncTask(function()
        success, result = ErrorUtils.safeCall(operation)
        completed = true
    end)
    
    -- Wait for completion or timeout
    local startTime = getLrTasks().currentTime()
    while not completed do
        getLrTasks().sleep(0.1)
        if getLrTasks().currentTime() - startTime > timeoutSeconds then
            return false, "Operation timed out after " .. timeoutSeconds .. " seconds"
        end
    end
    
    return success, result
end

-- Get logger safely
function ErrorUtils.getLogger(moduleName)
    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.logger then
        return _G.LightroomPythonBridge.logger
    end
    
    local LrLogger = import 'LrLogger'
    local logger = LrLogger(moduleName or 'ErrorUtils')
    logger:enable("logfile")
    return logger
end

-- Log error with context
function ErrorUtils.logError(logger, operation, error, context)
    if logger then
        local message = string.format("[%s] %s", operation or "unknown", tostring(error))
        if context then
            message = message .. " [Context: " .. tostring(context) .. "]"
        end
        logger:error(message)
    end
end

-- Wrap callback with error handling
function ErrorUtils.wrapCallback(callback, operation)
    return function(response)
        local success, err = ErrorUtils.safeCall(function()
            callback(response)
        end)
        
        if not success then
            local logger = ErrorUtils.getLogger()
            ErrorUtils.logError(logger, operation, err, "callback execution")
        end
    end
end

return ErrorUtils