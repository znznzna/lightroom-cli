-- AppShutdown.lua (LrShutdownApp)
-- Stops the CLI bridge when Lightroom quits. Sockets are closed immediately;
-- LrShutdownFunction then waits briefly and always calls doneFunction.

return require('BridgeShutdown').begin("app")
