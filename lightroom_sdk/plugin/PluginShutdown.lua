-- PluginShutdown.lua (LrShutdownPlugin)
-- Stops the CLI bridge when the plugin is disabled, reloaded or removed.
-- Sockets are closed immediately; LrShutdownFunction then waits briefly and
-- always calls doneFunction.

return require('BridgeShutdown').begin("plugin")
