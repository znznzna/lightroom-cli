# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2026-03-04

Full SDK coverage release — 107 CLI commands covering all Lightroom Classic Lua API operations.

### Added

**Develop Module (55 commands)**
- Tone curve commands: `get`, `set`, `add-point`, `remove-point`, `s-curve`, `linear` (per-channel RGB/Red/Green/Blue)
- Masking commands: `list`, `create`, `select`, `delete`, `invert`, `add`, `intersect`, `subtract`, `complex`, `toggle-overlay`, `activate`, `go-to`
- Mask tool management: `tool-info`, `select-tool`, `delete-tool`
- Local adjustment commands: `set`, `get`, `params`, `apply`, `create-mask`
- Filter creation: `graduated`, `radial`, `brush`, `ai-select`, `range`
- Color operations: `enhance`, `cyan-swatch`, `green-swatch`
- Debug tools: `dump`, `probe`, `monitor`, `gradient-params`
- Reset commands: `reset-brush`, `reset-circular`, `reset-crop`, `reset-gradient`, `reset-healing`, `reset-masking`, `reset-redeye`, `reset-spot`, `reset-transforms`
- Develop operations: `apply`, `auto-wb`, `get`, `range`, `reset-param`, `process-version`, `set-process-version`, `tool`, `edit-in-photoshop`
- Preset/snapshot: `preset`, `snapshot`, `copy-settings`, `paste-settings`

**Catalog Module (27 commands)**
- Advanced search: `find`, `find-by-path`
- Collection management: `collections`, `create-collection`, `create-collection-set`, `create-smart-collection`
- Keyword management: `keywords`, `create-keyword`, `remove-keyword`
- View filters: `get-view-filter`, `set-view-filter`
- Photo operations: `rotate-left`, `rotate-right`, `create-virtual-copy`, `remove-from-catalog`
- Metadata: `set-title`, `set-caption`, `set-color-label`, `set-metadata`, `batch-metadata`, `set-flag`, `get-flag`
- Folder listing: `folders`

**Selection Module (17 commands)**
- Flag getters: `get-flag`, `get-rating`, `get-color-label`
- Rating: `set-rating`, `increase-rating`, `decrease-rating`
- Label: `color-label`, `toggle-label` (red/yellow/green/blue/purple)
- Selection: `select-all`, `select-none`, `select-inverse`, `extend`, `deselect-active`, `deselect-others`

**Preview Module (4 commands)**
- `info` command for preview metadata

**Infrastructure**
- `bridge_command` decorator to reduce CLI boilerplate
- `pytest-cov` added to dev dependencies

### Fixed
- ResilientSocketBridge now only retries on connection errors (not timeouts)
- Masking CLI parameter keys aligned with Lua handlers (`maskId`, `toolId`, `maskType`)
- Tone curve channel-to-parameter mapping (`RGB` → `ToneCurvePV2012`, etc.)

## [1.0.0] - 2026-03-04

Initial release with core functionality.

### Added
- CLI tool (`lr`) with `system`, `catalog`, `develop`, `preview` command groups
- ResilientSocketBridge with auto-reconnect and heartbeat
- Lua plugin with dual TCP socket communication
- Tab completion for develop parameters
- Installation scripts (`scripts/install.sh`, `scripts/install-plugin.sh`)
- 3 output formats: `text`, `json`, `table`
- Comprehensive test suite (unit + integration)

### Fixed
- Lua plugin shutdown race condition (shuttingDown flag)
- Socket cleanup on reconnect and partial connect failure
