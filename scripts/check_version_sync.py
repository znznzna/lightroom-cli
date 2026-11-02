#!/usr/bin/env python3
"""Check that all version files match pyproject.toml."""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

DEFAULT_ROOT = Path(__file__).resolve().parent.parent


def read_pyproject_version(root: Path) -> str:
    with open(root / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def read_init_py_version(root: Path) -> str | None:
    m = re.search(r'__version__\s*=\s*"([^"]*)"', (root / "lightroom_sdk" / "__init__.py").read_text())
    return m.group(1) if m else None


def read_plugin_init_lua_version(root: Path) -> str | None:
    m = re.search(r'version\s*=\s*"([^"]*)"', (root / "lightroom_sdk" / "plugin" / "PluginInit.lua").read_text())
    return m.group(1) if m else None


def read_info_lua_version(root: Path) -> str | None:
    content = (root / "lightroom_sdk" / "plugin" / "Info.lua").read_text()
    m = re.search(r"VERSION\s*=\s*\{\s*major=(\d+),\s*minor=(\d+),\s*revision=(\d+)", content)
    if m:
        return f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
    return None


def read_claude_plugin_versions(root: Path) -> dict[str, str | None]:
    results = {}
    marketplace = root / ".claude-plugin" / "marketplace.json"
    if marketplace.exists():
        data = json.loads(marketplace.read_text())
        for plugin in data.get("plugins", []):
            results[".claude-plugin/marketplace.json"] = plugin.get("version")
            break
    for rel in (".claude-plugin/plugin.json", "plugin/.claude-plugin/plugin.json"):
        path = root / rel
        if path.exists():
            results[rel] = json.loads(path.read_text()).get("version")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="repository root (default: this checkout)")
    root = parser.parse_args(argv).root

    source = read_pyproject_version(root)
    checks = {
        "lightroom_sdk/__init__.py": read_init_py_version(root),
        "lightroom_sdk/plugin/PluginInit.lua": read_plugin_init_lua_version(root),
        "lightroom_sdk/plugin/Info.lua": read_info_lua_version(root),
        **read_claude_plugin_versions(root),
    }

    mismatches = [(file, version) for file, version in checks.items() if version != source]

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
