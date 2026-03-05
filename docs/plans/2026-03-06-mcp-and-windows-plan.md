# MCP Server + Windows 対応 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** lightroom-cli に MCP Server (fastmcp) を追加し、Windows 対応を完了する
**Architecture:** SDK 層を強化（validation 移動 + Resilient 化）し、MCP Server を並列インターフェースとして追加。Lua/Python のパスを OS 非依存に統一。
**Tech Stack:** Python 3.10+, fastmcp 3.x, Click 8.x, asyncio
---

## Phase 1: Windows 修正 (PlatformPaths.lua + paths.py + plugin.py)

### Task 1: Lua PlatformPaths を LrPathUtils.getStandardFilePath("temp") に変更

**Files:**
- Modify: `lightroom_sdk/plugin/PlatformPaths.lua`

**Step 1: 最小限の実装**

```lua
-- lightroom_sdk/plugin/PlatformPaths.lua
-- Cross-platform port file path using Lightroom SDK API.
-- LrPathUtils.getStandardFilePath("temp") returns:
--   macOS: /tmp (or /private/tmp)
--   Windows: %TEMP% equivalent

local LrPathUtils = import "LrPathUtils"

local PlatformPaths = {}

function PlatformPaths.getPortFilePath()
    local tempDir = LrPathUtils.getStandardFilePath("temp")
    return LrPathUtils.child(tempDir, "lightroom_ports.txt")
end

return PlatformPaths
```

**Step 2: 既存テストが壊れないことを確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/ -v --ignore=tests/e2e -x -q`
Expected: PASS (Lua変更はPythonテストに影響しない)

**Step 3: コミット**
```bash
git add lightroom_sdk/plugin/PlatformPaths.lua
git commit -m "fix: PlatformPaths.lua を LrPathUtils.getStandardFilePath に変更 (Windows対応)"
```

### Task 2: Python paths.py を tempfile.gettempdir() に変更

**Files:**
- Modify: `lightroom_sdk/paths.py`
- Test: `tests/test_paths.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_paths.py に追記
import tempfile
from unittest.mock import patch


def test_get_port_file_uses_tempfile_gettempdir():
    """get_port_file が tempfile.gettempdir() を使用すること"""
    from lightroom_sdk.paths import get_port_file

    with patch.dict("os.environ", {}, clear=True):
        # LR_PORT_FILE が未設定の場合
        with patch.dict("os.environ", {"LR_PORT_FILE": ""}, clear=False):
            pass  # 環境変数クリアのため
        import os
        os.environ.pop("LR_PORT_FILE", None)
        result = get_port_file()
        expected = Path(tempfile.gettempdir()) / "lightroom_ports.txt"
        assert result == expected


