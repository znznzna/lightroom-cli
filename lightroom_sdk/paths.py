"""
OS 横断のパス解決モジュール。
優先順位: 環境変数 > OS判定デフォルト

Windows 分岐は将来対応の布石として含むが、テストは macOS/Linux のみ。
"""

import os
import sys
from pathlib import Path

PLUGIN_NAME = "lightroom-cli-bridge.lrplugin"


def get_port_file() -> Path:
    env = os.environ.get("LR_PORT_FILE")
    if env:
        return Path(env)

    if sys.platform == "win32":
        return Path(os.environ.get("TEMP", r"C:\Temp")) / "lightroom_ports.txt"
    else:
        return Path("/tmp/lightroom_ports.txt")


def get_lightroom_modules_dir() -> Path:
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
    repo_dir = Path(__file__).parent.parent / "lightroom-plugin"
    if repo_dir.exists():
        return repo_dir

    import importlib.resources as pkg_resources

    return Path(str(pkg_resources.files("lightroom_cli_plugin")))
