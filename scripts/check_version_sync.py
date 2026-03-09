#!/usr/bin/env python3
"""Check that all version files match pyproject.toml."""

import json
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parent.parent


def read_pyproject_version() -> str:
    with open(ROOT / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def read_init_py_version() -> str | None:
    path = ROOT / "lightroom_sdk" / "__init__.py"
    m = re.search(r'__version__\s*=\s*"([^"]*)"', path.read_text())
    return m.group(1) if m else None


def read_plugin_init_lua_version() -> str | None:
    path = ROOT / "lightroom_sdk" / "plugin" / "PluginInit.lua"
    m = re.search(r'version\s*=\s*"([^"]*)"', path.read_text())
    return m.group(1) if m else None


def read_info_lua_version() -> str | None:
    path = ROOT / "lightroom_sdk" / "plugin" / "Info.lua"
    m = re.search(r"VERSION\s*=\s*\{\s*major=(\d+),\s*minor=(\d+),\s*revision=(\d+)", path.read_text())
    if m:
        return f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
    return None


def read_claude_plugin_versions() -> dict[str, str | None]:
    results = {}
    marketplace = ROOT / ".claude-plugin" / "marketplace.json"
    if marketplace.exists():
        data = json.loads(marketplace.read_text())
        for plugin in data.get("plugins", []):
            results[".claude-plugin/marketplace.json"] = plugin.get("version")
            break
    plugin_json = ROOT / "plugin" / ".claude-plugin" / "plugin.json"
    if plugin_json.exists():
        data = json.loads(plugin_json.read_text())
        results["plugin/.claude-plugin/plugin.json"] = data.get("version")
    return results


def main() -> int:
    source = read_pyproject_version()
    checks = {
        "lightroom_sdk/__init__.py": read_init_py_version(),
        "lightroom_sdk/plugin/PluginInit.lua": read_plugin_init_lua_version(),
        "lightroom_sdk/plugin/Info.lua": read_info_lua_version(),
        **read_claude_plugin_versions(),
    }

    mismatches = []
    for file, version in checks.items():
        if version != source:
            mismatches.append((file, version))

    if mismatches:
        print(f"Version mismatch! Source (pyproject.toml): {source}")
        for file, version in mismatches:
            print(f"  {file}: {version or 'NOT FOUND'}")
        print("\nRun: python scripts/sync_version.py")
        return 1

    print(f"All versions in sync: {source}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