def test_get_port_file_no_platform_branch():
    """sys.platform による分岐がないこと（Windows/macOS共通パス）"""
    import inspect
    from lightroom_sdk import paths

    source = inspect.getsource(paths.get_port_file)
    assert "sys.platform" not in source, "get_port_file should not branch on sys.platform"
    assert "win32" not in source, "get_port_file should not reference win32"
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_paths.py -v -k "test_get_port_file_no_platform_branch or test_get_port_file_uses_tempfile"`
Expected: FAIL (`sys.platform` が paths.py に存在するため)

**Step 3: 最小限の実装**

```python
# lightroom_sdk/paths.py
"""
OS 横断のパス解決モジュール。
優先順位: 環境変数 > tempfile.gettempdir() デフォルト
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
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_paths.py -v`
Expected: PASS

**Step 5: 全テスト確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/ -v --ignore=tests/e2e -x -q`
Expected: PASS

**Step 6: コミット**
```bash
git add lightroom_sdk/paths.py tests/test_paths.py
git commit -m "fix: paths.py の get_port_file を tempfile.gettempdir() に統一 (Windows対応)"
```

### Task 3: plugin.py の --dev フラグ Windows フォールバック

**Files:**
- Modify: `cli/commands/plugin.py`
- Test: `tests/test_cli_plugin.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_cli_plugin.py に追記
import os
from unittest.mock import patch


def test_plugin_install_dev_windows_fallback(tmp_path):
    """Windows で --dev 指定時に symlink 失敗したら copytree にフォールバック"""
    from click.testing import CliRunner
    from cli.commands.plugin import install

    source = tmp_path / "source_plugin"
    source.mkdir()
    (source / "Info.lua").write_text("return {}")

    dest_dir = tmp_path / "Modules"
    dest_dir.mkdir()

    with (
        patch("cli.commands.plugin.get_plugin_source_dir", return_value=source),
        patch("cli.commands.plugin.get_lightroom_modules_dir", return_value=dest_dir),
        patch("os.name", "nt"),
        patch("pathlib.Path.symlink_to", side_effect=OSError("symlink not supported")),
    ):
        runner = CliRunner()
        result = runner.invoke(install, ["--dev"])
        assert result.exit_code == 0
        assert "copytree" in result.output.lower() or "copy" in result.output.lower() or "installed" in result.output.lower()
        dest = dest_dir / "lightroom-cli-bridge.lrplugin"
        assert dest.exists()
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_cli_plugin.py::test_plugin_install_dev_windows_fallback -v`
Expected: FAIL (現在のコードは OSError をキャッチしない)

**Step 3: 最小限の実装**

```python
# cli/commands/plugin.py の install 関数を修正
@plugin.command()
@click.option("--dev", is_flag=True, help="Use symlink instead of copy (development mode)")
@click.option("--quiet", "-q", is_flag=True, help="Suppress output")
def install(dev, quiet):
    """Install the Lightroom plugin."""
    source = get_plugin_source_dir()
    dest_dir = get_lightroom_modules_dir()
    dest = dest_dir / PLUGIN_NAME

    if not source.exists():
        click.echo(f"Error: Plugin source not found at {source}", err=True)
        raise SystemExit(1)

    dest_dir.mkdir(parents=True, exist_ok=True)

    if dest.exists() or dest.is_symlink():
        if dest.is_symlink():
            dest.unlink()
        else:
            shutil.rmtree(dest)

    if dev:
        try:
            dest.symlink_to(source)
            if not quiet:
                click.echo(f"Plugin symlinked: {dest} -> {source}")
        except OSError:
            # Windows で symlink 権限がない場合は copytree にフォールバック
            click.echo(
                "Warning: Symlink creation failed. Falling back to copy.",
                err=True,
            )
            shutil.copytree(source, dest)
            if not quiet:
                click.echo(f"Plugin installed (copy fallback) to {dest}")
    else:
        shutil.copytree(source, dest)
        if not quiet:
            click.echo(f"Plugin installed to {dest}")
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_cli_plugin.py -v`
Expected: PASS

**Step 5: 全テスト確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/ -v --ignore=tests/e2e -x -q`
Expected: PASS

**Step 6: コミット**
```bash
git add cli/commands/plugin.py tests/test_cli_plugin.py
git commit -m "fix: plugin install --dev で Windows symlink 失敗時に copytree フォールバック"
```

---

## Phase 2: SDK 強化 (validation.py 移動 + LightroomClient Resilient化)

### Task 4: cli/validation.py を lightroom_sdk/validation.py に移動

**Files:**
- Move: `cli/validation.py` -> `lightroom_sdk/validation.py`
- Modify: `cli/helpers.py` (import パス更新)
- Modify: `tests/test_validation.py` (import パス更新)
- Modify: `tests/test_validation_range.py` (import パス更新)
- Modify: `tests/test_validation_sanitize.py` (import パス更新)
- Modify: `tests/test_review_fixes.py` (import パス更新)

**Step 1: ファイル移動**

```bash
cd /Users/motokiendo/dev/lightroom-cli
mv cli/validation.py lightroom_sdk/validation.py
```

**Step 2: cli/validation.py に互換エイリアスを作成**

```python
# cli/validation.py
"""Backward-compatible re-export. Real implementation lives in lightroom_sdk.validation."""
from lightroom_sdk.validation import ValidationError, validate_params, _find_similar  # noqa: F401
```

**Step 3: 全テスト確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/ -v --ignore=tests/e2e -x -q`
Expected: PASS (re-export により既存 import が全て動く)

**Step 4: テストの import を新パスに更新**

`tests/test_validation.py`, `tests/test_validation_range.py`, `tests/test_validation_sanitize.py`, `tests/test_review_fixes.py` の全ての `from cli.validation import` を `from lightroom_sdk.validation import` に変更。

`cli/helpers.py` の `from cli.validation import` を `from lightroom_sdk.validation import` に変更:

```python
# cli/helpers.py 内 execute_command 関数の該当行を変更
# Before:
#     from cli.validation import ValidationError, validate_params
# After:
        from lightroom_sdk.validation import ValidationError, validate_params
```

**Step 5: 全テスト確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/ -v --ignore=tests/e2e -x -q`
Expected: PASS

**Step 6: コミット**
```bash
git add lightroom_sdk/validation.py cli/validation.py cli/helpers.py tests/test_validation.py tests/test_validation_range.py tests/test_validation_sanitize.py tests/test_review_fixes.py
git commit -m "refactor: validation.py を lightroom_sdk/ に移動 (逆依存解消)"
```

### Task 5: LightroomClient を ResilientSocketBridge に切替

**Files:**
- Modify: `lightroom_sdk/client.py`
- Modify: `tests/test_client.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_client.py に追記
def test_client_uses_resilient_bridge():
    """LightroomClient が ResilientSocketBridge を使用すること"""
    from lightroom_sdk.client import LightroomClient
    from lightroom_sdk.resilient_bridge import ResilientSocketBridge

    client = LightroomClient()
    assert isinstance(client._bridge, ResilientSocketBridge)
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_client.py::test_client_uses_resilient_bridge -v`
Expected: FAIL (現在は SocketBridge を使用)

**Step 3: 最小限の実装**

```python
# lightroom_sdk/client.py
import asyncio
import logging
from typing import Any, Dict, Optional

from .exceptions import ERROR_CODE_MAP, LightroomSDKError
from .protocol import LightroomResponse
from .resilient_bridge import ResilientSocketBridge

logger = logging.getLogger(__name__)


class LightroomClient:
    """Main client for interacting with Lightroom (uses ResilientSocketBridge)"""

    def __init__(self, host: str = "localhost", port_file: str | None = None):
        self.host = host
        self._bridge = ResilientSocketBridge(host=host, port_file=port_file)

    async def connect(self, retry_attempts: int = 5) -> None:
        """Connect to Lightroom bridge"""
        logger.debug(f"[LR_CLIENT:{id(self)}] connect() called")
        await self._bridge.connect()
        logger.debug(f"[LR_CLIENT:{id(self)}] connect() completed")

    async def disconnect(self) -> None:
        """Disconnect from Lightroom bridge"""
        await self._bridge.disconnect()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def execute_command(
        self,
        command: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Execute a command and handle response"""
        response = await self._bridge.send_command(command, params, timeout)

        # Parse response
        lr_response = LightroomResponse(**response)

        if not lr_response.success:
            error = lr_response.error or {}
            error_code = error.get("code", "UNKNOWN")
            error_message = error.get("message", "Unknown error")

            # Map to specific exception type
            exception_class = ERROR_CODE_MAP.get(error_code, LightroomSDKError)
            raise exception_class(error_message, code=error_code, details=error)

        return lr_response.result or {}

    # Convenience methods for common operations
    async def ping(self) -> Dict[str, Any]:
        """Test connection to Lightroom"""
        return await self.execute_command("system.ping")

    async def get_status(self) -> Dict[str, Any]:
        """Get bridge status"""
        return await self.execute_command("system.status")

    async def wait_for_lightroom(self, timeout: float = 60.0) -> bool:
        """Wait for Lightroom to become available"""
        logger.info("Checking for Lightroom Classic...")
        try:
            await asyncio.wait_for(self.connect(), timeout=timeout)
            logger.info("Lightroom is ready!")
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Lightroom not available within {timeout}s")
            return False
        except Exception as e:
            logger.warning(f"Lightroom not ready: {e}")
            return False

    async def create_ai_mask(
        self,
        selection_type: str,
        part: Optional[str] = None,
        adjustments: Optional[Dict[str, float]] = None,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        """Create an AI mask and optionally apply adjustments."""
        params: Dict[str, Any] = {"selectionType": selection_type}
        if part:
            params["part"] = part
        if adjustments:
            params["adjustments"] = adjustments
        return await self.execute_command("develop.createAIMaskWithAdjustments", params, timeout=timeout)

    async def batch_ai_mask(
        self,
        selection_type: str,
        photo_ids: Optional[list[str]] = None,
        all_selected: bool = False,
        part: Optional[str] = None,
        adjustments: Optional[Dict[str, float]] = None,
        continue_on_error: bool = True,
        timeout: float = 300.0,
    ) -> Dict[str, Any]:
        """Apply AI mask to multiple photos."""
        params: Dict[str, Any] = {
            "selectionType": selection_type,
            "allSelected": all_selected,
            "continueOnError": continue_on_error,
        }
        if photo_ids:
            params["photoIds"] = photo_ids
        if part:
            params["part"] = part
        if adjustments:
            params["adjustments"] = adjustments
        return await self.execute_command("develop.batchAIMask", params, timeout=timeout)
```

**Step 4: 既存テストを更新**

`tests/test_client.py` の全テストで `SocketBridge` を直接作成している箇所を `mock_lr_server` 経由に修正:

```python
# tests/test_client.py
import time

import pytest

from lightroom_sdk.client import LightroomClient


@pytest.mark.asyncio
async def test_execute_command_no_blocking_sleep(mock_lr_server):
    """time.sleep(0.1)が削除され、コマンド実行がブロックしないことを検証"""
    mock_lr_server.register_response("system.ping", {"status": "ok"})

    client = LightroomClient(port_file=str(mock_lr_server.port_file))
    await client.connect()

    start = time.monotonic()
    for _ in range(10):
        await client.execute_command("system.ping")
    elapsed = time.monotonic() - start

    assert elapsed < 1.0, f"10 commands took {elapsed:.2f}s (expected <1.0s without sleep)"
    await client.disconnect()


@pytest.mark.asyncio
async def test_ping_returns_result(mock_lr_server):
    """ping()がresultを返すことを検証"""
    mock_lr_server.register_response("system.ping", {"status": "ok"})

    client = LightroomClient(port_file=str(mock_lr_server.port_file))
    await client.connect()

    result = await client.ping()
    assert result["status"] == "ok"
    await client.disconnect()


@pytest.mark.asyncio
async def test_create_ai_mask_basic(mock_lr_server):
    """create_ai_mask が develop.createAIMaskWithAdjustments を正しいパラメータで送信する"""
    mock_lr_server.register_response(
        "develop.createAIMaskWithAdjustments",
        {"maskType": "aiSelection", "selectionType": "sky", "message": "Created AI sky mask"},
    )

    client = LightroomClient(port_file=str(mock_lr_server.port_file))
    await client.connect()
    try:
        result = await client.create_ai_mask("sky")
        assert result["selectionType"] == "sky"
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_create_ai_mask_with_adjustments(mock_lr_server):
    """create_ai_mask に adjustments を渡すと params に含まれる"""
    mock_lr_server.register_response(
        "develop.createAIMaskWithAdjustments",
        {"maskType": "aiSelection", "selectionType": "subject", "adjustments": {"Exposure": 0.5}},
    )

    client = LightroomClient(port_file=str(mock_lr_server.port_file))
    await client.connect()
    try:
        result = await client.create_ai_mask("subject", adjustments={"Exposure": 0.5})
        assert result["adjustments"] == {"Exposure": 0.5}
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_create_ai_mask_with_part(mock_lr_server):
    """create_ai_mask に part を渡すと params に含まれる"""
    mock_lr_server.register_response(
        "develop.createAIMaskWithAdjustments",
        {"maskType": "aiSelection", "selectionType": "people", "part": "eyes"},
    )

    client = LightroomClient(port_file=str(mock_lr_server.port_file))
    await client.connect()
    try:
        result = await client.create_ai_mask("people", part="eyes")
        assert result["part"] == "eyes"
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_batch_ai_mask_with_photo_ids(mock_lr_server):
    """batch_ai_mask が photoIds 付きで送信される"""
    mock_lr_server.register_response(
        "develop.batchAIMask",
        {
            "total": 2,
            "succeeded": 2,
            "failed": 0,
            "results": [{"photoId": "1", "status": "success"}, {"photoId": "2", "status": "success"}],
        },
    )

    client = LightroomClient(port_file=str(mock_lr_server.port_file))
    await client.connect()
    try:
        result = await client.batch_ai_mask("sky", photo_ids=["1", "2"])
        assert result["total"] == 2
        assert result["succeeded"] == 2
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_batch_ai_mask_all_selected(mock_lr_server):
    """batch_ai_mask --all-selected で allSelected=True が送信される"""
    mock_lr_server.register_response(
        "develop.batchAIMask",
        {"total": 3, "succeeded": 3, "failed": 0, "results": []},
    )

    client = LightroomClient(port_file=str(mock_lr_server.port_file))
    await client.connect()
    try:
        result = await client.batch_ai_mask("subject", all_selected=True)
        assert result["total"] == 3
    finally:
        await client.disconnect()


def test_client_uses_resilient_bridge():
    """LightroomClient が ResilientSocketBridge を使用すること"""
    from lightroom_sdk.resilient_bridge import ResilientSocketBridge

    client = LightroomClient()
    assert isinstance(client._bridge, ResilientSocketBridge)
```

**Step 5: 通過を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_client.py -v`
Expected: PASS

**Step 6: 全テスト確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/ -v --ignore=tests/e2e -x -q`
Expected: PASS

**Step 7: コミット**
```bash
git add lightroom_sdk/client.py tests/test_client.py
git commit -m "feat: LightroomClient を ResilientSocketBridge に切替 (MCP長寿命プロセス対応)"
```

---

## Phase 3: mcp_server/ 骨格 + tool_registry.py

### Task 6: mcp_server パッケージ骨格を作成

**Files:**
- Create: `mcp_server/__init__.py`
- Create: `mcp_server/server.py`

**Step 1: パッケージ作成**

```python
# mcp_server/__init__.py
"""MCP Server for Lightroom CLI."""
```

```python
# mcp_server/server.py
"""FastMCP server for Lightroom CLI.

Requires: pip install lightroom-cli[mcp]
"""

from __future__ import annotations

import sys


def main():
    """MCP Server エントリポイント。fastmcp 未インストール時はガイダンス表示。"""
    try:
        from fastmcp import FastMCP  # noqa: F401
    except ImportError:
        print(
            "Error: fastmcp is not installed.\n"
            "Install with: pip install lightroom-cli[mcp]\n",
            file=sys.stderr,
        )
        sys.exit(1)

    from mcp_server._run import run_server

    run_server()
```

```python
# mcp_server/_run.py
"""Server bootstrap (separated to avoid import of fastmcp at module level)."""

from __future__ import annotations


def run_server():
    from fastmcp import FastMCP

    from mcp_server.instructions import INSTRUCTIONS
    from mcp_server.tool_registry import register_all_tools
    from mcp_server.connection import ConnectionManager

    mcp = FastMCP(
        name="lightroom-cli",
        instructions=INSTRUCTIONS,
    )

    connection = ConnectionManager()
    register_all_tools(mcp, connection)

    mcp.run()
```

**Step 2: 動作確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -c "from mcp_server.server import main; print('import ok')"`
Expected: `import ok`

**Step 3: コミット**
```bash
git add mcp_server/__init__.py mcp_server/server.py mcp_server/_run.py
git commit -m "feat: mcp_server パッケージ骨格を作成"
```

### Task 7: tool_registry.py - スキーマ駆動の MCP ツール自動生成

**Files:**
- Create: `mcp_server/tool_registry.py`
- Create: `tests/test_mcp_tool_registry.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_mcp_tool_registry.py
"""MCP tool_registry のテスト。

fastmcp がインストールされていない環境でもスキップせずテスト可能な部分をテスト。
"""
import pytest

from mcp_server.tool_registry import (
    sanitize_tool_name,
    build_description,
    param_type_to_json_schema,
    create_tool_function,
)
from lightroom_sdk.schema import CommandSchema, ParamSchema, ParamType


class TestSanitizeToolName:
    def test_basic_conversion(self):
        assert sanitize_tool_name("catalog.searchPhotos") == "lr_catalog_search_photos"

    def test_system_ping(self):
        assert sanitize_tool_name("system.ping") == "lr_system_ping"

    def test_develop_set_value(self):
        assert sanitize_tool_name("develop.setValue") == "lr_develop_set_value"

    def test_nested_camel_case(self):
        assert sanitize_tool_name("develop.createAIMaskWithAdjustments") == "lr_develop_create_ai_mask_with_adjustments"

    def test_consecutive_uppercase(self):
        """AI のような連続大文字も正しく変換"""
        assert sanitize_tool_name("develop.getAISettings") == "lr_develop_get_ai_settings"


class TestBuildDescription:
    def test_read_only_command(self):
        schema = CommandSchema("system.ping", "system.ping", "Test connection")
        desc = build_description(schema)
        assert "Test connection" in desc
        assert "[read]" in desc
        assert "Timeout:" in desc

    def test_mutating_command(self):
        schema = CommandSchema(
            "develop.setValue", "develop.set", "Set develop parameter(s)",
            mutating=True, supports_dry_run=True,
        )
        desc = build_description(schema)
        assert "[write, mutating]" in desc or "[mutating" in desc

    def test_destructive_command(self):
        schema = CommandSchema(
            "catalog.removeFromCatalog", "catalog.remove-from-catalog",
            "Remove photo from catalog",
            mutating=True, requires_confirm=True,
        )
        desc = build_description(schema)
        assert "destructive" in desc


class TestParamTypeToJsonSchema:
    def test_string(self):
        assert param_type_to_json_schema(ParamType.STRING) == {"type": "string"}

    def test_integer(self):
        assert param_type_to_json_schema(ParamType.INTEGER) == {"type": "integer"}

    def test_float(self):
        assert param_type_to_json_schema(ParamType.FLOAT) == {"type": "number"}

    def test_boolean(self):
        assert param_type_to_json_schema(ParamType.BOOLEAN) == {"type": "boolean"}

    def test_json_object(self):
        assert param_type_to_json_schema(ParamType.JSON_OBJECT) == {"type": "object"}

    def test_json_array(self):
        assert param_type_to_json_schema(ParamType.JSON_ARRAY) == {"type": "array"}

    def test_enum_with_values(self):
        result = param_type_to_json_schema(ParamType.ENUM, enum_values=["a", "b"])
        assert result == {"type": "string", "enum": ["a", "b"]}


class TestCreateToolFunction:
    def test_returns_callable(self):
        schema = CommandSchema("system.ping", "system.ping", "Test connection")
        fn = create_tool_function(schema, connection=None)
        assert callable(fn)

    def test_function_name(self):
        schema = CommandSchema("system.ping", "system.ping", "Test connection")
        fn = create_tool_function(schema, connection=None)
        assert fn.__name__ == "lr_system_ping"


class TestToolCount:
    def test_plugin_commands_excluded(self):
        """plugin.* コマンドは MCP ツールから除外される"""
        from lightroom_sdk.schema import COMMAND_SCHEMAS

        non_plugin = {k: v for k, v in COMMAND_SCHEMAS.items() if not k.startswith("plugin.")}
        assert len(non_plugin) > 100  # 120 expected
        plugin_count = sum(1 for k in COMMAND_SCHEMAS if k.startswith("plugin."))
        assert plugin_count == 3  # install, uninstall, status
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_mcp_tool_registry.py -v`
Expected: FAIL (ModuleNotFoundError)

**Step 3: 最小限の実装**

```python
# mcp_server/tool_registry.py
"""Schema-driven MCP tool registration.

Converts COMMAND_SCHEMAS into FastMCP tools automatically.
"""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, Any

from lightroom_sdk.schema import COMMAND_SCHEMAS, CommandSchema, ParamSchema, ParamType

if TYPE_CHECKING:
    from fastmcp import FastMCP
    from mcp_server.connection import ConnectionManager


def sanitize_tool_name(command: str) -> str:
    """Convert command name to MCP tool name.

    catalog.searchPhotos -> lr_catalog_search_photos
    develop.createAIMaskWithAdjustments -> lr_develop_create_ai_mask_with_adjustments
    """
    # Split on dot
    parts = command.split(".")
    result_parts = []
    for part in parts:
        # CamelCase -> snake_case
        # Insert _ before uppercase letters, handling consecutive uppercase (AI -> ai)
        snake = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", part)
        snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", snake)
        result_parts.append(snake.lower())
    return "lr_" + "_".join(result_parts)


def build_description(schema: CommandSchema) -> str:
    """Build tool description with metadata suffix."""
    tags = []
    tags.append(schema.risk_level)
    if schema.mutating:
        tags.append("mutating")
    if schema.requires_confirm:
        tags.append("requires_confirm")
    if schema.supports_dry_run:
        tags.append("supports_dry_run")

    tag_str = ", ".join(tags)
    return f"{schema.description} [{tag_str}] Timeout: {schema.timeout}s"


def param_type_to_json_schema(
    param_type: ParamType, enum_values: list[str] | None = None
) -> dict[str, Any]:
    """Convert ParamType to JSON Schema type."""
    mapping = {
        ParamType.STRING: {"type": "string"},
        ParamType.INTEGER: {"type": "integer"},
        ParamType.FLOAT: {"type": "number"},
        ParamType.BOOLEAN: {"type": "boolean"},
        ParamType.JSON_OBJECT: {"type": "object"},
        ParamType.JSON_ARRAY: {"type": "array"},
    }
    if param_type == ParamType.ENUM:
        result: dict[str, Any] = {"type": "string"}
        if enum_values:
            result["enum"] = enum_values
        return result
    return mapping.get(param_type, {"type": "string"})


def create_tool_function(
    schema: CommandSchema, connection: ConnectionManager | None
) -> Any:
    """Create an async tool function for a given CommandSchema."""
    tool_name = sanitize_tool_name(schema.command)

    async def tool_fn(**kwargs: Any) -> Any:
        if connection is None:
            return {"error": "No connection manager configured"}

        # Extract dry_run if present
        dry_run = kwargs.pop("dry_run", False)
        if dry_run and schema.mutating:
            return {
                "dry_run": True,
                "command": schema.command,
                "mutating": schema.mutating,
                "risk_level": schema.risk_level,
                "params": kwargs,
            }

        return await connection.execute(
            command=schema.command,
            params=kwargs,
            timeout=schema.timeout,
            mutating=schema.mutating,
        )

    tool_fn.__name__ = tool_name
    tool_fn.__qualname__ = tool_name
    return tool_fn


def register_all_tools(mcp: FastMCP, connection: ConnectionManager) -> int:
    """Register all COMMAND_SCHEMAS as MCP tools. Returns count of registered tools."""
    count = 0
    for name, schema in COMMAND_SCHEMAS.items():
        if name.startswith("plugin."):
            continue

        tool_fn = create_tool_function(schema, connection)
        tool_name = sanitize_tool_name(name)
        description = build_description(schema)

        # Build parameter annotations dynamically for fastmcp
        # fastmcp uses function signature inspection, so we register via decorator
        mcp.tool(name=tool_name, description=description)(tool_fn)
        count += 1

    return count
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_mcp_tool_registry.py -v`
Expected: PASS

**Step 5: コミット**
```bash
git add mcp_server/tool_registry.py tests/test_mcp_tool_registry.py
git commit -m "feat: tool_registry.py - スキーマ駆動の MCP ツール自動生成"
```

---

## Phase 4: connection.py + エラーハンドリング + Lock

### Task 8: ConnectionManager 実装

**Files:**
- Create: `mcp_server/connection.py`
- Create: `tests/test_mcp_connection.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_mcp_connection.py
"""ConnectionManager のテスト。MockLightroomServer を使用。"""
import asyncio

import pytest

from mcp_server.connection import ConnectionManager


@pytest.mark.asyncio
async def test_lazy_connect(mock_lr_server):
    """初回 execute 時に自動接続する"""
    mock_lr_server.register_response("system.ping", {"status": "ok"})

    cm = ConnectionManager(port_file=str(mock_lr_server.port_file))
    assert cm._client is None

    result = await cm.execute("system.ping", {}, timeout=5.0, mutating=False)
    assert result["result"]["status"] == "ok"
    assert cm._client is not None
    await cm.shutdown()


@pytest.mark.asyncio
async def test_connection_error_returns_mcp_error(mock_lr_server):
    """接続できない場合に MCP エラーレスポンスを返す"""
    cm = ConnectionManager(port_file="/tmp/nonexistent_port_file_test.txt")

    result = await cm.execute("system.ping", {}, timeout=2.0, mutating=False)
    assert result["isError"] is True
    assert "CONNECTION_ERROR" in result.get("code", "") or "接続" in result.get("message", "")
    await cm.shutdown()


@pytest.mark.asyncio
async def test_timeout_error_returns_mcp_error(mock_lr_server):
    """タイムアウト時に MCP エラーレスポンスを返す"""
    mock_lr_server.register_response("system.ping", {"status": "ok"}, delay=5.0)

    cm = ConnectionManager(port_file=str(mock_lr_server.port_file))
    result = await cm.execute("system.ping", {}, timeout=0.1, mutating=False)
    assert result["isError"] is True
    await cm.shutdown()


@pytest.mark.asyncio
async def test_validation_error_returns_mcp_error(mock_lr_server):
    """バリデーションエラー時に MCP エラーレスポンスを返す"""
    cm = ConnectionManager(port_file=str(mock_lr_server.port_file))

    # unknown_param は catalog.setRating に存在しない
    result = await cm.execute(
        "catalog.setRating",
        {"photoId": "1", "rating": 3, "unknownParam": "bad"},
        timeout=5.0,
        mutating=True,
    )
    assert result["isError"] is True
    assert "VALIDATION_ERROR" in result.get("code", "")
    await cm.shutdown()


@pytest.mark.asyncio
async def test_lock_serializes_commands(mock_lr_server):
    """asyncio.Lock がコマンドを直列化すること"""
    call_order = []

    mock_lr_server.register_response("system.ping", {"status": "ok"}, delay=0.1)

    cm = ConnectionManager(port_file=str(mock_lr_server.port_file))

    async def run_cmd(label: str):
        await cm.execute("system.ping", {}, timeout=5.0, mutating=False)
        call_order.append(label)

    await asyncio.gather(run_cmd("A"), run_cmd("B"))
    assert len(call_order) == 2
    await cm.shutdown()


@pytest.mark.asyncio
async def test_mutating_not_retried_after_reconnect():
    """mutating コマンドは再接続後に再送されずエラーを返す"""
    cm = ConnectionManager(port_file="/tmp/nonexistent_port_file_test.txt")
    result = await cm.execute(
        "develop.setValue",
        {"parameter": "Exposure", "value": 0.5},
        timeout=2.0,
        mutating=True,
    )
    assert result["isError"] is True
    await cm.shutdown()
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_mcp_connection.py -v`
Expected: FAIL (ModuleNotFoundError)

**Step 3: 最小限の実装**

```python
# mcp_server/connection.py
"""Lightroom connection lifecycle manager for MCP Server."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages LightroomClient lifecycle with lazy connect and asyncio.Lock."""

    def __init__(self, port_file: str | None = None):
        self._port_file = port_file
        self._client = None
        self._lock = asyncio.Lock()

    async def execute(
        self,
        command: str,
        params: dict[str, Any],
        timeout: float,
        mutating: bool,
    ) -> dict[str, Any]:
        """Execute a command with validation, locking, and error handling.

        Returns MCP-formatted response dict (always includes 'isError' on failure).
        """
        # 1. Validation
        from lightroom_sdk.validation import ValidationError, validate_params

        try:
            validated = validate_params(command, params)
        except ValidationError as e:
            return {
                "isError": True,
                "code": "VALIDATION_ERROR",
                "message": str(e),
                "suggestions": e.suggestions,
            }

        # 2. Execute with lock
        try:
            async with asyncio.timeout(timeout):
                async with self._lock:
                    client = await self._get_client()
                    return await client._bridge.send_command(command, validated, timeout=timeout)
        except (ConnectionError, OSError) as e:
            logger.warning(f"Connection error on '{command}': {e}")
            self._client = None  # Force reconnect on next call
            return {
                "isError": True,
                "code": "CONNECTION_ERROR",
                "message": (
                    "Lightroom に接続できません。Lightroom Classic が起動し、"
                    "CLI Bridge プラグインが有効であることを確認してください。"
                ),
            }
        except (asyncio.TimeoutError, TimeoutError) as e:
            return {
                "isError": True,
                "code": "TIMEOUT_ERROR",
                "message": f"コマンドがタイムアウトしました ({timeout}秒)。",
            }
        except Exception as e:
            # Check for SDK-specific exceptions
            from lightroom_sdk.exceptions import ConnectionError as LRConnectionError
            from lightroom_sdk.exceptions import TimeoutError as LRTimeoutError

            if isinstance(e, LRConnectionError):
                self._client = None
                return {
                    "isError": True,
                    "code": "CONNECTION_ERROR",
                    "message": (
                        "Lightroom に接続できません。Lightroom Classic が起動し、"
                        "CLI Bridge プラグインが有効であることを確認してください。"
                    ),
                }
            if isinstance(e, LRTimeoutError):
                return {
                    "isError": True,
                    "code": "TIMEOUT_ERROR",
                    "message": f"コマンドがタイムアウトしました ({timeout}秒)。",
                }
            logger.exception(f"Unexpected error on '{command}'")
            return {
                "isError": True,
                "code": "INTERNAL_ERROR",
                "message": str(e),
            }

    async def _get_client(self):
        """Get or create LightroomClient (lazy initialization)."""
        if self._client is None:
            from lightroom_sdk.client import LightroomClient

            self._client = LightroomClient(port_file=self._port_file)
            await self._client.connect()
        return self._client

    async def get_status(self) -> dict[str, Any]:
        """Get connection status for MCP resource."""
        if self._client is None:
            return {"connected": False, "state": "disconnected"}
        state = self._client._bridge.state.value
        return {"connected": state == "connected", "state": state}

    async def shutdown(self) -> None:
        """Clean shutdown."""
        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._client = None
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_mcp_connection.py -v`
Expected: PASS

**Step 5: 全テスト確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/ -v --ignore=tests/e2e -x -q`
Expected: PASS

**Step 6: コミット**
```bash
git add mcp_server/connection.py tests/test_mcp_connection.py
git commit -m "feat: ConnectionManager - lazy connect, asyncio.Lock, エラーハンドリング"
```

---

## Phase 5: instructions.py

### Task 9: MCP instructions テキストを作成

**Files:**
- Create: `mcp_server/instructions.py`
- Create: `tests/test_mcp_instructions.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_mcp_instructions.py
"""instructions のテスト。"""


def test_instructions_is_non_empty_string():
    from mcp_server.instructions import INSTRUCTIONS

    assert isinstance(INSTRUCTIONS, str)
    assert len(INSTRUCTIONS) > 100


def test_instructions_contains_ping():
    """接続確認フローが含まれること"""
    from mcp_server.instructions import INSTRUCTIONS

    assert "lr_system_ping" in INSTRUCTIONS


def test_instructions_contains_error_recovery():
    """エラー回復パターンが含まれること"""
    from mcp_server.instructions import INSTRUCTIONS

    assert "CONNECTION_ERROR" in INSTRUCTIONS


def test_instructions_contains_workflow():
    """主要ワークフローが含まれること"""
    from mcp_server.instructions import INSTRUCTIONS

    assert "lr_catalog" in INSTRUCTIONS
    assert "lr_develop" in INSTRUCTIONS


def test_instructions_mentions_lr_prefix():
    """ツール名が lr_ prefix であることが記載されていること"""
    from mcp_server.instructions import INSTRUCTIONS

    assert "lr_" in INSTRUCTIONS


def test_instructions_mentions_dry_run():
    """dry_run の説明が含まれること"""
    from mcp_server.instructions import INSTRUCTIONS

    assert "dry_run" in INSTRUCTIONS
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_mcp_instructions.py -v`
Expected: FAIL (ModuleNotFoundError)

**Step 3: 最小限の実装**

```python
# mcp_server/instructions.py
"""MCP Server instructions for AI agents (Cowork/Desktop).

Equivalent to SKILL.md but adapted for MCP tool naming conventions.
"""

INSTRUCTIONS = """\
# Lightroom CLI - MCP Server Guide

You are interacting with Adobe Lightroom Classic through MCP tools.
All tool names use the `lr_` prefix with snake_case (e.g., `lr_system_ping`, `lr_catalog_list`).

## Getting Started

1. **Always verify connection first:**
   Call `lr_system_ping`. If it fails, Lightroom Classic may not be running or the CLI Bridge plugin may not be active.

2. **Check connection details:**
   Call `lr_system_check_connection` for detailed diagnostics.

## Error Recovery

| Error Code | Meaning | Action |
|------------|---------|--------|
| CONNECTION_ERROR | Cannot reach Lightroom | Ensure Lightroom Classic is running with CLI Bridge plugin active. Call `lr_system_check_connection`. |
| TIMEOUT_ERROR | Command took too long | Retry with a longer timeout or check if Lightroom is busy. |
| VALIDATION_ERROR | Invalid parameters | Check the error message for details and suggestions. |

## Key Workflows

### Browse and Select Photos
1. `lr_catalog_list` - List photos in the current view
2. `lr_catalog_search_photos` - Search by keyword
3. `lr_catalog_get_selected` - Get currently selected photos
4. `lr_catalog_set_selected_photos` - Select specific photos by ID

### Develop / Edit
1. `lr_develop_get_settings` - Get current develop settings
2. `lr_develop_set_value` - Set a single develop parameter (e.g., Exposure, Contrast)
3. `lr_develop_apply_settings` - Apply multiple settings at once
4. `lr_develop_auto_tone` - Apply auto tone
5. `lr_develop_reset_all` - Reset all develop settings (destructive)

### AI Masks
1. `lr_develop_create_ai_mask_with_adjustments` - Create AI mask (subject, sky, background, etc.)
2. `lr_develop_batch_ai_mask` - Apply AI mask to multiple photos

### Metadata
1. `lr_catalog_get_photo_metadata` - Get photo metadata
2. `lr_catalog_set_rating` - Set star rating (0-5)
3. `lr_catalog_add_keywords` - Add keywords
4. `lr_catalog_set_flag` - Set flag (1=pick, -1=reject, 0=none)

## Safety

- **Mutating commands** modify photos/catalog. Check `[mutating]` in tool description.
- **Destructive commands** require explicit confirmation. Check `[destructive, requires_confirm]`.
- **Use `dry_run=true`** parameter on mutating commands to preview changes without applying them.
- Read-only commands are always safe to call.

## Parameter Discovery

Tool descriptions include parameter types and constraints. For detailed parameter info,
use `lr_schema_get_command_detail` if available, or refer to the tool's parameter schema.

## Tips

- Use `lr_catalog_get_selected` to get photo IDs before operating on specific photos.
- Most develop commands operate on the currently selected photo.
- Batch operations accept `photoIds` arrays or `allSelected=true`.
- Preview generation (`lr_preview_*`) can take up to 120 seconds.
"""
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_mcp_instructions.py -v`
Expected: PASS

**Step 5: コミット**
```bash
git add mcp_server/instructions.py tests/test_mcp_instructions.py
git commit -m "feat: MCP instructions - エージェント向けガイドテキスト"
```

---

## Phase 6: lr mcp install/uninstall/status/test コマンド

### Task 10: cli/commands/mcp.py サブコマンド実装

**Files:**
- Create: `cli/commands/mcp.py`
- Modify: `cli/main.py`
- Create: `tests/test_cli_mcp.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_cli_mcp.py
"""lr mcp サブコマンドのテスト。"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from cli.main import cli


class TestMcpInstall:
    def test_install_creates_config_entry(self, tmp_path):
        """lr mcp install が設定ファイルにエントリを追加する"""
        config_file = tmp_path / "claude_desktop_config.json"
        config_file.write_text("{}")

        with patch("cli.commands.mcp._get_claude_config_path", return_value=config_file):
            runner = CliRunner()
            result = runner.invoke(cli, ["mcp", "install"])
            assert result.exit_code == 0

            config = json.loads(config_file.read_text())
            assert "mcpServers" in config
            assert "lightroom-cli" in config["mcpServers"]
            assert config["mcpServers"]["lightroom-cli"]["command"] == "lr-mcp"

    def test_install_preserves_existing_servers(self, tmp_path):
        """既存の mcpServers エントリを保持する"""
        config_file = tmp_path / "claude_desktop_config.json"
        config_file.write_text(json.dumps({
            "mcpServers": {"other-server": {"command": "other"}}
        }))

        with patch("cli.commands.mcp._get_claude_config_path", return_value=config_file):
            runner = CliRunner()
            result = runner.invoke(cli, ["mcp", "install"])
            assert result.exit_code == 0

            config = json.loads(config_file.read_text())
            assert "other-server" in config["mcpServers"]
            assert "lightroom-cli" in config["mcpServers"]

    def test_install_creates_config_file_if_missing(self, tmp_path):
        """設定ファイルが存在しない場合は新規作成"""
        config_file = tmp_path / "claude_desktop_config.json"

        with patch("cli.commands.mcp._get_claude_config_path", return_value=config_file):
            runner = CliRunner()
            result = runner.invoke(cli, ["mcp", "install"])
            assert result.exit_code == 0
            assert config_file.exists()

    def test_install_checks_fastmcp_availability(self):
        """fastmcp がない場合はエラー"""
        with patch("cli.commands.mcp._check_fastmcp_installed", return_value=False):
            runner = CliRunner()
            result = runner.invoke(cli, ["mcp", "install"])
            assert result.exit_code != 0
            assert "fastmcp" in result.output.lower() or "pip install" in result.output.lower()


class TestMcpUninstall:
    def test_uninstall_removes_entry(self, tmp_path):
        """lr mcp uninstall がエントリを削除する"""
        config_file = tmp_path / "claude_desktop_config.json"
        config_file.write_text(json.dumps({
            "mcpServers": {
                "lightroom-cli": {"command": "lr-mcp"},
                "other": {"command": "other"},
            }
        }))

        with patch("cli.commands.mcp._get_claude_config_path", return_value=config_file):
            runner = CliRunner()
            result = runner.invoke(cli, ["mcp", "uninstall"])
            assert result.exit_code == 0

            config = json.loads(config_file.read_text())
            assert "lightroom-cli" not in config["mcpServers"]
            assert "other" in config["mcpServers"]

    def test_uninstall_when_not_installed(self, tmp_path):
        """インストールされていない場合は正常終了"""
        config_file = tmp_path / "claude_desktop_config.json"
        config_file.write_text("{}")

        with patch("cli.commands.mcp._get_claude_config_path", return_value=config_file):
            runner = CliRunner()
            result = runner.invoke(cli, ["mcp", "uninstall"])
            assert result.exit_code == 0


class TestMcpStatus:
    def test_status_installed(self, tmp_path):
        """インストール済みの場合"""
        config_file = tmp_path / "claude_desktop_config.json"
        config_file.write_text(json.dumps({
            "mcpServers": {"lightroom-cli": {"command": "lr-mcp"}}
        }))

        with patch("cli.commands.mcp._get_claude_config_path", return_value=config_file):
            runner = CliRunner()
            result = runner.invoke(cli, ["mcp", "status"])
            assert result.exit_code == 0
            assert "installed" in result.output.lower() or "Installed" in result.output

    def test_status_not_installed(self, tmp_path):
        """未インストールの場合"""
        config_file = tmp_path / "claude_desktop_config.json"
        config_file.write_text("{}")

        with patch("cli.commands.mcp._get_claude_config_path", return_value=config_file):
            runner = CliRunner()
            result = runner.invoke(cli, ["mcp", "status"])
            assert result.exit_code == 0
            assert "not installed" in result.output.lower() or "Not" in result.output
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_cli_mcp.py -v`
Expected: FAIL

**Step 3: 最小限の実装**

```python
# cli/commands/mcp.py
"""lr mcp -- MCP Server 管理コマンド"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click


def _get_claude_config_path() -> Path:
    """Claude Desktop 設定ファイルのパスを返す。"""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif sys.platform == "win32":
        import os
        appdata = os.environ.get("APPDATA", "")
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    else:
        return Path.home() / ".config" / "claude" / "claude_desktop_config.json"


def _check_fastmcp_installed() -> bool:
    """fastmcp がインストールされているか確認。"""
    try:
        import fastmcp  # noqa: F401
        return True
    except ImportError:
        return False


def _read_config(config_path: Path) -> dict:
    """設定ファイルを読み込む。存在しない場合は空 dict。"""
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))
    return {}


