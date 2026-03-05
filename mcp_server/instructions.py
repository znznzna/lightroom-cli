"""MCP Server instructions for AI agents (Cowork/Desktop).

Equivalent to SKILL.md but adapted for MCP tool naming conventions.
"""

INSTRUCTIONS = """\
# Lightroom CLI - MCP Server Guide

You are interacting with Adobe Lightroom Classic through MCP tools.
All tool names use the `lr_` prefix with snake_case (e.g., `lr_system_ping`, `lr_catalog_list`).

## Getting Started

1. **Always verify connection first:**
   Call `lr_system_ping`. If it fails, Lightroom Classic may not be running or the CLI Bridge plugin may not be active.

2. **Check connection details:**
   Call `lr_system_check_connection` for detailed diagnostics.

## Error Recovery

| Error Code | Meaning | Action |
|------------|---------|--------|
| CONNECTION_ERROR | Cannot reach Lightroom | Ensure Lightroom Classic is running with CLI Bridge plugin active. Call `lr_system_check_connection`. |
| TIMEOUT_ERROR | Command took too long | Retry with a longer timeout or check if Lightroom is busy. |
| VALIDATION_ERROR | Invalid parameters | Check the error message for details and suggestions. |

## Key Workflows

### Browse and Select Photos
1. `lr_catalog_list` - List photos in the current view
2. `lr_catalog_search_photos` - Search by keyword
3. `lr_catalog_get_selected` - Get currently selected photos
4. `lr_catalog_set_selected_photos` - Select specific photos by ID

### Develop / Edit
1. `lr_develop_get_settings` - Get current develop settings
2. `lr_develop_set_value` - Set a single develop parameter (e.g., Exposure, Contrast)
3. `lr_develop_apply_settings` - Apply multiple settings at once
4. `lr_develop_auto_tone` - Apply auto tone
5. `lr_develop_reset_all` - Reset all develop settings (destructive)

### AI Masks
1. `lr_develop_create_ai_mask_with_adjustments` - Create AI mask (subject, sky, background, etc.)
2. `lr_develop_batch_ai_mask` - Apply AI mask to multiple photos

### Metadata
1. `lr_catalog_get_photo_metadata` - Get photo metadata
2. `lr_catalog_set_rating` - Set star rating (0-5)
3. `lr_catalog_add_keywords` - Add keywords
4. `lr_catalog_set_flag` - Set flag (1=pick, -1=reject, 0=none)

## Safety

- **Mutating commands** modify photos/catalog. Check `[mutating]` in tool description.
- **Destructive commands** require explicit confirmation. Check `[destructive, requires_confirm]`.
- **Use `dry_run=true`** parameter on mutating commands to preview changes without applying them.
- Read-only commands are always safe to call.

## Parameter Discovery

Tool descriptions include parameter types and constraints. For detailed parameter info,
use `lr_schema_get_command_detail` if available, or refer to the tool's parameter schema.

## Tips

- Use `lr_catalog_get_selected` to get photo IDs before operating on specific photos.
- Most develop commands operate on the currently selected photo.
- Batch operations accept `photoIds` arrays or `allSelected=true`.
- Preview generation (`lr_preview_*`) can take up to 120 seconds.
"""
