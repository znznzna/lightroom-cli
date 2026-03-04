local PlatformPaths = {}

function PlatformPaths.isWindows()
    return package.config:sub(1,1) == "\\"
end

function PlatformPaths.getPortFilePath()
    local envPath = os.getenv("LR_PORT_FILE")
    if envPath and envPath ~= "" then
        return envPath
    end

    if PlatformPaths.isWindows() then
        local temp = os.getenv("TEMP") or "C:\\Temp"
        return temp .. "\\lightroom_ports.txt"
    else
        return "/tmp/lightroom_ports.txt"
    end
end

return PlatformPaths