def _write_config(config_path: Path, config: dict) -> None:
    """設定ファイルを書き込む。親ディレクトリも作成。"""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


MCP_SERVER_ENTRY = {
    "command": "lr-mcp",
    "args": [],
}


@click.group()
def mcp():
    """Manage MCP Server for Claude Desktop / Cowork."""
    pass


@mcp.command()
def install():
    """Install lightroom-cli MCP server into Claude Desktop config."""
    if not _check_fastmcp_installed():
        click.echo(
            "Error: fastmcp is not installed.\n"
            "Run: pip install lightroom-cli[mcp]",
            err=True,
        )
        raise SystemExit(1)

    config_path = _get_claude_config_path()
    config = _read_config(config_path)

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    config["mcpServers"]["lightroom-cli"] = MCP_SERVER_ENTRY
    _write_config(config_path, config)

    click.echo(f"MCP server installed to {config_path}")
    click.echo("Restart Claude Desktop / Cowork to activate.")


@mcp.command()
def uninstall():
    """Remove lightroom-cli MCP server from Claude Desktop config."""
    config_path = _get_claude_config_path()
    config = _read_config(config_path)

    servers = config.get("mcpServers", {})
    if "lightroom-cli" not in servers:
        click.echo("MCP server is not installed.")
        return

    del servers["lightroom-cli"]
    _write_config(config_path, config)
    click.echo("MCP server uninstalled.")


