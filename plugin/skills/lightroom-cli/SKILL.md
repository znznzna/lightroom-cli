---
name: lightroom-cli
description: |
  Control Adobe Lightroom Classic via CLI. Use when the user wants to interact
  with Lightroom — adjust develop settings, manage catalog, navigate photos,
  apply presets, or automate photo workflows. Triggers: "Lightroomで",
  "現像設定を", "写真を編集", "カタログから", "lr コマンド", "プリセットを適用",
  "写真の露出", "ホワイトバランス", "プレビュー生成", "写真を検索".
  Do NOT use for general image editing unrelated to Lightroom Classic.
---

# Lightroom CLI Skills for Claude Code (v1.2.0+)

## Agent Quick Contract

1. **Always use `-o json`** (or pipe) for machine-readable output
2. **Always use `--fields`** to limit response size: `lr --fields id,filename catalog list`
3. **Check `lr schema CMD`** for parameter types and ranges before calling
4. **Use `--dry-run`** before mutating commands to preview changes
5. **Exit codes matter**: 0=ok, 2=validation, 3=connection, 4=timeout
6. **`requires_confirm` commands** need `--confirm` flag (see Destructive Commands below)

## Prerequisites

- lightroom-cli installed (`lr --version` to verify)
- Lightroom Classic running with plugin active
- Connection verified (`lr system check-connection`)

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

Basic: `--rating`, `--rating-op`, `--flag`, `--color-label`, `--camera`
Extended (v1.2.0): `--folder-path`, `--capture-date-from/to`, `--file-format`, `--keyword`, `--filename`

Full examples and notes → `references/catalog-find-filters.md`

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

### Recommended `--fields` patterns

| Use case | Recommended fields |
|----------|-------------------|
| Photo listing / search | `--fields id,filename,rating` |
| Photo detail | `--fields id,filename,rating,colorLabel,flag,keywords` |
| Develop settings overview | `--fields Exposure,Contrast,Highlights,Shadows,Whites,Blacks` |
| Color grading | `--fields Temperature,Tint,Vibrance,Saturation` |
| Tone curve | `--fields ToneCurve,ToneCurvePV2012` |
| Batch find (ID only) | `--fields photos.id` |

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

## Environment Variables & MCP Server

Environment variables (`LR_PORT_FILE`, `LR_OUTPUT`, `LR_TIMEOUT`, etc.) and MCP Server setup → `references/environment-and-mcp.md`

## Troubleshooting

### Connection issues

| Symptom | Cause | Recovery |
|---------|-------|----------|
| Exit code 3 / "Connection refused" | Lightroom not running or plugin disabled | 1. Verify Lightroom is running → 2. File > Plug-in Manager: check "Lightroom CLI Bridge" is enabled → 3. `lr system reconnect` |
| "Port file not found" | Port file not generated | 1. Restart Lightroom → 2. Confirm plugin shows "Start CLI Bridge" → 3. `ls /tmp/lightroom_ports.txt` to verify |
| "Connection timeout" after reconnect | Stale port info | 1. `rm /tmp/lightroom_ports.txt` → 2. In Lightroom: Stop plugin → Start plugin → 3. `lr system check-connection` |
| "Already connected" error | Another session is connected | 1. Check if `lr` is running in another terminal → 2. `lr system reconnect --force` |

### Plugin issues

| Symptom | Cause | Recovery |
|---------|-------|----------|
| Plugin not shown in Plug-in Manager | Wrong install path | 1. `lr plugin status` to check path → 2. `lr plugin install` to reinstall → 3. Restart Lightroom |
| "Plugin is disabled" | Lightroom disabled it | File > Plug-in Manager → click "Enable" → `lr system check-connection` |

### Command issues

| Symptom | Cause | Recovery |
|---------|-------|----------|
| Exit code 2 / "VALIDATION_ERROR" | Invalid parameters | Check `lr schema CMD` for correct types/ranges → `lr develop range PARAM` for value bounds |
| Exit code 4 / Timeout | Heavy operation | Add `-t 120` to extend timeout (preview ops need 120s+) |
| "No photo selected" | No target photo | `lr catalog select PHOTO_ID` first, then retry |
