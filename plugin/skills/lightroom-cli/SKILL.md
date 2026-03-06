# Lightroom CLI Skills for Claude Code

## Prerequisites

- lightroom-cli installed (`lr --version` to verify)
- Lightroom Classic running with plugin active
- Connection verified (`lr system check-connection`)

## Agent Quick Contract

1. **Always use `-o json`** (or pipe) for machine-readable output
2. **Always use `--fields`** to limit response size: `lr --fields id,filename catalog list`
3. **Check `lr schema CMD`** for parameter types and ranges before calling
4. **Use `--dry-run`** before mutating commands to preview changes
5. **Exit codes matter**: 0=ok, 2=validation, 3=connection, 4=timeout
6. **`requires_confirm` commands** need `--confirm` flag (see Destructive Commands below)

## Schema-First Discovery

Use `lr schema` to discover commands dynamically — don't memorize command lists.

```bash
lr schema                      # List all module groups
lr schema develop              # List commands in a group
lr schema develop.set          # Show command detail with parameters
lr develop range Exposure      # Get min/max for a develop parameter
```

**Example** (`lr -o json schema develop.set`):
```json
{"command": "develop.set", "mutating": true, "supports_dry_run": true, "requires_confirm": false, "risk_level": "write", "params": [{"name": "parameter", "type": "string", "required": true}, {"name": "value", "type": "float", "required": true}], "response_fields": ["parameter", "value", "previousValue"]}
```

## Getting Started for Agents

### Step 1: Verify connection

```bash
lr system check-connection
```

If unavailable, ensure Lightroom Classic is running with the plugin active.

### Step 2: Get photo IDs

```bash
# Get currently selected photos (most common)
lr -o json catalog get-selected
# Returns: {"photos": [{"id": "12345", "filename": "IMG_001.jpg", ...}], "count": 1}

# Or list all photos
lr -o json --fields id,filename catalog list --limit 10
```

The `id` field in each photo object is the PHOTO_ID used in subsequent commands.

### Step 3: Operate on photos

```bash
# Read settings
lr -o json develop get-settings

# Modify settings (values are ABSOLUTE, not relative — see Gotchas)
lr develop set Exposure 0.5 Contrast 25

# Set metadata
lr catalog set-rating 12345 5
```

### catalog vs selection

| | catalog | selection |
|---|---------|-----------|
| **Target** | Specific photo by ID | Currently selected photo(s) |
| **Use when** | You know the exact photo ID | Operating on what the user is viewing |
| **Agent preference** | Recommended (explicit, predictable) | Use for navigation workflows |

**Key:** `develop` commands implicitly target the currently selected photo(s). Use `catalog select PHOTO_ID` to set the target first, then `develop set ...`.

## Module Overview

Discover full command lists with `lr schema MODULE`. Below is what each module does.

- **system** — Connection management: ping, status, check-connection, reconnect
- **catalog** — Photo management: list, find, get-info, set-rating, add-keywords, set-flag, collections, collection-photos, folders, develop-presets, metadata operations. Use explicit PHOTO_ID for predictable results.
- **develop** — Image editing: get/set parameters, auto-tone, auto-wb, reset, apply JSON settings, presets, snapshots, tone curve, AI masks (subject/sky/background/etc with `--adjust`), graduated/radial/brush filters, local adjustments, crop/transform resets
- **selection** — Navigation & flagging: next/previous, flag/reject/unflag, set-rating, color-label, select-all/none/inverse
- **preview** — Preview generation: generate for current/batch, get preview info
- **plugin** — Plugin management: install, uninstall, status

## Common Workflows

### Relative value adjustment (values are absolute!)

```bash
lr -o json develop get Exposure        # 1. Read current value (e.g., 0.3)
# 2. Compute new value: 0.3 + 0.5 = 0.8
lr develop set Exposure 0.8            # 3. Set absolute value
```

### Batch find + mutate (agent pattern)

```bash
# 1. Find photos matching criteria
lr -o json --fields photos.id catalog find --rating 4 --rating-op ">="
# 2. Parse JSON → loop over photos[].id
lr catalog add-keywords PHOTO_ID1 portfolio
lr catalog add-keywords PHOTO_ID2 portfolio
```

> **Note:** There is no "find and mutate" single command. Parse JSON from `find`/`list` and call mutating commands per photo ID.

### catalog find — filter options

```bash
# Basic filters
lr -o json catalog find --rating 5                          # Exact rating
lr -o json catalog find --rating 3 --rating-op ">="         # Rating >= 3
lr -o json catalog find --flag pick                          # Flagged photos
lr -o json catalog find --color-label red                    # Color label
lr -o json catalog find --camera "Canon"                     # Camera model (substring)

# New filters (v1.2.0)
lr -o json catalog find --folder-path "2024/vacation"        # Folder path (substring)
lr -o json catalog find --capture-date-from "2024-06-01"     # Captured after date
lr -o json catalog find --capture-date-to "2024-12-31"       # Captured before date
lr -o json catalog find --file-format RAW                    # File format (exact: RAW/DNG/JPEG)
lr -o json catalog find --keyword "landscape"                # Keyword (substring)
lr -o json catalog find --filename "IMG_00"                  # Filename (substring)

# Combined filters
lr -o json catalog find --rating 4 --rating-op ">=" --flag pick --file-format RAW
```