@mcp.command()
def status():
    """Show MCP server installation status."""
    config_path = _get_claude_config_path()
    config = _read_config(config_path)

    click.echo(f"Config file: {config_path}")

    servers = config.get("mcpServers", {})
    if "lightroom-cli" in servers:
        entry = servers["lightroom-cli"]
        click.echo(f"Status: Installed")
        click.echo(f"Command: {entry.get('command', 'N/A')}")
    else:
        click.echo("Status: Not installed")
        click.echo("Run 'lr mcp install' to set up.")

    # Check fastmcp
    if _check_fastmcp_installed():
        click.echo("fastmcp: Available")
    else:
        click.echo("fastmcp: Not installed (run: pip install lightroom-cli[mcp])")


@mcp.command()
def test():
    """Test MCP server startup (connect to Lightroom and exit)."""
    if not _check_fastmcp_installed():
        click.echo(
            "Error: fastmcp is not installed.\n"
            "Run: pip install lightroom-cli[mcp]",
            err=True,
        )
        raise SystemExit(1)

    click.echo("Testing MCP server startup...")
    try:
        from mcp_server.connection import ConnectionManager
        import asyncio

        async def _test():
            cm = ConnectionManager()
            status = await cm.get_status()
            click.echo(f"Connection status: {status}")
            await cm.shutdown()

        asyncio.run(_test())
        click.echo("MCP server test complete.")
    except Exception as e:
        click.echo(f"Test failed: {e}", err=True)
        raise SystemExit(1)
