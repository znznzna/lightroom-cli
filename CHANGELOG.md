# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2026-03-07

Stability improvements, batch develop, extended search filters, and new catalog commands.

### Added
- **Extended search filters** for `catalog find` — `--folder-path`, `--capture-date-from`, `--capture-date-to`, `--file-format`, `--keyword`, `--filename`
- **`develop batch-set`** — batch set a single develop parameter across multiple photos (`--photo-ids`)
- **`catalog collection-photos`** — get photos from a collection by ID with pagination
- **`catalog develop-presets`** — list/search develop presets by name or folder
- **NDJSON streaming** — `StreamAggregator` for chunked responses with progress callbacks
- **Command cancellation** — Lua-side `shouldAbort()` checks at chunk boundaries
- **Version sync** — `scripts/sync_version.py` + CI `check-version` job
- **`protocolVersion`** field in ping response

### Fixed
- `searchPhotos` backward compatibility — delegates to `findPhotos` with `hasMore` field preserved
- `captureDateTo` inclusive date handling — date-only input appends `T23:59:59`
- Keyword filter uses plain text matching (`string.find` with `plain=true`)
- Stream cleanup — `_pending_streams` entry removed after final event
- `getCommandRouter` uses correct global key (`commandRouter`, not `router`)
- Negative offset crash in `getCollectionPhotos` — clamped with `math.max`

### Changed
- `searchPhotos` deprecated in favor of `findPhotos`
- 814+ tests (was 750+)

## [1.1.0] - 2026-03-06

MCP Server support, Windows compatibility, and reliability improvements.

### Added
- **MCP Server** — `lr-mcp` entry point for Claude Desktop / Cowork integration
  - `lr mcp install` / `uninstall` / `status` / `test` commands
  - All 107 CLI commands available as MCP tools (`lr_` prefix + snake_case)
  - Auto-resolves absolute path for Claude Desktop's PATH-limited environment
- **Windows support** — platform-aware path resolution (`platformdirs`), CI matrix with `windows-latest`. Not yet tested on real hardware — [please report issues](https://github.com/znznzna/lightroom-cli/issues)
- **Input validation layer** — `lightroom_sdk/validation.py` with type coercion, range checks, enum validation, string sanitization
- **Schema-driven architecture** — `lightroom_sdk/schema.py` as single source of truth for all command parameters
- **`--json` / `--json-stdin`** — JSON input for all commands, enables pipe-based workflows
- **`--dry-run`** — preview command execution without sending to Lightroom

### Fixed
- Schema/Lua parameter name mismatches (14 commands fixed)
- `catalog set-rating 0` — Lua `and/or` idiom fails with `nil`; use explicit `if` statement
- `catalog remove-keyword` — pass keyword object instead of string to `photo:removeKeyword()`
- `catalog select` — `withWriteAccessDo` return value not propagated; use external variable
- `catalog batch-metadata` — iterate photo-keyed table instead of integer-indexed
- `develop range` — `math.abs()` for correct min/max when range is negative number
- `develop set` — unknown parameter detection changed from `getRange` to `getValue`
- Exit code 0 on Lightroom errors — added `success: false` check in `helpers.py`

### Changed
- `fastmcp` is now a required dependency (was optional `[mcp]` extra)
- `develop set` with multiple pairs uses individual `setValue` calls instead of `batchApplySettings`
- 750+ tests (was 680+)

## [1.0.0] - 2026-03-06

Initial public release — 107 CLI commands covering all Lightroom Classic Lua API operations.

### Highlights
- **CLI tool (`lr`)** with `system`, `catalog`, `develop`, `preview`, `selection`, `plugin` command groups
- **107 commands** for full Lightroom Classic control
- **AI Mask API** — subject/sky/background/people/landscape with adjustments and presets
- **Agent-first design** — `lr schema` for dynamic discovery, `--fields`, `--dry-run`, structured JSON errors
- **ResilientSocketBridge** with auto-reconnect, heartbeat, per-command timeouts
- **Lua plugin** bundled and installable via `lr plugin install`
- **3 output formats**: `text`, `json`, `table`
- **680+ tests** (unit + integration)
