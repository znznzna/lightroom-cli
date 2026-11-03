-- WriteAccess.lua
-- Wrapper around LrCatalog:withWriteAccessDo that never treats a skipped write as success.
--
-- With timeoutParams, withWriteAccessDo returns "aborted" instead of raising when it cannot get
-- write access in time (another write holds the catalog). The function was then never run, so
-- callers that only checked "no error" reported success for a change that did not happen, and
-- callers that answer from inside the function never answered at all. Raising here makes both
-- kinds of caller finish the request once, with an explicit error: the safeCall around the write
-- reports it, or CommandRouter's pcall turns it into a HANDLER_ERROR response.

local WriteAccess = {}

WriteAccess.BLOCKED = "WRITE_ACCESS_BLOCKED"

function WriteAccess.run(catalog, actionName, func, timeoutParams)
    local status = catalog:withWriteAccessDo(actionName, func, timeoutParams)
    if status == "aborted" then
        error(WriteAccess.BLOCKED .. ": could not get catalog write access for '" .. tostring(actionName)
            .. "' (another operation is writing to the catalog); nothing was changed", 0)
    end
    return status
end

return WriteAccess