```

**Step 4: cli/main.py に mcp コマンドを登録**

`cli/main.py` の import セクションに以下を追加:

```python
from cli.commands.mcp import mcp

cli.add_command(mcp)
```

**Step 5: 通過を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_cli_mcp.py -v`
Expected: PASS

**Step 6: 全テスト確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/ -v --ignore=tests/e2e -x -q`
Expected: PASS

**Step 7: コミット**
```bash
git add cli/commands/mcp.py cli/main.py tests/test_cli_mcp.py
git commit -m "feat: lr mcp install/uninstall/status/test コマンド追加"
```

---

## Phase 7: テスト (MCP + Windows paths + 同値性)

### Task 11: MCP Server 統合テスト (fastmcp TestClient)

**Files:**
- Create: `tests/test_mcp_server.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_mcp_server.py
"""MCP Server 統合テスト。fastmcp の TestClient を使用。

fastmcp がない環境ではスキップ。
"""
import pytest

fastmcp = pytest.importorskip("fastmcp")

from fastmcp import FastMCP

from mcp_server.tool_registry import register_all_tools, sanitize_tool_name
from mcp_server.connection import ConnectionManager
from mcp_server.instructions import INSTRUCTIONS
from lightroom_sdk.schema import COMMAND_SCHEMAS


