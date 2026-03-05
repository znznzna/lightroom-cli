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
| `lr catalog find --flag pick --rating 3` | Find photos by criteria (flag/rating/color/camera) |
| `lr catalog select PHOTO_ID [PHOTO_ID ...]` | Select photos by ID |
| `lr catalog find-by-path PATH` | Find photo by file path |
| `lr catalog folders [--recursive]` | List folders in catalog |
| `lr catalog set-flag PHOTO_ID pick\|reject\|none` | Set photo flag |
| `lr catalog get-flag PHOTO_ID` | Get photo flag status |
| `lr catalog set-caption PHOTO_ID "caption"` | Set photo caption |
| `lr catalog set-color-label PHOTO_ID COLOR` | Set color label (red/yellow/green/blue/purple/none) |
| `lr catalog batch-metadata PHOTO_ID [PHOTO_ID ...]` | Get formatted metadata for multiple photos |
| `lr catalog rotate-right` | Rotate photo right |
| `lr catalog set-metadata PHOTO_ID KEY VALUE` | Set arbitrary metadata |
| `lr catalog create-smart-collection "name" --search-desc JSON` | Create smart collection |
| `lr catalog create-collection-set "name"` | Create collection set |
| `lr catalog create-keyword "keyword"` | Create a keyword in catalog |
| `lr catalog remove-keyword PHOTO_ID keyword` | Remove keyword from photo |
| `lr catalog set-view-filter --filter JSON` | Set library view filter |
| `lr catalog get-view-filter` | Get current view filter |
| `lr catalog remove-from-catalog PHOTO_ID` | Remove photo from catalog (irreversible!) |

### develop — Image editing

| Command | Description |
|---------|-------------|
| `lr develop get-settings` | Get all develop settings |
| `lr develop set PARAM VALUE [PARAM VALUE ...]` | Set parameters |
| `lr develop get PARAM` | Get single parameter |
| `lr develop auto-tone` | Apply AutoTone |
| `lr develop auto-wb` | Apply Auto White Balance |
| `lr develop reset` | Reset to defaults |
| `lr develop apply --settings '{"Exposure": 1.0}'` | Apply JSON settings |
| `lr develop copy-settings` | Copy develop settings |
| `lr develop paste-settings` | Paste develop settings |
| `lr develop preset "name"` | Apply preset |
| `lr develop snapshot "name"` | Create snapshot |
| `lr develop range PARAM` | Get min/max range for parameter |
| `lr develop reset-param PARAM` | Reset single parameter to default |
| `lr develop process-version` | Get current process version |
| `lr develop set-process-version VERSION` | Set process version |
| `lr develop tool TOOL` | Select tool (loupe/crop/dust/redeye/gradient/circularGradient) |
| `lr develop edit-in-photoshop` | Edit selected photo in Photoshop |

#### Develop Parameters Reference

Use `lr develop range PARAM` to get the exact min/max for any parameter.

| Parameter | Range | Description |
|-----------|-------|-------------|
| Exposure | -5.0 to +5.0 | Overall brightness |
| Contrast | -100 to +100 | Tonal contrast |
| Highlights | -100 to +100 | Bright area recovery |
| Shadows | -100 to +100 | Shadow detail |
| Whites | -100 to +100 | White point |
| Blacks | -100 to +100 | Black point |
| Temperature | 2000 to 50000 | Color temperature (Kelvin) |
| Tint | -150 to +150 | Green/magenta tint |
| Vibrance | -100 to +100 | Subtle saturation |
| Saturation | -100 to +100 | Overall saturation |
| Clarity | -100 to +100 | Midtone contrast |
| Dehaze | -100 to +100 | Haze removal |
| Texture | -100 to +100 | Detail texture |
| Sharpness | 0 to 150 | Sharpening amount |
| LuminanceSmoothing | 0 to 100 | Luminance noise reduction |
| ColorNoiseReduction | 0 to 100 | Color noise reduction |
| VignetteAmount | -100 to +100 | Post-crop vignetting |
| SplitToningHighlightHue | 0 to 360 | Split tone highlight hue |
| SplitToningShadowHue | 0 to 360 | Split tone shadow hue |

> **Note:** Use the internal Lightroom parameter names exactly as shown.
> Get the full list dynamically: `lr develop debug probe`

#### Tone Curve

| Command | Description |
|---------|-------------|
| `lr develop curve get` | Get curve points |
| `lr develop curve set --points '[[0,0],[128,140],[255,255]]'` | Set curve |
| `lr develop curve s-curve` | Apply S-curve preset |
| `lr develop curve linear` | Reset to linear |
| `lr develop curve add-point X Y` | Add point |
| `lr develop curve remove-point INDEX` | Remove point from curve |

#### Masking (legacy)

> **Note:** Most masking operations have moved to `lr develop ai`. The `mask` subgroup is kept for low-level operations.

| Command | Description |
|---------|-------------|
| `lr develop mask list` | List all masks (deprecated — use `lr develop ai list`) |
| `lr develop mask selected` | Get currently selected mask |
| `lr develop mask go-to` | Go to masking view |
| `lr develop mask toggle-overlay` | Toggle mask overlay |

#### AI Masks

| Command | Description |
|---------|-------------|
| `lr develop ai subject` | Create AI subject mask |
| `lr develop ai sky` | Create AI sky mask |
| `lr develop ai background` | Create AI background mask |
| `lr develop ai objects` | Create AI objects mask |
| `lr develop ai people` | Create AI people mask |
| `lr develop ai landscape` | Create AI landscape mask |
| `lr develop ai list` | List all masks on current photo |
| `lr develop ai reset` | Remove all masks from current photo |
| `lr develop ai presets` | List available adjustment presets |
| `lr develop ai batch TYPE --photos ID1,ID2` | Apply AI mask to multiple photos |

