# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-03-06

Initial public release — 107 CLI commands covering all Lightroom Classic Lua API operations.

### Highlights
- **CLI tool (`lr`)** with `system`, `catalog`, `develop`, `preview`, `selection`, `plugin` command groups
- **107 commands** for full Lightroom Classic control
- **AI Mask API** — subject/sky/background/people/landscape with adjustments and presets
- **Agent-first design** — `lr schema` for dynamic discovery, `--fields`, `--dry-run`, structured JSON errors
- **ResilientSocketBridge** with auto-reconnect, heartbeat, per-command timeouts
- **Lua plugin** bundled and installable via `lr plugin install`
- **3 output formats**: `text`, `json`, `table` (auto-detects TTY)
- **680+ tests** (unit + integration)