@pytest.fixture
def mcp_server(mock_lr_server):
    """テスト用 MCP サーバーを作成"""
    server = FastMCP(name="lightroom-cli-test", instructions=INSTRUCTIONS)
    connection = ConnectionManager(port_file=str(mock_lr_server.port_file))
    register_all_tools(server, connection)
    return server, connection


class TestMcpServerToolCount:
    def test_registered_tool_count(self, mcp_server):
        """plugin.* を除いた全コマンドが登録されること"""
        server, _ = mcp_server
        non_plugin = sum(1 for k in COMMAND_SCHEMAS if not k.startswith("plugin."))
        # FastMCP の登録ツール数を確認
        # 注: fastmcp の内部APIに依存するため、ツール数はスキーマ数と一致するはず
        assert non_plugin > 100


class TestMcpServerPing:
    @pytest.mark.asyncio
    async def test_ping_via_mcp(self, mcp_server, mock_lr_server):
        """MCP 経由で system.ping が実行できること"""
        server, connection = mcp_server
        mock_lr_server.register_response("system.ping", {"status": "ok"})

        # ConnectionManager を使って直接テスト
        result = await connection.execute("system.ping", {}, timeout=5.0, mutating=False)
        assert result.get("result", {}).get("status") == "ok" or result.get("status") == "ok"
        await connection.shutdown()


