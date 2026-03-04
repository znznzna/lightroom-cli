# Lightroom CLI Skills for Claude Code

## Prerequisites

- lightroom-cli installed (`lr --version` to verify)
- Lightroom Classic running with plugin active
- Connection verified (`lr system check-connection`)

## Available Modules

### system — Connection & status

| Command | Description |
|---------|-------------|
| `lr system ping` | Quick connectivity test |
| `lr system status` | Plugin status and uptime |
| `lr system check-connection` | Detailed connection check |
| `lr system reconnect` | Force reconnection |

### catalog — Photo management

| Command | Description |
|---------|-------------|
| `lr catalog get-selected` | Get currently selected photos |
| `lr catalog list --limit N` | List photos |
| `lr catalog search "keyword"` | Search photos by keyword |
| `lr catalog get-info PHOTO_ID` | Get detailed metadata |
| `lr catalog set-rating PHOTO_ID N` | Set star rating (0-5) |
| `lr catalog add-keywords PHOTO_ID kw1 kw2` | Add keywords |
| `lr catalog set-title PHOTO_ID "title"` | Set title |
| `lr catalog collections` | List collections |
| `lr catalog create-collection "name"` | Create collection |
| `lr catalog keywords` | List all keywords |
| `lr catalog rotate-left` | Rotate photo left |
| `lr catalog create-virtual-copy` | Create virtual copy |

### develop — Image editing

| Command | Description |
|---------|-------------|
| `lr develop get-settings` | Get all develop settings |
| `lr develop set PARAM VALUE [PARAM VALUE ...]` | Set parameters |
| `lr develop get PARAM` | Get single parameter |
| `lr develop auto-tone` | Apply AutoTone |
| `lr develop auto-wb` | Apply Auto White Balance |
| `lr develop reset` | Reset to defaults |
| `lr develop apply '{"Exposure": 1.0}'` | Apply JSON settings |
| `lr develop copy-settings` | Copy develop settings |
| `lr develop paste-settings` | Paste develop settings |
| `lr develop preset "name"` | Apply preset |
| `lr develop snapshot "name"` | Create snapshot |

#### Tone Curve

| Command | Description |
|---------|-------------|
| `lr develop curve get` | Get curve points |
| `lr develop curve set '[[0,0],[128,140],[255,255]]'` | Set curve |
| `lr develop curve s-curve` | Apply S-curve preset |
| `lr develop curve linear` | Reset to linear |
| `lr develop curve add-point X Y` | Add point |

#### Masking

| Command | Description |
|---------|-------------|
| `lr develop mask list` | List all masks |
| `lr develop mask create` | Create new mask |
| `lr develop mask add brush` | Add brush to mask |
| `lr develop mask intersect luminance` | Intersect mask |
| `lr develop mask subtract color` | Subtract from mask |
| `lr develop mask invert MASK_ID` | Invert mask |

#### Filters

| Command | Description |
|---------|-------------|
| `lr develop filter graduated` | Graduated filter |
| `lr develop filter radial` | Radial filter |
| `lr develop filter brush` | Brush filter |
| `lr develop filter ai-select` | AI selection |

#### Local Adjustments

| Command | Description |
|---------|-------------|
| `lr develop local set PARAM VALUE` | Set local parameter |
| `lr develop local get PARAM` | Get local parameter |

### preview — Image preview generation

| Command | Description |
|---------|-------------|
| `lr preview generate-current` | Generate preview for selected photo |
| `lr preview generate --size 2048` | Generate with size |
| `lr preview generate-batch` | Batch generate |
| `lr preview info` | Get preview info |

### selection — Navigation & flagging

| Command | Description |
|---------|-------------|
| `lr selection flag` | Set Pick flag |
| `lr selection reject` | Set Reject flag |
| `lr selection unflag` | Remove flag |
| `lr selection get-flag` | Get flag status |
| `lr selection set-rating N` | Set rating (0-5) |
| `lr selection get-rating` | Get rating |
| `lr selection color-label COLOR` | Set color label |
| `lr selection get-color-label` | Get color label |
| `lr selection next` | Next photo |
| `lr selection previous` | Previous photo |
| `lr selection select-all` | Select all |
| `lr selection select-none` | Deselect all |

### plugin — Plugin management

| Command | Description |
|---------|-------------|
| `lr plugin install` | Install plugin (copy) |
| `lr plugin install --dev` | Install plugin (symlink) |
| `lr plugin uninstall` | Remove plugin |
| `lr plugin status` | Check install status |

## Common Workflows

### Batch rate photos by content analysis

```bash
# 1. Get selected photos
lr -o json catalog get-selected

# 2. For each photo, generate preview for analysis
lr preview generate-current

# 3. Set rating based on analysis
lr catalog set-rating PHOTO_ID 5
```

### Apply consistent edits across photos

```bash
# 1. Get settings from reference photo
lr -o json develop get-settings

# 2. Apply to target photos
lr develop apply '{"Exposure": 1.0, "Contrast": 25}'
```

### Organize photos with keywords and collections

```bash
# 1. Search for photos
lr -o json catalog search "sunset"

# 2. Add keywords
lr catalog add-keywords PHOTO_ID sunset landscape golden-hour

# 3. Create and populate collection
lr catalog create-collection "Best Sunsets"
```

### Quick culling workflow

```bash
# Navigate and rate
lr selection next
lr selection set-rating 3
lr selection next
lr selection reject
lr selection next
lr selection flag
```

## Output Formats

All commands support `-o json` for machine-readable output:

```bash
lr -o json develop get-settings    # Full JSON
lr -o table catalog list           # Table format
lr develop get-settings            # Human-readable text
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LR_PORT_FILE` | Port file path | `/tmp/lightroom_ports.txt` |
| `LR_PLUGIN_DIR` | Lightroom Modules dir | Auto-detected |

## Error Handling

- Connection errors: The CLI auto-retries with exponential backoff
- Timeout: Use `-t SECONDS` to increase timeout for slow operations
- Plugin not running: `lr system check-connection` for diagnostics
