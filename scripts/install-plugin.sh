#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PLUGIN_SRC="$PROJECT_DIR/lightroom-plugin"
LR_MODULES="$HOME/Library/Application Support/Adobe/Lightroom/Modules"
PLUGIN_DEST="$LR_MODULES/lightroom-python-bridge.lrdevplugin"

if [ ! -d "$PLUGIN_SRC" ]; then
    echo "Error: Plugin source not found at $PLUGIN_SRC"
    exit 1
fi

mkdir -p "$LR_MODULES"

if [ -L "$PLUGIN_DEST" ] || [ -e "$PLUGIN_DEST" ]; then
    echo "Plugin already exists at $PLUGIN_DEST"
    echo "Remove it first if you want to reinstall."
    exit 0
fi

ln -s "$PLUGIN_SRC" "$PLUGIN_DEST"
echo "Plugin symlinked: $PLUGIN_DEST -> $PLUGIN_SRC"