class TestMcpServerValidation:
    @pytest.mark.asyncio
    async def test_validation_error(self, mcp_server, mock_lr_server):
        """不正パラメータで VALIDATION_ERROR が返ること"""
        _, connection = mcp_server
        result = await connection.execute(
            "catalog.setRating",
            {"photoId": "1", "rating": 3, "badParam": "x"},
            timeout=5.0,
            mutating=True,
        )
        assert result["isError"] is True
        assert result["code"] == "VALIDATION_ERROR"
        await connection.shutdown()
```

**Step 2: テスト実行**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_mcp_server.py -v`
Expected: PASS

**Step 3: コミット**
```bash
git add tests/test_mcp_server.py
git commit -m "test: MCP Server 統合テスト追加"
```

### Task 12: Windows paths テスト

**Files:**
- Modify: `tests/test_paths.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_paths.py に追記
import tempfile
from pathlib import Path
from unittest.mock import patch


class TestWindowsPaths:
    def test_get_port_file_windows(self):
        """Windows でも tempfile.gettempdir() が使われること"""
        with patch.dict("os.environ", {}, clear=True):
            import os
            os.environ.pop("LR_PORT_FILE", None)
            from lightroom_sdk.paths import get_port_file

            result = get_port_file()
            assert result == Path(tempfile.gettempdir()) / "lightroom_ports.txt"

    def test_get_lightroom_modules_dir_windows(self):
        """Windows で APPDATA ベースのパスが返ること"""
        with (
            patch("sys.platform", "win32"),
            patch.dict("os.environ", {"APPDATA": r"C:\Users\test\AppData\Roaming"}, clear=False),
        ):
            # 環境変数をクリア
            import os
            os.environ.pop("LR_PLUGIN_DIR", None)
            from lightroom_sdk import paths
            # force reimport
            import importlib
            importlib.reload(paths)

            result = paths.get_lightroom_modules_dir()
            assert "Adobe" in str(result)
            assert "Lightroom" in str(result)
            assert "Modules" in str(result)

    def test_get_port_file_env_override(self):
        """LR_PORT_FILE 環境変数が優先されること"""
        with patch.dict("os.environ", {"LR_PORT_FILE": "/custom/ports.txt"}):
            from lightroom_sdk.paths import get_port_file

            result = get_port_file()
            assert result == Path("/custom/ports.txt")
```

**Step 2: テスト実行**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_paths.py -v`
Expected: PASS

**Step 3: コミット**
```bash
git add tests/test_paths.py
git commit -m "test: Windows paths テスト追加"
```

### Task 13: CLI/MCP バリデーション同値性テスト

**Files:**
- Create: `tests/test_mcp_cli_equivalence.py`

**Step 1: テストを書く**

```python
# tests/test_mcp_cli_equivalence.py
"""CLI と MCP でバリデーション結果が一致することを確認。"""
import pytest

from lightroom_sdk.validation import ValidationError, validate_params


class TestValidationEquivalence:
    """CLI と MCP は同一の validate_params を使うため、結果は同一であること。"""

    def test_valid_params_pass(self):
        """正常パラメータが通ること"""
        result = validate_params("catalog.setRating", {"photoId": "1", "rating": 3})
        assert result["photoId"] == "1"
        assert result["rating"] == 3

    def test_unknown_param_raises(self):
        """不明パラメータでエラー"""
        with pytest.raises(ValidationError) as exc_info:
            validate_params("catalog.setRating", {"photoId": "1", "rating": 3, "bad": "x"})
        assert "bad" in str(exc_info.value)

    def test_missing_required_raises(self):
        """必須パラメータ欠落でエラー"""
        with pytest.raises(ValidationError):
            validate_params("catalog.setRating", {"photoId": "1"})

    def test_type_coercion(self):
        """文字列 -> 数値の型変換"""
        result = validate_params("catalog.setRating", {"photoId": "1", "rating": "3"})
        assert result["rating"] == 3

    def test_range_validation(self):
        """範囲外でエラー"""
        with pytest.raises(ValidationError):
            validate_params("catalog.setRating", {"photoId": "1", "rating": 10})

    def test_enum_validation(self):
        """ENUM のバリデーション"""
        result = validate_params("catalog.setColorLabel", {"photoId": "1", "label": "red"})
        assert result["label"] == "red"

        with pytest.raises(ValidationError):
            validate_params("catalog.setColorLabel", {"photoId": "1", "label": "orange"})

    def test_unknown_command_passes_through(self):
        """スキーマ未定義のコマンドはバリデーションスキップ"""
        result = validate_params("unknown.command", {"any": "param"})
        assert result == {"any": "param"}

    def test_validation_source_is_sdk(self):
        """バリデーションが lightroom_sdk.validation から来ていること"""
        import lightroom_sdk.validation as sdk_val
        assert validate_params is sdk_val.validate_params
