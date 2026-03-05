-- lightroom_sdk/plugin/PlatformPaths.lua
-- Cross-platform port file path using Lightroom SDK API.
-- LrPathUtils.getStandardFilePath("temp") returns:
--   macOS: /tmp (or /private/tmp)
--   Windows: %TEMP% equivalent

local LrPathUtils = import "LrPathUtils"

local PlatformPaths = {}

function PlatformPaths.getPortFilePath()
    local tempDir = LrPathUtils.getStandardFilePath("temp")
    return LrPathUtils.child(tempDir, "lightroom_ports.txt")
end

return PlatformPaths
