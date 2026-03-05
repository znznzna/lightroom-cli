-- AppShutdown.lua
-- Handles app shutdown — must complete quickly to avoid timeout dialog

local bridge = _G.LightroomPythonBridge
if bridge then
    bridge.shuttingDown = true
    bridge.socketServerRunning = false
    bridge.running = false
end
