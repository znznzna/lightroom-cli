-- SelectionModule.lua
-- LrSelection API wrapper

local LrSelection = nil
local LrTasks = import 'LrTasks'

local function getErrorUtils()
    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.ErrorUtils then
        return _G.LightroomPythonBridge.ErrorUtils
    end
    return {
        safeCall = function(func, ...) return LrTasks.pcall(func, ...) end,
        createError = function(code, message) return { error = { code = code or "ERROR", message = message or "An error occurred" } } end,
        createSuccess = function(result) return { result = result or {} } end,
    }
end

local ErrorUtils = getErrorUtils()

local function ensureLrSelection()
    if not LrSelection then
        LrSelection = import 'LrSelection'
    end
end

local function getLogger()
    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.logger then
        return _G.LightroomPythonBridge.logger
    end
    local LrLogger = import 'LrLogger'
    local logger = LrLogger('SelectionModule')
    logger:enable("logfile")
    return logger
end

local SelectionModule = {}

function SelectionModule.flagAsPick(params, callback)
    ensureLrSelection()
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.flagAsPick()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Flag set to pick" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to flag as pick: " .. tostring(err)))
    end
end

function SelectionModule.flagAsReject(params, callback)
    ensureLrSelection()
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.flagAsReject()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Flag set to reject" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to flag as reject: " .. tostring(err)))
    end
end

function SelectionModule.removeFlag(params, callback)
    ensureLrSelection()
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.removeFlag()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Flag removed" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to remove flag: " .. tostring(err)))
    end
end

function SelectionModule.getFlag(params, callback)
    ensureLrSelection()
    local success, result = ErrorUtils.safeCall(function()
        return LrSelection.getFlag()
    end)
    if success then
        local label = "none"
        if result == 1 then label = "pick"
        elseif result == -1 then label = "reject" end
        callback(ErrorUtils.createSuccess({ pickStatus = result, label = label }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to get flag: " .. tostring(result)))
    end
end

function SelectionModule.setRating(params, callback)
    ensureLrSelection()
    local rating = params.rating
    if not rating or rating < 0 or rating > 5 then
        callback(ErrorUtils.createError("INVALID_PARAM_VALUE", "rating must be between 0 and 5"))
        return
    end
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.setRating(rating)
    end)
    if success then
        callback(ErrorUtils.createSuccess({ rating = rating, message = "Rating set" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to set rating: " .. tostring(err)))
    end
end

function SelectionModule.getRating(params, callback)
    ensureLrSelection()
    local success, result = ErrorUtils.safeCall(function()
        return LrSelection.getRating()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ rating = result }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to get rating: " .. tostring(result)))
    end
end

function SelectionModule.setColorLabel(params, callback)
    ensureLrSelection()
    local label = params.label
    if not label then
        callback(ErrorUtils.createError("MISSING_PARAM", "label is required"))
        return
    end
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.setColorLabel(label)
    end)
    if success then
        callback(ErrorUtils.createSuccess({ label = label, message = "Color label set to " .. label }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to set color label: " .. tostring(err)))
    end
end

function SelectionModule.getColorLabel(params, callback)
    ensureLrSelection()
    local success, result = ErrorUtils.safeCall(function()
        return LrSelection.getColorLabel()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ label = result }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to get color label: " .. tostring(result)))
    end
end

function SelectionModule.nextPhoto(params, callback)
    ensureLrSelection()
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.nextPhoto()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Moved to next photo" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to move to next photo: " .. tostring(err)))
    end
end

function SelectionModule.previousPhoto(params, callback)
    ensureLrSelection()
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.previousPhoto()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Moved to previous photo" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to move to previous photo: " .. tostring(err)))
    end
end

function SelectionModule.selectAll(params, callback)
    ensureLrSelection()
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.selectAll()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "All photos selected" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to select all: " .. tostring(err)))
    end
end

function SelectionModule.selectNone(params, callback)
    ensureLrSelection()
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.selectNone()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Selection cleared" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to clear selection: " .. tostring(err)))
    end
end

function SelectionModule.selectInverse(params, callback)
    ensureLrSelection()
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.selectInverse()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Selection inverted" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to invert selection: " .. tostring(err)))
    end
end

function SelectionModule.increaseRating(params, callback)
    ensureLrSelection()
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.increaseRating()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Rating increased" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to increase rating: " .. tostring(err)))
    end
end

function SelectionModule.decreaseRating(params, callback)
    ensureLrSelection()
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.decreaseRating()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Rating decreased" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to decrease rating: " .. tostring(err)))
    end
end

return SelectionModule
