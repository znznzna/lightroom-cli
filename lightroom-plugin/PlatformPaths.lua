-- PlatformPaths.lua
-- Lightroom's Lua sandbox does not provide os.getenv or package globals.
-- macOS only for now; Windows support will use a separate repo.

local PlatformPaths = {}

function PlatformPaths.getPortFilePath()
    return "/tmp/lightroom_ports.txt"
end

return PlatformPaths
