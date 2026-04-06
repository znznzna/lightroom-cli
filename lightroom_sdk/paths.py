"""
OS 横断のパス解決モジュール。
優先順位: 環境変数 > OS判定デフォルト

全OS: tempfile.gettempdir() を使用（Lightroom SDK の LrPathUtils.getStandardFilePath("temp") と一致）
macOS では /tmp ではなく /var/folders/... が実際のテンポラリディレクトリとなるため /tmp ハードコードは不可
"""

import os
import tempfile
from pathlib import Path

PLUGIN_NAME = "lightroom-cli-bridge.lrplugin"


def get_port_file() -> Path:
    env = os.environ.get("LR_PORT_FILE")
    if env:
        return Path(env)
    return Path(tempfile.gettempdir()) / "lightroom_ports.txt"


def get_lightroom_modules_dir() -> Path:
    import sys

    env = os.environ.get("LR_PLUGIN_DIR")
    if env:
        return Path(env)

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Adobe" / "Lightroom" / "Modules"
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "")
        return Path(appdata) / "Adobe" / "Lightroom" / "Modules"
    else:
        raise RuntimeError(
            "Unsupported platform for Lightroom Classic. Set LR_PLUGIN_DIR environment variable to override."
        )


def get_plugin_source_dir() -> Path:
    return Path(__file__).parent / "plugin"
