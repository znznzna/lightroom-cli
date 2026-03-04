local PlatformPaths = {}

function PlatformPaths.isWindows()
    return package.config:sub(1,1) == "\\"
end

function PlatformPaths.getPortFilePath()
    if PlatformPaths.isWindows() then
        local temp = os.getenv and os.getenv("TEMP") or "C:\\Temp"
        return temp .. "\\lightroom_ports.txt"
    else
        return "/tmp/lightroom_ports.txt"
    end
end

return PlatformPaths