Unknown filter keys return a `warnings` field in the response. Invalid values (e.g., non-numeric rating) return a validation error.

### Safe editing with snapshots

```bash
lr develop snapshot "before-edit"           # 1. Checkpoint (no undo command exists!)
lr develop set Exposure 1.0 Contrast 25     # 2. Edit
lr develop reset                            # 3. Revert if unhappy
```

### AI mask with adjustments

```bash
lr develop ai sky --adjust '{"Exposure": -1.0, "Highlights": -30}'   # Darken sky
lr develop ai subject --adjust-preset brighten-subject               # Named preset
lr -o json develop ai presets                                        # List presets
```

### Apply consistent edits across photos

```bash
lr -o json develop get-settings                              # 1. Get reference
lr develop apply --settings '{"Exposure": 1.0, "Contrast": 25}'  # 2. Apply to others
```

## Input Options

### --dry-run

All mutating commands support `--dry-run` to preview what would be executed:

```bash
lr develop set Exposure 1.0 --dry-run
# Returns: {"dry_run": true, "command": "develop.setValue", "risk_level": "write", "params": {...}}
```

### --json Input

```bash
lr develop set --json '{"parameter": "Exposure", "value": 1.0}'
echo '{"parameter": "Contrast", "value": 25}' | lr develop set --json-stdin
```

> **Limitation:** `--json` cannot bypass required Click positional arguments. Use it primarily for commands where all parameters are options.

## Output Formats

The CLI auto-detects TTY vs pipe: text in TTY, JSON in pipe. Override with `-o json|text|table`.

Use `--fields` (global option, before subcommand) to select specific fields. Dot notation filters nested arrays:
```bash
lr --fields Exposure,Contrast -o json develop get-settings
lr --fields photos.id -o json catalog find --rating 5
# → {"photos": [{"id": "123"}, {"id": "456"}]}
```

## Gotchas & Limitations

### Destructive commands (require `--confirm`)

| Command | Effect |
|---------|--------|
| `lr catalog remove-from-catalog PHOTO_ID --confirm` | Remove from catalog (not disk) |
| `lr develop ai reset --confirm` | Remove all masks from photo |

Omitting `--confirm` returns a structured error with the suggestion to add it.

### Values are absolute, not relative

`lr develop set Exposure 0.5` sets Exposure **to** 0.5, not +0.5 from current. To make relative changes: read current → compute → set. See "Relative value adjustment" workflow.

### No Undo/Redo

There is no undo command. **Always** run `lr develop snapshot "name"` before significant edits. To revert: `lr develop reset` and re-apply from the snapshot.

### Batch editing

For single-parameter batch edits across multiple photos, use `batch-set`:

```bash
lr develop batch-set --photo-ids 123,456,789 Exposure 0.5
```

For more complex batch edits (different parameters per photo), use the "Batch find + mutate" pattern: `find` → parse JSON → loop mutating commands per ID.

### Preset listing & search

```bash
lr -o json catalog develop-presets                    # List all presets (name + folder)
lr -o json catalog develop-presets --query "Portra"   # Search by preset name or folder name
```

Then apply: `lr develop preset "PRESET_NAME"`

### Collection photos

```bash
lr -o json catalog collections                           # List collections with IDs
lr -o json catalog collection-photos COLLECTION_ID       # Get photos from a collection
lr -o json catalog collection-photos 12345 --limit 100   # With pagination
```

### Other limitations

- **Preview = file path**: `lr preview generate` returns a file path on disk, not image data
- **Single connection**: Only one CLI session at a time
- **Out-of-range values**: Rejected with validation error. Use `lr develop range PARAM` to check

## Error Handling

Structured JSON errors with `code`, `message`, and `suggestions` fields:
```json
{"error": {"code": "VALIDATION_ERROR", "message": "...", "suggestions": ["..."]}}
```

### Exit code recovery playbook

| Exit Code | Meaning | Recovery |
|-----------|---------|----------|
| 0 | Success | — |
| 1 | General error | Read error message, adjust parameters |
| 2 | Validation error | Check `lr schema CMD` for valid params/types/ranges |
| 3 | Connection error | `lr system check-connection` → ensure Lightroom running → `lr system reconnect` |
| 4 | Timeout | Retry with `-t SECONDS` (default 30s; preview ops may need 120s+) |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LR_PORT_FILE` | Port file path | `/tmp/lightroom_ports.txt` |
| `LR_PLUGIN_DIR` | Lightroom Modules dir | Auto-detected |
| `LR_OUTPUT` | Default output format (`json`/`text`/`table`) | Auto-detect (TTY) |
| `LR_TIMEOUT` | Default timeout in seconds | `30` |
| `LR_FIELDS` | Default fields filter (comma-separated) | None |
| `LR_VERBOSE` | Enable verbose output (`1`/`true`) | Off |

## MCP Server (Claude Desktop / Cowork)

For non-CLI environments (Claude Desktop, Cowork), use the MCP Server:

1. `pip install lightroom-cli`
2. `lr mcp install`
3. Restart Claude Desktop / Cowork

MCP tool names use `lr_` prefix + snake_case (e.g., `lr_system_ping`, `lr_catalog_list`).
Parameters are identical to CLI. Use `dry_run=true` for mutating commands.

To check status: `lr mcp status`
To uninstall: `lr mcp uninstall`
