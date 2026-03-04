#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Lightroom CLI Installer ==="

# Python バージョン確認
PYTHON_VERSION=$(python3 --version 2>&1 | sed -n 's/Python \([0-9]*\.[0-9]*\).*/\1/p')
REQUIRED="3.10"
if [ "$(printf '%s\n' "$REQUIRED" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED" ]; then
    echo "Error: Python >= $REQUIRED required (found $PYTHON_VERSION)"
    exit 1
fi

# pip install -e .
echo "Installing lightroom-cli..."
cd "$PROJECT_DIR"
pip install -e ".[dev]"

# Lua プラグインのシンボリックリンク作成
"$SCRIPT_DIR/install-plugin.sh"

# セットアップ完了メッセージ
echo ""
echo "=== Setup Complete ==="
echo "Run 'lr system check-connection' to verify Lightroom connection."

# 接続テスト
python3 "$SCRIPT_DIR/check-connection.py" || true
