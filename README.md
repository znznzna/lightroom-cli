# Lightroom CLI

[![Test](https://github.com/znznzna/lightroom-cli/actions/workflows/test.yml/badge.svg)](https://github.com/znznzna/lightroom-cli/actions/workflows/test.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Japanese / 日本語](README.ja.md)

**Full command-line control for Adobe Lightroom Classic — 107 commands.**

Develop parameter adjustment, masking, tone curves, catalog management, selection operations, and more. Ideal for batch processing and scripted automation.

## Architecture

```
+---------------------+     TCP Socket (JSON-RPC)     +--------------+
|  Lightroom Classic  |<----------------------------->|  Python SDK  |
|  (Lua Plugin)       |   Dual socket: send/receive   |              |
+---------------------+                               +------+-------+
                                                              |
                                              +---------------+---------------+
                                              |               |               |
                                       +------+-------+ +-----+------+ +------+------+
                                       |   CLI (lr)   | | MCP Server | | Python SDK  |
                                       |   Click app  | | (lr-mcp)   | |   Direct    |
                                       +--------------+ +------------+ +-------------+
```

A Lua plugin runs inside Lightroom Classic and communicates with the Python SDK via dual TCP sockets. Three interfaces are available: the `lr` CLI, the MCP Server for Claude Desktop/Cowork, and the Python SDK for direct integration.

## Quick Start

### Prerequisites

- **Python 3.10+**
- **Adobe Lightroom Classic** (desktop version)
- macOS / Windows

### Installation

```bash
pip install lightroom-cli
```

Then install the Lightroom plugin and restart Lightroom Classic:

```bash
lr plugin install
```

The plugin appears under **File > Plug-in Manager** as "Lightroom CLI Bridge".

### Choose Your Integration

#### Option A: Claude Code (SKILL-based)

For **Claude Code** users — install the Claude Code Plugin so the agent can discover and use all 107 commands via the SKILL file:

```bash
/plugin marketplace add znznzna/lightroom-cli
/plugin install lightroom-cli@lightroom-cli
```

The agent reads `SKILL.md` to understand available commands, parameters, and workflows. No manual command typing needed.

#### Option B: Claude Desktop / Cowork (MCP Server)

For **Claude Desktop** or **Cowork** users — register the MCP Server:

```bash
lr mcp install
```

Restart Claude Desktop / Cowork. All 107 commands are available as MCP tools with `lr_` prefix (e.g., `lr_system_ping`, `lr_catalog_list`).

Check MCP status:

```bash
lr mcp status
lr mcp test      # Test connection to Lightroom
```

#### Option C: Direct CLI / Scripting

Use the `lr` command directly for shell scripting and automation:

```bash
lr system ping
lr catalog list --limit 10
lr develop set Exposure 1.5
```

### Verify Connection

1. Open Lightroom Classic
2. Go to **File > Plugin Extras > Start CLI Bridge**
3. Run:

```bash
lr system ping
# -> pong

lr system status
```

> **Note:** The bridge does not start automatically. You must select "Start CLI Bridge" from the menu each time you launch Lightroom.

## Usage Examples

```bash
# Get currently selected photo
lr catalog get-selected

# Set develop parameters
lr develop set Exposure 1.5 Contrast 25 Clarity 30

# Apply AutoTone
lr develop auto-tone

# Apply S-curve to tone curve
lr develop curve s-curve

# Create a mask and add a brush
lr develop mask create
lr develop mask add brush

# Apply a preset
lr develop preset "Vivid Landscape"

# Rating and flag operations
lr selection set-rating 5
lr selection flag

# Search the catalog
lr catalog search "landscape" --limit 20

# JSON output
lr -o json develop get-settings

# Table output
lr -o table catalog list --limit 10
```

## Command Groups

| Group | Commands | Description |
|-------|----------|-------------|
| [`lr system`](#lr-system) | 4 | Connection management and status |
| [`lr catalog`](#lr-catalog) | 27 | Catalog operations, photo search, metadata |
| [`lr develop`](#lr-develop) | 55 | Develop settings, masks, curves, filters |
| [`lr preview`](#lr-preview) | 4 | Preview generation and info |
| [`lr selection`](#lr-selection) | 17 | Selection, flags, ratings, labels |
| [`lr plugin`](#lr-plugin) | 3 | Plugin installation and management |
| [`lr mcp`](#lr-mcp) | 4 | MCP Server management |

**For all 107 commands, see the [CLI Reference](docs/CLI_REFERENCE.md).**

### lr system

```bash
lr system ping                # Connection test
lr system status              # Bridge status
lr system reconnect           # Force reconnect
lr system check-connection    # Detailed connection check
```

### lr catalog

```bash
lr catalog get-selected               # Get currently selected photo
lr catalog list --limit 10            # List photos
lr catalog search "keyword"           # Search
lr catalog get-info <photo_id>        # Detailed metadata
lr catalog set-rating <id> 5          # Set rating
lr catalog add-keywords <id> kw1 kw2  # Add keywords
lr catalog set-title <id> "Title"     # Set title
lr catalog collections                # List collections
lr catalog create-collection "name"   # Create collection
lr catalog keywords                   # List keywords
lr catalog set-view-filter <json>     # Set view filter
lr catalog rotate-left                # Rotate left
lr catalog create-virtual-copy        # Create virtual copy
```

### lr develop

```bash
# Basic operations
lr develop get-settings               # Get all develop settings
lr develop set Exposure 1.5           # Set parameter
lr develop get Exposure               # Get single parameter
lr develop auto-tone                  # AutoTone
lr develop auto-wb                    # Auto White Balance
lr develop reset                      # Reset settings
lr develop apply '{"Exposure": 1.0}'  # Apply settings from JSON

# Tone curve
lr develop curve get                  # Get curve
lr develop curve set '[[0,0],[128,140],[255,255]]'
lr develop curve s-curve              # S-curve preset
lr develop curve linear               # Linear reset
lr develop curve add-point 128 140    # Add point

# Masking
lr develop mask list                  # List all masks
lr develop mask create                # Create new mask
lr develop mask add brush             # Add brush component
lr develop mask intersect luminance   # Intersect with luminance
lr develop mask subtract color        # Subtract with color
lr develop mask invert mask-1         # Invert mask

# Filters
lr develop filter graduated           # Graduated filter
lr develop filter radial              # Radial filter
lr develop filter brush               # Brush filter
lr develop filter ai-select           # AI select

# Local adjustments
lr develop local set Exposure 0.5     # Set local parameter
lr develop local get Exposure         # Get local parameter

# Tools, presets, and snapshots
lr develop tool crop                  # Select tool
lr develop preset "Preset Name"       # Apply preset
lr develop snapshot "Snapshot Name"   # Create snapshot
lr develop copy-settings              # Copy settings
lr develop paste-settings             # Paste settings
```

### lr preview

```bash
lr preview generate-current           # Generate preview for selected photo
lr preview generate --size 2048       # Generate with specified size
lr preview generate-batch             # Batch generation
lr preview info                       # Preview info
```

### lr selection

```bash
lr selection flag                     # Pick flag
lr selection reject                   # Reject flag
lr selection unflag                   # Remove flag
lr selection get-flag                 # Get flag state
lr selection set-rating 5             # Set rating (0-5)
lr selection get-rating               # Get rating
lr selection color-label red          # Set color label
lr selection get-color-label          # Get color label
lr selection toggle-label red         # Toggle label
lr selection next                     # Next photo
lr selection previous                 # Previous photo
lr selection select-all               # Select all
lr selection select-none              # Deselect all
lr selection select-inverse           # Invert selection
lr selection extend --direction right # Extend selection
```

### lr mcp

```bash
lr mcp install                # Register MCP server in Claude Desktop config
lr mcp install --force        # Overwrite existing entry
lr mcp uninstall              # Remove MCP server entry
lr mcp status                 # Show installation status
lr mcp test                   # Test connection via MCP
```

## Global Options

```bash
lr --output json ...    # JSON output (-o json)
lr --output table ...   # Table output (-o table)
lr --verbose ...        # Debug logging (-v)
lr --timeout 60 ...     # Timeout in seconds (-t 60)
lr --version            # Show version
```

## Configuration

| Environment Variable | Description |
|---------------------|-------------|
| `LR_PORT_FILE` | Path to the port file used for socket communication |
| `LR_PLUGIN_DIR` | Path to the Lightroom plugin directory |

## Features

- **Auto-reconnect**: Automatically retries when the Lightroom connection drops (exponential backoff)
- **Heartbeat**: Connection monitoring at 30-second intervals
- **Shutdown detection**: Graceful handling when Lightroom exits
- **3 output formats**: `text` / `json` / `table`
- **Tab completion**: Completion support for develop parameter names
- **Per-command timeout**: Long-running operations like preview generation are automatically extended
- **MCP Server**: Native integration with Claude Desktop and Cowork

## Development

### For Contributors Only

> **Regular users can skip this section.** `pip install lightroom-cli` is all you need.

```bash
git clone https://github.com/znznzna/lightroom-cli.git
cd lightroom-cli
pip install -e ".[dev]"
lr plugin install --dev
```

```bash
# Run tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ -v --cov=lightroom_sdk --cov=cli --cov=mcp_server

# Single test file
python -m pytest tests/integration/test_cli_develop.py -v
```

## Project Structure

```
lightroom-cli/
+-- cli/                      # Click CLI application
|   +-- main.py               # Entry point (lr command)
|   +-- output.py             # OutputFormatter (json/text/table)
|   +-- helpers.py            # Command execution helpers
|   +-- commands/             # Command groups
|       +-- system.py         # lr system
|       +-- catalog.py        # lr catalog
|       +-- develop.py        # lr develop (+ curve/mask/local/filter/debug/color)
|       +-- preview.py        # lr preview
|       +-- selection.py      # lr selection
|       +-- plugin.py         # lr plugin
|       +-- mcp.py            # lr mcp
+-- mcp_server/               # MCP Server (FastMCP)
|   +-- server.py             # Entry point (lr-mcp command)
|   +-- tool_registry.py      # Schema-driven tool registration
|   +-- connection.py         # Bridge connection management
|   +-- instructions.py       # MCP server instructions
+-- lightroom_sdk/            # Python SDK
|   +-- client.py             # LightroomClient
|   +-- socket_bridge.py      # Dual TCP socket
|   +-- resilient_bridge.py   # Auto-reconnect + heartbeat
|   +-- schema.py             # Command schemas (single source of truth)
|   +-- validation.py         # Input validation + sanitization
|   +-- retry.py              # Per-command timeout
|   +-- protocol.py           # JSON-RPC protocol
|   +-- paths.py              # Path resolution utilities
|   +-- plugin/               # Lua plugin (bundled)
|       +-- PluginInit.lua    # Command router (107 commands)
|       +-- DevelopModule.lua # Develop operations
|       +-- CatalogModule.lua # Catalog operations
+-- tests/                    # pytest test suite (750+ tests)
```

## Requirements

- Python >= 3.10
- Adobe Lightroom Classic
- macOS / Windows

### Python Dependencies

- [click](https://click.palletsprojects.com/) >= 8.1 — CLI framework
- [rich](https://rich.readthedocs.io/) >= 13.0 — Table output
- [pydantic](https://docs.pydantic.dev/) >= 2.0 — Data validation
- [platformdirs](https://platformdirs.readthedocs.io/) >= 3.0 — Platform-specific directory paths
- [fastmcp](https://github.com/jlowin/fastmcp) >= 3.0 — MCP Server framework

## License

[MIT](LICENSE)
