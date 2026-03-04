# Changelog

## [1.0.0] - 2026-03-04

### Added
- CLI tool (`lr`) with system/catalog/develop/preview commands
- ResilientSocketBridge with auto-reconnect and heartbeat
- Tab completion for develop parameters
- Installation scripts (`scripts/install.sh`)
- Comprehensive test suite (unit + integration)

### Changed
- Removed MCP server dependency
- Renamed plugin directory to `lightroom-plugin/`
- Removed `time.sleep(0.1)` from client.py

### Fixed
- Lua plugin shutdown race condition (shuttingDown flag)
- Socket cleanup on reconnect and partial connect failure
- CLI command names aligned with Lua plugin registrations
