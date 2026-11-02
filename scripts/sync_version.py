#!/usr/bin/env python3
"""Sync version from pyproject.toml to all version files."""

import argparse
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_PLUGIN_JSON_FILES = (
    ".claude-plugin/marketplace.json",
    ".claude-plugin/plugin.json",
    "plugin/.claude-plugin/plugin.json",
)


def _read(path: Path) -> str:
    # newline="" keeps CRLF files as CRLF when written back
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def _write(path: Path, content: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)


def read_pyproject_version(root: Path) -> str:
    with open(root / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def _sub_file(root: Path, rel: str, pattern: str, repl: str, count: int = 0) -> bool:
    path = root / rel
    content = _read(path)
    new_content = re.sub(pattern, repl, content, count=count)
    if content != new_content:
        _write(path, new_content)
        print(f"Updated: {rel}")
        return True
    return False


def sync_init_py(root: Path, version: str) -> bool:
    return _sub_file(root, "lightroom_sdk/__init__.py", r'__version__\s*=\s*"[^"]*"', f'__version__ = "{version}"')


def sync_plugin_init_lua(root: Path, version: str) -> bool:
    return _sub_file(
        root, "lightroom_sdk/plugin/PluginInit.lua", r'version\s*=\s*"[^"]*"', f'version = "{version}"', count=1
    )


def sync_info_lua(root: Path, version: str) -> bool:
    parts = version.split(".")
    major = parts[0] if len(parts) > 0 else "0"
    minor = parts[1] if len(parts) > 1 else "0"
    revision = parts[2] if len(parts) > 2 else "0"
    return _sub_file(
        root,
        "lightroom_sdk/plugin/Info.lua",
        r"VERSION\s*=\s*\{[^}]+\}",
        f"VERSION = {{ major={major}, minor={minor}, revision={revision}, build=1 }}",
    )


def sync_claude_plugin_json(root: Path, version: str) -> bool:
    changed = False
    for rel in CLAUDE_PLUGIN_JSON_FILES:
        if (root / rel).exists():
            # Replace the value in place so formatting and line endings stay as they are
            changed |= _sub_file(root, rel, r'("version"\s*:\s*)"[^"]*"', rf'\g<1>"{version}"')
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="repository root (default: this checkout)")
    root = parser.parse_args(argv).root

    version = read_pyproject_version(root)
    print(f"Source version (pyproject.toml): {version}")

    changed = False
    changed |= sync_init_py(root, version)
    changed |= sync_plugin_init_lua(root, version)
    changed |= sync_info_lua(root, version)
    changed |= sync_claude_plugin_json(root, version)

    if not changed:
        print("All files already in sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
