"""バージョン同期スクリプトのテスト

同期スクリプトは一時ディレクトリに作った最小のリポの中で動かす（本物の checkout は書き換えない）。
本物の checkout が同期済みかどうかは、検査スクリプトだけで確かめる。
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SYNC = ROOT / "scripts" / "sync_version.py"
CHECK = ROOT / "scripts" / "check_version_sync.py"

VERSION_FILES = [
    "pyproject.toml",
    "lightroom_sdk/__init__.py",
    "lightroom_sdk/plugin/PluginInit.lua",
    "lightroom_sdk/plugin/Info.lua",
    ".claude-plugin/marketplace.json",
    ".claude-plugin/plugin.json",
    "plugin/.claude-plugin/plugin.json",
]
NEW_VERSION = "9.8.7"


def _run(script: Path, root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), "--root", str(root)], capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """版を持つファイルだけを写した一時リポ。pyproject.toml だけ NEW_VERSION に上げてある"""
    for rel in VERSION_FILES:
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, dst)
    pyproject = tmp_path / "pyproject.toml"
    content = pyproject.read_bytes()
    bumped = re.sub(rb'(?m)^version\s*=\s*"[^"]*"', b'version = "' + NEW_VERSION.encode() + b'"', content, count=1)
    assert bumped != content
    pyproject.write_bytes(bumped)
    return tmp_path


def test_real_checkout_is_in_sync():
    """リポのバージョンファイルが pyproject.toml と揃っていること（読むだけ）"""
    result = subprocess.run([sys.executable, str(CHECK)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout
    assert "All versions in sync" in result.stdout


def test_check_detects_mismatch(repo):
    """不一致がある場合 exit code 1 + 不一致箇所の出力"""
    result = _run(CHECK, repo)
    assert result.returncode == 1
    assert "mismatch" in result.stdout.lower()
    for rel in VERSION_FILES[1:]:
        assert rel in result.stdout


def test_sync_updates_all_files(repo):
    result = _run(SYNC, repo)
    assert result.returncode == 0, result.stderr

    assert f'__version__ = "{NEW_VERSION}"' in (repo / "lightroom_sdk/__init__.py").read_text()
    assert f'version = "{NEW_VERSION}"' in (repo / "lightroom_sdk/plugin/PluginInit.lua").read_text()
    info = (repo / "lightroom_sdk/plugin/Info.lua").read_text()
    m = re.search(r"VERSION\s*=\s*\{\s*major=(\d+),\s*minor=(\d+),\s*revision=(\d+)", info)
    assert m is not None
    assert ".".join(m.groups()) == NEW_VERSION
    marketplace = json.loads((repo / ".claude-plugin/marketplace.json").read_text())
    assert marketplace["plugins"][0]["version"] == NEW_VERSION
    assert json.loads((repo / ".claude-plugin/plugin.json").read_text())["version"] == NEW_VERSION
    assert json.loads((repo / "plugin/.claude-plugin/plugin.json").read_text())["version"] == NEW_VERSION

    check = _run(CHECK, repo)
    assert check.returncode == 0, check.stdout
    assert "All versions in sync" in check.stdout


def test_sync_changes_only_the_version(repo):
    """改行コード（CRLF/LF）と整形を保ち、版の値以外は変えないこと"""
    before = {rel: (repo / rel).read_bytes() for rel in VERSION_FILES[1:]}
    assert _run(SYNC, repo).returncode == 0
    for rel, old in before.items():
        new = (repo / rel).read_bytes()
        assert new.count(b"\r\n") == old.count(b"\r\n"), rel
        assert new.count(b"\n") == old.count(b"\n"), rel
        old_lines = old.splitlines()
        new_lines = new.splitlines()
        changed = [i for i, (a, b) in enumerate(zip(old_lines, new_lines)) if a != b]
        assert len(changed) == 1, (rel, changed)
        assert NEW_VERSION.encode() in new_lines[changed[0]] or b"major=9" in new_lines[changed[0]]


def test_sync_is_idempotent(repo):
    assert _run(SYNC, repo).returncode == 0
    snapshot = {rel: (repo / rel).read_bytes() for rel in VERSION_FILES}
    second = _run(SYNC, repo)
    assert second.returncode == 0
    assert "All files already in sync" in second.stdout
    assert {rel: (repo / rel).read_bytes() for rel in VERSION_FILES} == snapshot