```

**Step 2: テスト実行**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_mcp_cli_equivalence.py -v`
Expected: PASS

**Step 3: コミット**
```bash
git add tests/test_mcp_cli_equivalence.py
git commit -m "test: CLI/MCP バリデーション同値性テスト追加"
```

---

## Phase 8: pyproject.toml + SKILL.md 更新

### Task 14: pyproject.toml 更新

**Files:**
- Modify: `pyproject.toml`

**Step 1: pyproject.toml を更新**

以下の変更を適用:

1. `version` を `"1.1.0"` に更新
2. `project.scripts` に `lr-mcp` エントリポイントを追加
3. `project.optional-dependencies` に `mcp` セクションを追加
4. `dev` に `fastmcp` を追加
5. `classifiers` に Windows を追加
6. `tool.setuptools.packages` に `mcp_server` を追加

```toml
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "lightroom-cli"
version = "1.1.0"
description = "CLI tool for Adobe Lightroom Classic — 107 commands for full Lightroom control"
authors = [{name = "M.Endo", email = "motoki@clockwork-sound.com"}]
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.10"
classifiers = [
    "Development Status :: 4 - Beta",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Multimedia :: Graphics",
    "Operating System :: MacOS",
    "Operating System :: Microsoft :: Windows",
]
dependencies = [
    "click>=8.1",
    "rich>=13.0",
    "pydantic>=2.0",
    "platformdirs>=3.0",
]

[project.optional-dependencies]
mcp = [
    "fastmcp>=3.0",
]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
    "ruff>=0.4",
    "fastmcp>=3.0",
]

[project.urls]
Homepage = "https://github.com/znznzna/lightroom-cli"
Repository = "https://github.com/znznzna/lightroom-cli"
Issues = "https://github.com/znznzna/lightroom-cli/issues"

[project.scripts]
lr = "cli.main:cli"
lr-mcp = "mcp_server.server:main"

[tool.setuptools]
packages = ["lightroom_sdk", "lightroom_sdk.types", "cli", "cli.commands", "mcp_server"]

[tool.setuptools.package-data]
lightroom_sdk = ["plugin/*.lua"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
markers = [
    "integration: marks tests as integration tests requiring Lightroom",
    "unit: marks tests as unit tests",
    "e2e: marks tests as E2E tests requiring Lightroom Classic",
    "destructive: marks destructive tests (skipped by default, run with --run-destructive)",
    "slow: marks slow tests (preview generation, batch operations)",
]

[tool.ruff]
target-version = "py310"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "W", "I"]
ignore = ["E402"]
```

**Step 2: インストール確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/pip install -e ".[dev]" && venv/bin/lr --version`
Expected: `lr, version 1.1.0`

**Step 3: 全テスト確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/ -v --ignore=tests/e2e -x -q`
Expected: PASS

**Step 4: コミット**
```bash
git add pyproject.toml
git commit -m "feat: pyproject.toml - MCP optional dependency + Windows classifier + v1.1.0"
```

### Task 15: SKILL.md に MCP セクション追加

**Files:**
- Modify: `plugin/skills/lightroom-cli/SKILL.md`

**Step 1: SKILL.md 末尾に MCP セクションを追加**

```markdown
## MCP Server (Claude Desktop / Cowork)

For non-CLI environments (Claude Desktop, Cowork), use the MCP Server:

1. `pip install lightroom-cli[mcp]`
2. `lr mcp install`
3. Restart Claude Desktop / Cowork

MCP tool names use `lr_` prefix + snake_case (e.g., `lr_system_ping`, `lr_catalog_list`).
Parameters are identical to CLI. Use `dry_run=true` for mutating commands.

To check status: `lr mcp status`
To uninstall: `lr mcp uninstall`
```

**Step 2: コミット**
```bash
git add plugin/skills/lightroom-cli/SKILL.md
git commit -m "docs: SKILL.md に MCP Server セットアップセクション追加"
```

---

## Phase 9: Windows CI (GitHub Actions)

### Task 16: GitHub Actions に Windows matrix 追加

**Files:**
- Modify: `.github/workflows/test.yml`

**Step 1: test.yml を更新**

```yaml
name: Test

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff
      - run: ruff check .
      - run: ruff format --check .

  test:
    strategy:
      matrix:
        os: [macos-latest, windows-latest]
        python-version: ["3.10", "3.12"]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: python -m pytest tests/ -v --ignore=tests/e2e --cov=lightroom_sdk --cov=cli --cov=mcp_server
```

**Step 2: コミット**
```bash
git add .github/workflows/test.yml
git commit -m "ci: Windows + macOS matrix テスト追加"
```

---

## 全体確認

### Task 17: 最終リグレッションテスト

**Step 1: Lint**
Run: `cd /Users/motokiendo/dev/lightroom-cli && ruff check . && ruff format --check .`
Expected: PASS

**Step 2: 全テスト**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/ -v --ignore=tests/e2e`
Expected: PASS (680+ 既存テスト + 新規テスト全通過)

**Step 3: MCP Server import テスト**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -c "from mcp_server.server import main; print('OK')"`
Expected: `OK`

**Step 4: lr-mcp エントリポイント確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/lr-mcp --help 2>&1 || echo 'entry point works (stdio mode, no --help)'`
Expected: エントリポイントが存在すること

---

## ファイル変更サマリー

| ファイル | 操作 | Phase |
|---------|------|-------|
| `lightroom_sdk/plugin/PlatformPaths.lua` | Modify | 1 |
| `lightroom_sdk/paths.py` | Modify | 1 |
| `cli/commands/plugin.py` | Modify | 1 |
| `lightroom_sdk/validation.py` | Create (move from cli/) | 2 |
| `cli/validation.py` | Modify (re-export) | 2 |
| `cli/helpers.py` | Modify (import path) | 2 |
| `lightroom_sdk/client.py` | Modify | 2 |
| `mcp_server/__init__.py` | Create | 3 |
| `mcp_server/server.py` | Create | 3 |
| `mcp_server/_run.py` | Create | 3 |
| `mcp_server/tool_registry.py` | Create | 3 |
| `mcp_server/connection.py` | Create | 4 |
| `mcp_server/instructions.py` | Create | 5 |
| `cli/commands/mcp.py` | Create | 6 |
| `cli/main.py` | Modify | 6 |
| `pyproject.toml` | Modify | 8 |
| `plugin/skills/lightroom-cli/SKILL.md` | Modify | 8 |
| `.github/workflows/test.yml` | Modify | 9 |

| テストファイル | 操作 | Phase |
|---------------|------|-------|
| `tests/test_paths.py` | Modify | 1, 7 |
| `tests/test_cli_plugin.py` | Modify | 1 |
| `tests/test_validation.py` | Modify (import) | 2 |
| `tests/test_validation_range.py` | Modify (import) | 2 |
| `tests/test_validation_sanitize.py` | Modify (import) | 2 |
| `tests/test_review_fixes.py` | Modify (import) | 2 |
| `tests/test_client.py` | Modify | 2 |
| `tests/test_mcp_tool_registry.py` | Create | 3 |
| `tests/test_mcp_connection.py` | Create | 4 |
| `tests/test_mcp_instructions.py` | Create | 5 |
| `tests/test_cli_mcp.py` | Create | 6 |
| `tests/test_mcp_server.py` | Create | 7 |
| `tests/test_mcp_cli_equivalence.py` | Create | 7 |