#### Filters

| Command | Description |
|---------|-------------|
| `lr develop filter graduated` | Graduated filter |
| `lr develop filter radial` | Radial filter |
| `lr develop filter brush` | Brush filter |
| `lr develop filter range` | Range mask (luminance/color/depth) |

#### Local Adjustments

| Command | Description |
|---------|-------------|
| `lr develop local set PARAM VALUE` | Set local parameter |
| `lr develop local get PARAM` | Get local parameter |
| `lr develop local apply --settings JSON` | Apply multiple local adjustments |
| `lr develop local params` | List available local parameters |
| `lr develop local create-mask --tool TYPE` | Create mask with local adjustments |

#### Reset Commands

| Command | Description |
|---------|-------------|
| `lr develop reset-gradient` | Reset gradient filter |
| `lr develop reset-circular` | Reset circular gradient |
| `lr develop reset-brush` | Reset adjustment brush |
| `lr develop reset-masking` | Reset masking |
| `lr develop reset-crop` | Reset crop |
| `lr develop reset-transforms` | Reset transforms |
| `lr develop reset-spot` | Reset spot removal |
| `lr develop reset-redeye` | Reset red-eye removal |
| `lr develop reset-healing` | Reset healing |

#### Debug Commands

| Command | Description |
|---------|-------------|
| `lr develop debug dump` | Dump LrDevelopController info |
| `lr develop debug gradient-params` | Discover gradient parameters |
| `lr develop debug monitor --duration N` | Monitor parameter changes |
| `lr develop debug probe` | Probe all develop parameters |

#### Color Operations

| Command | Description |
|---------|-------------|
| `lr develop color green-swatch` | Create green color swatch |
| `lr develop color cyan-swatch` | Create cyan color swatch |
| `lr develop color enhance --preset natural\|vivid\|muted` | Enhance colors |

### preview — Image preview generation

| Command | Description |
|---------|-------------|
| `lr preview generate-current` | Generate preview for selected photo |
| `lr preview generate --size 2048` | Generate with size |
| `lr preview generate-batch` | Batch generate |
| `lr preview info PHOTO_ID` | Get preview info for a photo |

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
| `lr selection select-inverse` | Invert current selection |
| `lr selection increase-rating` | Increase rating by 1 |
| `lr selection decrease-rating` | Decrease rating by 1 |
| `lr selection toggle-label COLOR` | Toggle color label |
| `lr selection extend --direction left\|right --amount N` | Extend selection |
| `lr selection deselect-active` | Deselect active photo |
| `lr selection deselect-others` | Deselect all except active |

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
lr develop apply --settings '{"Exposure": 1.0, "Contrast": 25}'
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

## Schema Introspection

Use `lr schema` to discover available commands without reading documentation:

```bash
lr schema                      # List all command groups
lr schema develop              # List commands in develop group
lr schema develop.set          # Show command detail with parameters
```

## Output Formats

The CLI auto-detects TTY vs pipe and chooses the appropriate format:

- **TTY (interactive)**: Human-readable text output
- **Pipe / non-TTY**: JSON output (machine-readable, ideal for agents)

Override with `-o`:

```bash
lr -o json develop get-settings    # Force JSON
lr -o table catalog list           # Table format
lr develop get-settings            # Auto-detect (text in TTY, JSON in pipe)
```

### Field Filtering

Use `--fields` to select specific fields from the response:

```bash
lr --fields status,timestamp system ping    # Only return status and timestamp
lr --fields Exposure,Contrast develop get-settings
```

## Input Options

### --dry-run

All mutating commands support `--dry-run` to preview what would be executed:

```bash
lr develop set Exposure 1.0 --dry-run
lr catalog set-rating PHOTO_ID 5 --dry-run
```

### --json Input

Pass parameters as JSON instead of CLI arguments:

```bash
lr develop set --json '{"parameter": "Exposure", "value": 1.0}'
echo '{"parameter": "Contrast", "value": 25}' | lr develop set --json-stdin
```

> **Limitation:** `--json` / `--json-stdin` cannot bypass required Click arguments. For commands with required positional arguments (e.g., `lr catalog get-info PHOTO_ID`), you must provide the argument on the command line — passing it only via JSON will fail with a missing-argument error. Use `--json` primarily for commands where all parameters are options.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LR_PORT_FILE` | Port file path | `/tmp/lightroom_ports.txt` |
| `LR_PLUGIN_DIR` | Lightroom Modules dir | Auto-detected |
| `LR_OUTPUT` | Default output format (`json`/`text`/`table`) | Auto-detect (TTY) |
| `LR_TIMEOUT` | Default timeout in seconds | `30` |
| `LR_FIELDS` | Default fields filter (comma-separated) | None |
| `LR_VERBOSE` | Enable verbose output (`1`/`true`) | Off |

## Error Handling

- **Structured errors**: JSON errors with `code`, `message`, and `suggestions` fields
- **Exit codes**: 0=success, 1=general error, 2=validation error, 3=connection error, 4=timeout
- Connection errors: The CLI auto-retries with exponential backoff
- Timeout: Use `-t SECONDS` to increase timeout for slow operations
- Plugin not running: `lr system check-connection` for diagnostics
