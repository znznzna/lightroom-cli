# Environment Variables & MCP Server Reference

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
