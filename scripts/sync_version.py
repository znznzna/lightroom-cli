#!/usr/bin/env python3
"""Sync version from pyproject.toml to all version files."""

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


def sync_init_py(version: str) -> bool:
    path = ROOT / "lightroom_sdk" / "__init__.py"
    content = path.read_text()
    new_content = re.sub(r'__version__\s*=\s*"[^"]*"', f'__version__ = "{version}"', content)
    if content != new_content:
        path.write_text(new_content)
        print(f"Updated: {path.relative_to(ROOT)}")
        return True
    return False


def sync_plugin_init_lua(version: str) -> bool:
    path = ROOT / "lightroom_sdk" / "plugin" / "PluginInit.lua"
    content = path.read_text()
    new_content = re.sub(r'version\s*=\s*"[^"]*"', f'version = "{version}"', content, count=1)
    if content != new_content:
        path.write_text(new_content)
        print(f"Updated: {path.relative_to(ROOT)}")
        return True
    return False


def sync_info_lua(version: str) -> bool:
    path = ROOT / "lightroom_sdk" / "plugin" / "Info.lua"
    parts = version.split(".")
    major = parts[0] if len(parts) > 0 else "0"
    minor = parts[1] if len(parts) > 1 else "0"
    revision = parts[2] if len(parts) > 2 else "0"

    content = path.read_text()
    new_content = re.sub(
        r"VERSION\s*=\s*\{[^}]+\}",
        f"VERSION = {{ major={major}, minor={minor}, revision={revision}, build=1 }}",
        content,
    )
    if content != new_content:
        path.write_text(new_content)
        print(f"Updated: {path.relative_to(ROOT)}")
        return True
    return False


def main() -> int:
    version = read_pyproject_version()
    print(f"Source version (pyproject.toml): {version}")

    changed = False
    changed |= sync_init_py(version)
    changed |= sync_plugin_init_lua(version)
    changed |= sync_info_lua(version)

    if not changed:
        print("All files already in sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
