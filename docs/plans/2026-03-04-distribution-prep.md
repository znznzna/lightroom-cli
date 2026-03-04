# Distribution Preparation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** lightroom-cli を Homebrew / PyPI で配布可能にし、README英日化・SKILLS.md・E2Eテストを整備する
**Architecture:** paths.py でOS横断パス抽象化、lr plugin install でCLIプラグイン管理、homebrew-tap リポでFormula配布
**Tech Stack:** Python 3.10+, Click, platformdirs, Homebrew Formula (Ruby), Lua
---

## Phase 1: パス抽象化 (`lightroom_sdk/paths.py` + `PlatformPaths.lua`)

### Task 1: paths.py のユニットテスト作成

**Files:**
- Create: `tests/test_paths.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_paths.py
import pytest
from unittest.mock import patch
from pathlib import Path


class TestGetPortFile:
    """get_port_file() のユニットテスト"""

    def test_env_override(self, monkeypatch):
        """LR_PORT_FILE 環境変数が設定されていればそのパスを返す"""
        monkeypatch.setenv("LR_PORT_FILE", "/custom/path.txt")
        from lightroom_sdk.paths import get_port_file
        assert get_port_file() == Path("/custom/path.txt")

    def test_macos_default(self, monkeypatch):
        """macOS ではデフォルトで /tmp/lightroom_ports.txt"""
        monkeypatch.delenv("LR_PORT_FILE", raising=False)
        with patch("lightroom_sdk.paths.sys") as mock_sys:
            mock_sys.platform = "darwin"
            from importlib import reload
            import lightroom_sdk.paths
            reload(lightroom_sdk.paths)
            result = lightroom_sdk.paths.get_port_file()
            assert result == Path("/tmp/lightroom_ports.txt")

    def test_linux_default(self, monkeypatch):
        """Linux でもデフォルトで /tmp/lightroom_ports.txt"""
        monkeypatch.delenv("LR_PORT_FILE", raising=False)
        with patch("lightroom_sdk.paths.sys") as mock_sys:
            mock_sys.platform = "linux"
            from importlib import reload
            import lightroom_sdk.paths
            reload(lightroom_sdk.paths)
            result = lightroom_sdk.paths.get_port_file()
            assert result == Path("/tmp/lightroom_ports.txt")

    def test_env_override_takes_priority(self, monkeypatch):
        """環境変数はプラットフォーム判定より優先"""
        monkeypatch.setenv("LR_PORT_FILE", "/override/ports.txt")
        with patch("lightroom_sdk.paths.sys") as mock_sys:
            mock_sys.platform = "darwin"
            from importlib import reload
            import lightroom_sdk.paths
            reload(lightroom_sdk.paths)
            result = lightroom_sdk.paths.get_port_file()
            assert result == Path("/override/ports.txt")


class TestGetLightroomModulesDir:
    """get_lightroom_modules_dir() のユニットテスト"""

    def test_env_override(self, monkeypatch):
        """LR_PLUGIN_DIR 環境変数が設定されていればそのパスを返す"""
        monkeypatch.setenv("LR_PLUGIN_DIR", "/custom/modules")
        from lightroom_sdk.paths import get_lightroom_modules_dir
        assert get_lightroom_modules_dir() == Path("/custom/modules")

    def test_macos_default(self, monkeypatch):
        """macOS では ~/Library/Application Support/Adobe/Lightroom/Modules"""
        monkeypatch.delenv("LR_PLUGIN_DIR", raising=False)
        with patch("lightroom_sdk.paths.sys") as mock_sys:
            mock_sys.platform = "darwin"
            from importlib import reload
            import lightroom_sdk.paths
            reload(lightroom_sdk.paths)
            result = lightroom_sdk.paths.get_lightroom_modules_dir()
            assert "Library/Application Support/Adobe/Lightroom/Modules" in str(result)

    def test_linux_raises(self, monkeypatch):
        """Linux では Lightroom Classic 非対応なので RuntimeError"""
        monkeypatch.delenv("LR_PLUGIN_DIR", raising=False)
        with patch("lightroom_sdk.paths.sys") as mock_sys:
            mock_sys.platform = "linux"
            from importlib import reload
            import lightroom_sdk.paths
            reload(lightroom_sdk.paths)
            with pytest.raises(RuntimeError, match="Unsupported platform"):
                lightroom_sdk.paths.get_lightroom_modules_dir()

    def test_env_override_bypasses_platform_check(self, monkeypatch):
        """環境変数設定時はプラットフォームチェックをバイパス"""
        monkeypatch.setenv("LR_PLUGIN_DIR", "/custom/lr/modules")
        with patch("lightroom_sdk.paths.sys") as mock_sys:
            mock_sys.platform = "linux"
            from importlib import reload
            import lightroom_sdk.paths
            reload(lightroom_sdk.paths)
            result = lightroom_sdk.paths.get_lightroom_modules_dir()
            assert result == Path("/custom/lr/modules")


class TestGetPluginSourceDir:
    """get_plugin_source_dir() のユニットテスト"""

    def test_returns_existing_plugin_dir(self):
        """リポジトリルートの lightroom-plugin/ ディレクトリを返す"""
        from lightroom_sdk.paths import get_plugin_source_dir
        result = get_plugin_source_dir()
        assert result.name == "lightroom-plugin"
        assert result.exists()

    def test_contains_info_lua(self):
        """プラグインソースに Info.lua が含まれる"""
        from lightroom_sdk.paths import get_plugin_source_dir
        result = get_plugin_source_dir()
        assert (result / "Info.lua").exists()


class TestConstants:
    """定数のテスト"""

    def test_plugin_name(self):
        from lightroom_sdk.paths import PLUGIN_NAME
        assert PLUGIN_NAME == "lightroom-python-bridge.lrdevplugin"
```

**Step 2: 失敗を確認**

Run: `python -m pytest tests/test_paths.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'lightroom_sdk.paths')

---

### Task 2: paths.py の実装

**Files:**
- Create: `lightroom_sdk/paths.py`

**Step 1: 実装コード**

```python
"""
OS 横断のパス解決モジュール。
優先順位: 環境変数 > OS判定デフォルト

Windows 分岐は将来対応の布石として含むが、テストは macOS/Linux のみ。
"""
import os
import sys
from pathlib import Path

PLUGIN_NAME = "lightroom-python-bridge.lrdevplugin"


def get_port_file() -> Path:
    """ポートファイルのパスを返す。

    優先順位:
    1. 環境変数 LR_PORT_FILE
    2. OS 判定デフォルト
    """
    env = os.environ.get("LR_PORT_FILE")
    if env:
        return Path(env)

    if sys.platform == "win32":
        return Path(os.environ.get("TEMP", r"C:\Temp")) / "lightroom_ports.txt"
    else:
        # macOS / Linux
        return Path("/tmp/lightroom_ports.txt")


def get_lightroom_modules_dir() -> Path:
    """Lightroom Classic の Modules ディレクトリを返す。

    優先順位:
    1. 環境変数 LR_PLUGIN_DIR
    2. OS 判定デフォルト
    """
    env = os.environ.get("LR_PLUGIN_DIR")
    if env:
        return Path(env)

    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "Adobe"
            / "Lightroom"
            / "Modules"
        )
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "")
        return Path(appdata) / "Adobe" / "Lightroom" / "Modules"
    else:
        raise RuntimeError(
            "Unsupported platform for Lightroom Classic. "
            "Set LR_PLUGIN_DIR environment variable to override."
        )


def get_plugin_source_dir() -> Path:
    """バンドルされた Lua プラグインソースのパスを返す。

    開発時: リポジトリルートの lightroom-plugin/
    パッケージインストール時: site-packages 内のデータ
    """
    # リポジトリルートからの相対パス
    repo_dir = Path(__file__).parent.parent / "lightroom-plugin"
    if repo_dir.exists():
        return repo_dir

    # site-packages からのフォールバック (pip install 時)
    import importlib.resources as pkg_resources

    return Path(str(pkg_resources.files("lightroom_cli_plugin")))
```

**Step 2: テスト通過を確認**

Run: `python -m pytest tests/test_paths.py -v`
Expected: PASS

**Step 3: コミット**

```bash
git add lightroom_sdk/paths.py tests/test_paths.py
git commit -m "feat: add paths.py for OS-agnostic path resolution (distribution prep)"
```

---

### Task 3: socket_bridge.py を paths.py に移行

**Files:**
- Modify: `lightroom_sdk/socket_bridge.py:14`
- Test: `tests/test_paths.py` (既存テストがデグレしないこと)

**Step 1: 失敗するテストを書く**

`tests/test_paths.py` の末尾に追加:

```python
class TestSocketBridgeUsesPathsModule:
    """socket_bridge.py が paths.py を使用していることを検証"""

    def test_default_port_file_matches_paths(self):
        """SocketBridge のデフォルト port_file が paths.get_port_file() と一致"""
        from lightroom_sdk.paths import get_port_file
        from lightroom_sdk.socket_bridge import SocketBridge
        bridge = SocketBridge()
        assert bridge.port_file == get_port_file()
```

**Step 2: 失敗を確認**

Run: `python -m pytest tests/test_paths.py::TestSocketBridgeUsesPathsModule -v`
Expected: FAIL (SocketBridge() requires port_file arg or uses old default)

**Step 3: socket_bridge.py を修正**

`lightroom_sdk/socket_bridge.py` の14行目を変更:

変更前:
```python
    def __init__(self, host: str = 'localhost', port_file: str = '/tmp/lightroom_ports.txt'):
```

変更後:
```python
    def __init__(self, host: str = 'localhost', port_file: str | None = None):
        from .paths import get_port_file
        if port_file is None:
            resolved_port_file = get_port_file()
        else:
            resolved_port_file = Path(port_file)
```

さらに15行目を変更:

変更前:
```python
        self.port_file = Path(port_file)
```

変更後:
```python
        self.port_file = resolved_port_file
```

**Step 4: テスト通過を確認**

Run: `python -m pytest tests/test_paths.py -v && python -m pytest tests/ -v`
Expected: ALL PASS

**Step 5: コミット**

```bash
git add lightroom_sdk/socket_bridge.py tests/test_paths.py
git commit -m "refactor: socket_bridge.py uses paths.get_port_file() (remove hardcoded path)"
```

---

### Task 4: resilient_bridge.py を paths.py に移行

**Files:**
- Modify: `lightroom_sdk/resilient_bridge.py:25`

**Step 1: 失敗するテストを書く**

`tests/test_paths.py` の末尾に追加:

```python
class TestResilientBridgeUsesPathsModule:
    """resilient_bridge.py が paths.py を使用していることを検証"""

    def test_default_port_file_matches_paths(self):
        """ResilientSocketBridge のデフォルト port_file が paths.get_port_file() と一致"""
        from lightroom_sdk.paths import get_port_file
        from lightroom_sdk.resilient_bridge import ResilientSocketBridge
        bridge = ResilientSocketBridge()
        assert bridge._port_file == str(get_port_file())
```

**Step 2: 失敗を確認**

Run: `python -m pytest tests/test_paths.py::TestResilientBridgeUsesPathsModule -v`
Expected: FAIL

**Step 3: resilient_bridge.py を修正**

`lightroom_sdk/resilient_bridge.py` の22-26行目を変更:

変更前:
```python
    def __init__(
        self,
        host: str = "localhost",
        port_file: str = "/tmp/lightroom_ports.txt",
        max_reconnect_attempts: int = 5,
```

変更後:
```python
    def __init__(
        self,
        host: str = "localhost",
        port_file: str | None = None,
        max_reconnect_attempts: int = 5,
```

そして30行目を変更:

変更前:
```python
        self._port_file = port_file
```

変更後:
```python
        if port_file is None:
            from .paths import get_port_file
            self._port_file = str(get_port_file())
        else:
            self._port_file = port_file
```

**Step 4: テスト通過を確認**

Run: `python -m pytest tests/test_paths.py -v && python -m pytest tests/ -v`
Expected: ALL PASS

**Step 5: コミット**

```bash
git add lightroom_sdk/resilient_bridge.py tests/test_paths.py
git commit -m "refactor: resilient_bridge.py uses paths.get_port_file() (remove hardcoded path)"
```

---

### Task 5: cli/commands/system.py を paths.py に移行

**Files:**
- Modify: `cli/commands/system.py:7` (get_bridge のデフォルト引数)
- Modify: `cli/commands/system.py:86` (check-connection の --port-file デフォルト)

**Step 1: 失敗するテストを書く**

`tests/test_paths.py` の末尾に追加:

```python
class TestSystemCommandUsesPathsModule:
    """system.py が paths.py を使用していることを検証"""

    def test_get_bridge_default_uses_paths(self):
        """get_bridge() のデフォルトが paths.get_port_file() を使用"""
        import inspect
        from cli.commands.system import get_bridge
        sig = inspect.signature(get_bridge)
        default = sig.parameters["port_file"].default
        # デフォルトが None であること（paths.py に委譲）
        assert default is None
```

**Step 2: 失敗を確認**

Run: `python -m pytest tests/test_paths.py::TestSystemCommandUsesPathsModule -v`
Expected: FAIL

**Step 3: cli/commands/system.py を修正**

7行目を変更:

変更前:
```python
def get_bridge(port_file: str = "/tmp/lightroom_ports.txt"):
    """ResilientSocketBridgeインスタンスを取得（遅延import）"""
    from lightroom_sdk.resilient_bridge import ResilientSocketBridge
    return ResilientSocketBridge(port_file=port_file)
```

変更後:
```python
def get_bridge(port_file: str | None = None):
    """ResilientSocketBridgeインスタンスを取得（遅延import）"""
    from lightroom_sdk.resilient_bridge import ResilientSocketBridge
    return ResilientSocketBridge(port_file=port_file)
```

86行目を変更:

変更前:
```python
@click.option("--port-file", default="/tmp/lightroom_ports.txt")
```

変更後:
```python
@click.option("--port-file", default=None, help="Path to port file (default: auto-detect)")
```

88-90行目の check_connection 関数も修正:

変更前:
```python
def check_connection(ctx, port_file):
    """Check if Lightroom is available"""
    port_path = Path(port_file)
```

変更後:
```python
def check_connection(ctx, port_file):
    """Check if Lightroom is available"""
    if port_file is None:
        from lightroom_sdk.paths import get_port_file
        port_file = str(get_port_file())
    port_path = Path(port_file)
```

**Step 4: テスト通過を確認**

Run: `python -m pytest tests/test_paths.py -v && python -m pytest tests/ -v`
Expected: ALL PASS

**Step 5: コミット**

```bash
git add cli/commands/system.py tests/test_paths.py
git commit -m "refactor: system.py uses paths.get_port_file() (remove hardcoded path)"
```

---

### Task 6: scripts/check-connection.py を paths.py に移行

**Files:**
- Modify: `scripts/check-connection.py:7`

**Step 1: 修正**

`scripts/check-connection.py` の7行目を変更:

変更前:
```python
PORT_FILE = Path("/tmp/lightroom_ports.txt")
```

変更後:
```python
from lightroom_sdk.paths import get_port_file
PORT_FILE = get_port_file()
```

不要になった `from pathlib import Path` のインポートも削除（Port_FILE に Path() を使わなくなるため）。ただし他で Path を使っていないか確認。使っていなければ削除。

**Step 2: テスト通過を確認**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

**Step 3: コミット**

```bash
git add scripts/check-connection.py
git commit -m "refactor: check-connection.py uses paths.get_port_file() (remove hardcoded path)"
```

---

### Task 7: PlatformPaths.lua の作成

**Files:**
- Create: `lightroom-plugin/PlatformPaths.lua`

**Step 1: 実装**

```lua
-- PlatformPaths.lua
-- OS 横断のパス解決モジュール
-- 優先順位: 環境変数 > OS 自動判定デフォルト
local PlatformPaths = {}

--- OS 判定: Windows かどうか
function PlatformPaths.isWindows()
    return package.config:sub(1, 1) == "\\"
end

--- OS 判定: macOS かどうか (= not Windows)
function PlatformPaths.isMacOS()
    return not PlatformPaths.isWindows()
end

--- ポートファイルパスを返す
--- @return string ポートファイルの絶対パス
function PlatformPaths.getPortFilePath()
    -- 環境変数優先
    local envPath = os.getenv("LR_PORT_FILE")
    if envPath and envPath ~= "" then
        return envPath
    end

    -- OS 判定でデフォルト
    if PlatformPaths.isWindows() then
        local temp = os.getenv("TEMP") or "C:\\Temp"
        return temp .. "\\lightroom_ports.txt"
    else
        return "/tmp/lightroom_ports.txt"
    end
end

return PlatformPaths
```

**Step 2: コミット**

```bash
git add lightroom-plugin/PlatformPaths.lua
git commit -m "feat: add PlatformPaths.lua for OS-agnostic port file path (Lua side)"
```

---

### Task 8: SimpleSocketBridge.lua を PlatformPaths.lua に移行

**Files:**
- Modify: `lightroom-plugin/SimpleSocketBridge.lua:71` (writePortFile 内の io.open)
- Modify: `lightroom-plugin/SimpleSocketBridge.lua:338-339` (ソケットループ終了時の削除)
- Modify: `lightroom-plugin/SimpleSocketBridge.lua:438-439` (stopSocketServer 内の削除)

**Step 1: SimpleSocketBridge.lua の先頭に require を追加**

ファイル先頭の既存 import の後（8行目以降）に追加:

```lua
local PlatformPaths = require 'PlatformPaths'
```

**Step 2: 71行目を変更**

変更前:
```lua
        local file = io.open("/tmp/lightroom_ports.txt", "w")
```

変更後:
```lua
        local file = io.open(PlatformPaths.getPortFilePath(), "w")
```

**Step 3: 338-339行目を変更**

変更前:
```lua
                if LrFileUtils.exists("/tmp/lightroom_ports.txt") then
                    LrFileUtils.delete("/tmp/lightroom_ports.txt")
```

変更後:
```lua
                local portFile = PlatformPaths.getPortFilePath()
                if LrFileUtils.exists(portFile) then
                    LrFileUtils.delete(portFile)
```

**Step 4: 438-439行目を変更**

変更前:
```lua
        if LrFileUtils.exists("/tmp/lightroom_ports.txt") then
            LrFileUtils.delete("/tmp/lightroom_ports.txt")
```

変更後:
```lua
        local portFile = PlatformPaths.getPortFilePath()
        if LrFileUtils.exists(portFile) then
            LrFileUtils.delete(portFile)
```

**Step 5: 既存テストの通過を確認**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS (Lua の変更は Python テストに影響しない)

**Step 6: コミット**

```bash
git add lightroom-plugin/SimpleSocketBridge.lua
git commit -m "refactor: SimpleSocketBridge.lua uses PlatformPaths (remove 4 hardcoded paths)"
```

---

## Phase 2: `lr plugin install` コマンド

### Task 9: plugin コマンドのテスト作成

**Files:**
- Create: `tests/test_cli_plugin.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_cli_plugin.py
import pytest
from pathlib import Path
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestPluginInstall:
    """lr plugin install のテスト"""

    def test_install_copy(self, tmp_path, monkeypatch, runner):
        """コピーモードでプラグインをインストール"""
        modules_dir = tmp_path / "Modules"
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))
        result = runner.invoke(cli, ["plugin", "install"])
        assert result.exit_code == 0
        assert "installed" in result.output.lower() or "Plugin installed" in result.output
        dest = modules_dir / "lightroom-python-bridge.lrdevplugin"
        assert dest.exists()
        assert not dest.is_symlink()
        # Info.lua がコピーされていることを確認
        assert (dest / "Info.lua").exists()

    def test_install_dev_symlink(self, tmp_path, monkeypatch, runner):
        """--dev フラグでシンボリックリンクインストール"""
        modules_dir = tmp_path / "Modules"
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))
        result = runner.invoke(cli, ["plugin", "install", "--dev"])
        assert result.exit_code == 0
        assert "symlink" in result.output.lower()
        dest = modules_dir / "lightroom-python-bridge.lrdevplugin"
        assert dest.is_symlink()

    def test_install_overwrites_existing(self, tmp_path, monkeypatch, runner):
        """既存インストールを上書き"""
        modules_dir = tmp_path / "Modules"
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))
        # 1回目
        runner.invoke(cli, ["plugin", "install"])
        # 2回目（上書き）
        result = runner.invoke(cli, ["plugin", "install"])
        assert result.exit_code == 0

    def test_install_quiet(self, tmp_path, monkeypatch, runner):
        """--quiet フラグで出力を抑制"""
        modules_dir = tmp_path / "Modules"
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))
        result = runner.invoke(cli, ["plugin", "install", "--quiet"])
        assert result.exit_code == 0
        assert result.output.strip() == ""


class TestPluginUninstall:
    """lr plugin uninstall のテスト"""

    def test_uninstall_copy(self, tmp_path, monkeypatch, runner):
        """コピーインストールのアンインストール"""
        modules_dir = tmp_path / "Modules"
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))
        runner.invoke(cli, ["plugin", "install"])
        result = runner.invoke(cli, ["plugin", "uninstall"])
        assert result.exit_code == 0
        assert "uninstalled" in result.output.lower()
        dest = modules_dir / "lightroom-python-bridge.lrdevplugin"
        assert not dest.exists()

    def test_uninstall_symlink(self, tmp_path, monkeypatch, runner):
        """シンボリックリンクインストールのアンインストール"""
        modules_dir = tmp_path / "Modules"
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))
        runner.invoke(cli, ["plugin", "install", "--dev"])
        result = runner.invoke(cli, ["plugin", "uninstall"])
        assert result.exit_code == 0
        dest = modules_dir / "lightroom-python-bridge.lrdevplugin"
        assert not dest.exists()

    def test_uninstall_not_installed(self, tmp_path, monkeypatch, runner):
        """未インストール時のアンインストール"""
        modules_dir = tmp_path / "Modules"
        modules_dir.mkdir(parents=True)
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))
        result = runner.invoke(cli, ["plugin", "uninstall"])
        assert result.exit_code == 0
        assert "not installed" in result.output.lower()


class TestPluginStatus:
    """lr plugin status のテスト"""

    def test_status_not_installed(self, tmp_path, monkeypatch, runner):
        """未インストール時のステータス"""
        modules_dir = tmp_path / "Modules"
        modules_dir.mkdir(parents=True)
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))
        result = runner.invoke(cli, ["plugin", "status"])
        assert result.exit_code == 0
        assert "not installed" in result.output.lower()

    def test_status_installed_copy(self, tmp_path, monkeypatch, runner):
        """コピーインストール時のステータス"""
        modules_dir = tmp_path / "Modules"
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))
        runner.invoke(cli, ["plugin", "install"])
        result = runner.invoke(cli, ["plugin", "status"])
        assert result.exit_code == 0
        assert "copy" in result.output.lower()

    def test_status_installed_symlink(self, tmp_path, monkeypatch, runner):
        """シンボリックリンクインストール時のステータス"""
        modules_dir = tmp_path / "Modules"
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))
        runner.invoke(cli, ["plugin", "install", "--dev"])
        result = runner.invoke(cli, ["plugin", "status"])
        assert result.exit_code == 0
        assert "symlink" in result.output.lower()
```

**Step 2: 失敗を確認**

Run: `python -m pytest tests/test_cli_plugin.py -v`
Expected: FAIL (No such command 'plugin')

---

### Task 10: cli/commands/plugin.py の実装

**Files:**
- Create: `cli/commands/plugin.py`

**Step 1: 実装**

```python
"""lr plugin — Lightroom プラグインの管理コマンド"""
import click
import shutil
import os
from pathlib import Path

from lightroom_sdk.paths import get_lightroom_modules_dir, get_plugin_source_dir, PLUGIN_NAME


@click.group()
def plugin():
    """Manage Lightroom plugin installation."""
    pass


@plugin.command()
@click.option("--dev", is_flag=True, help="Use symlink instead of copy (development mode)")
@click.option("--quiet", "-q", is_flag=True, help="Suppress output")
def install(dev: bool, quiet: bool) -> None:
    """Install the Lightroom plugin to the Modules directory."""
    source = get_plugin_source_dir()
    dest_dir = get_lightroom_modules_dir()
    dest = dest_dir / PLUGIN_NAME

    if not source.exists():
        click.echo(f"Error: Plugin source not found at {source}", err=True)
        raise SystemExit(1)

    dest_dir.mkdir(parents=True, exist_ok=True)

    # 既存インストールを削除
    if dest.exists() or dest.is_symlink():
        if dest.is_symlink():
            dest.unlink()
        else:
            shutil.rmtree(dest)

    if dev:
        dest.symlink_to(source)
        if not quiet:
            click.echo(f"Plugin symlinked: {dest} -> {source}")
    else:
        shutil.copytree(source, dest)
        if not quiet:
            click.echo(f"Plugin installed to {dest}")


@plugin.command()
@click.option("--quiet", "-q", is_flag=True, help="Suppress output")
def uninstall(quiet: bool) -> None:
    """Uninstall the Lightroom plugin."""
    dest = get_lightroom_modules_dir() / PLUGIN_NAME

    if not dest.exists() and not dest.is_symlink():
        if not quiet:
            click.echo("Plugin is not installed.")
        return

    if dest.is_symlink():
        dest.unlink()
    else:
        shutil.rmtree(dest)

    if not quiet:
        click.echo("Plugin uninstalled.")


@plugin.command()
def status() -> None:
    """Show plugin installation status."""
    dest = get_lightroom_modules_dir() / PLUGIN_NAME
    source = get_plugin_source_dir()

    click.echo(f"Plugin source:  {source}")
    click.echo(f"Install target: {dest}")

    if dest.is_symlink():
        target = dest.resolve()
        click.echo(f"Status:         Installed (symlink -> {target})")
    elif dest.exists():
        click.echo(f"Status:         Installed (copy)")
    else:
        click.echo(f"Status:         Not installed")
```

**Step 2: テスト通過を確認（plugin コマンド単体）**

Run: `python -m pytest tests/test_cli_plugin.py -v`
Expected: FAIL (まだ main.py に登録していないので 'plugin' コマンドが見つからない)

---

### Task 11: main.py に plugin グループを登録

**Files:**
- Modify: `cli/main.py:33` (末尾に追加)

**Step 1: cli/main.py を修正**

31行目以降に追加:

```python
from cli.commands.plugin import plugin
cli.add_command(plugin)
```

**Step 2: テスト通過を確認**

Run: `python -m pytest tests/test_cli_plugin.py -v && python -m pytest tests/ -v`
Expected: ALL PASS

**Step 3: コミット**

```bash
git add cli/commands/plugin.py cli/main.py tests/test_cli_plugin.py
git commit -m "feat: add lr plugin install/uninstall/status commands"
```

---

## Phase 3: クリーンアップ

### Task 12: .gitignore に docs/plans/ を追加

**Files:**
- Modify: `.gitignore`

**Step 1: .gitignore に追加**

`.gitignore` の末尾に追加:

```gitignore

# Development plans (dev-only, not for distribution)
docs/plans/
```

**Step 2: 既存の docs/plans/ をトラッキングから除外**

Run:
```bash
git rm --cached -r docs/plans/
```

注意: ファイル自体はローカルに残る。リモートからは削除される。

**Step 3: コミット**

```bash
git add .gitignore
git commit -m "docs: exclude docs/plans/ from distribution (dev-only)"
```

---

### Task 13: pyproject.toml の整備

**Files:**
- Modify: `pyproject.toml`

**Step 1: pyproject.toml を更新**

全体を以下に更新:

```toml
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "lightroom-cli"
version = "2.1.0"
description = "CLI tool for Adobe Lightroom Classic — 107 commands for full Lightroom control"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.10"
keywords = ["lightroom", "adobe", "photography", "cli", "automation"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: MIT License",
    "Operating System :: MacOS",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Multimedia :: Graphics",
]
dependencies = [
    "click>=8.1",
    "rich>=13.0",
    "pydantic>=2.0",
    "platformdirs>=3.0",
]

[project.urls]
Homepage = "https://github.com/znznzna/lightroom-cli"
Repository = "https://github.com/znznzna/lightroom-cli"
Issues = "https://github.com/znznzna/lightroom-cli/issues"

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
]

[project.scripts]
lr = "cli.main:cli"

[tool.setuptools]
packages = ["lightroom_sdk", "cli", "cli.commands"]

[tool.setuptools.package-data]
"*" = ["lightroom-plugin/**/*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
markers = [
    "integration: marks tests as integration tests requiring Lightroom",
    "unit: marks tests as unit tests",
    "e2e: end-to-end test requiring running Lightroom Classic",
]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

**Step 2: platformdirs をインストール**

Run: `pip install platformdirs>=3.0`

**Step 3: pytest.ini を削除（pyproject.toml に統合済み）**

Run: `rm pytest.ini`

**Step 4: テスト通過を確認**

Run: `pip install -e ".[dev]" && python -m pytest tests/ -v`
Expected: ALL PASS

**Step 5: コミット**

```bash
git add pyproject.toml
git rm pytest.ini
git commit -m "refactor: consolidate pyproject.toml (add platformdirs, classifiers, merge pytest.ini)"
```

---

### Task 14: 不要なランタイムパス参照を .gitignore から除去

**Files:**
- Modify: `.gitignore`

**Step 1: .gitignore から不要なエントリを削除**

以下の2行を削除（/tmp/ のパスは .gitignore で管理するものではない）:

```
/tmp/lightroom_ports.txt
/tmp/lightroom_ports_test.txt
```

これらは /tmp 配下なのでリポジトリには入らない。.gitignore に入れる意味がない。

**Step 2: コミット**

```bash
git add .gitignore
git commit -m "fix: remove irrelevant /tmp paths from .gitignore"
```

---

## Phase 4: Homebrew 準備

### Task 15: Homebrew Formula のテンプレート作成

**Files:**
- Create: `homebrew/lightroom-cli.rb`

**Step 1: Formula 作成**

```ruby
# homebrew/lightroom-cli.rb
# Template for homebrew-tap repository (znznzna/homebrew-tap)
# SHA256 and URL will be updated on release.
class LightroomCli < Formula
  include Language::Python::Virtualenv

  desc "CLI tool for Adobe Lightroom Classic - 107 commands"
  homepage "https://github.com/znznzna/lightroom-cli"
  url "https://github.com/znznzna/lightroom-cli/archive/refs/tags/vX.Y.Z.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"

  depends_on "python@3.12"

  # Resource blocks will be generated by `brew update-python-resources`
  # after the package is published to PyPI.
  # Example:
  # resource "click" do
  #   url "https://files.pythonhosted.org/packages/..."
  #   sha256 "..."
  # end

  def install
    virtualenv_install_with_resources
  end

  def post_install
    system bin/"lr", "plugin", "install", "--quiet"
  end

  def caveats
    <<~EOS
      Lightroom Classic must be running with the plugin active.

      To install/update the Lightroom plugin:
        lr plugin install

      To verify the connection:
        lr system check-connection
    EOS
  end

  test do
    assert_match "lr", shell_output("#{bin}/lr --version")
  end
end
```

**Step 2: コミット**

```bash
git add homebrew/lightroom-cli.rb
git commit -m "docs: add Homebrew Formula template (for future homebrew-tap repo)"
```

---

## Phase 5: README 英語/日本語

### Task 16: 現在の README.md を README.ja.md にコピー

**Files:**
- Create: `README.ja.md` (現在の README.md の内容 + 英語版リンク)

**Step 1: コピー & リンク追加**

Run: `cp README.md README.ja.md`

`README.ja.md` の先頭（1行目の前）に追加:

```markdown
[English](README.md)

```

**Step 2: コミット**

```bash
git add README.ja.md
git commit -m "docs: create README.ja.md from existing Japanese README"
```

---

### Task 17: README.md を英語化

**Files:**
- Modify: `README.md`

**Step 1: README.md を英語で書き直す**

```markdown
# Lightroom CLI

[![Test](https://github.com/znznzna/lightroom-cli/actions/workflows/test.yml/badge.svg)](https://github.com/znznzna/lightroom-cli/actions/workflows/test.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Japanese / 日本語](README.ja.md)

**Full command-line control for Adobe Lightroom Classic — 107 commands.**

Develop settings, masking, tone curves, catalog management, selection operations, and more. Perfect for batch processing and scripting automation.

## Architecture

```
+---------------------+     TCP Socket (JSON-RPC)     +--------------+
|  Lightroom Classic   |<----------------------------->|  Python SDK  |
|  (Lua Plugin)        |   Dual socket: send/receive   |              |
+---------------------+                                +------+-------+
                                                              |
                                                       +------+-------+
                                                       |   CLI (lr)   |
                                                       |   Click app  |
                                                       +--------------+
```

A Lua plugin runs inside Lightroom Classic and communicates with the Python SDK over dual TCP sockets (send/receive) using JSON-RPC. The CLI runs as the `lr` command and controls Lightroom via the SDK.

## Quick Start

### Prerequisites

- **Python 3.10+**
- **Adobe Lightroom Classic** (desktop)
- macOS

### Installation

#### From Source (Recommended for Development)

```bash
git clone https://github.com/znznzna/lightroom-cli.git
cd lightroom-cli
pip install -e ".[dev]"
lr plugin install --dev
```

#### Via pip

```bash
pip install lightroom-cli
lr plugin install
```

### Verify Connection

```bash
# With Lightroom Classic running:
lr system ping
# -> pong

lr system status
```

## Usage Examples

```bash
# Get selected photos
lr catalog get-selected

# Set develop parameters
lr develop set Exposure 1.5 Contrast 25 Clarity 30

# Apply AutoTone
lr develop auto-tone

# Apply S-curve to tone curve
lr develop curve s-curve

# Create mask and add brush
lr develop mask create
lr develop mask add brush

# Apply preset
lr develop preset "Vivid Landscape"

# Rating and flagging
lr selection set-rating 5
lr selection flag

# Search catalog
lr catalog search "landscape" --limit 20

# JSON output
lr -o json develop get-settings

# Table format
lr -o table catalog list --limit 10
```

## Command Groups

| Group | Commands | Description |
|-------|----------|-------------|
| `lr system` | 4 | Connection management and status |
| `lr catalog` | 27 | Catalog operations, photo search, metadata |
| `lr develop` | 55 | Develop settings, masks, curves, filters |
| `lr preview` | 4 | Preview generation and info |
| `lr selection` | 17 | Selection, flags, ratings, labels |
| `lr plugin` | 3 | Plugin installation management |

**See [CLI Reference](docs/CLI_REFERENCE.md) for all 107 commands.**

## Global Options

```bash
lr --output json ...    # JSON output (-o json)
lr --output table ...   # Table output (-o table)
lr --verbose ...        # Debug logging (-v)
lr --timeout 60 ...     # Timeout in seconds (-t 60)
lr --version            # Show version
```

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `LR_PORT_FILE` | Path to Lightroom port file | `/tmp/lightroom_ports.txt` |
| `LR_PLUGIN_DIR` | Lightroom Modules directory | `~/Library/Application Support/Adobe/Lightroom/Modules` |

## Features

- **Auto-reconnect**: Automatic retry with exponential backoff on connection loss
- **Heartbeat**: 30-second connection monitoring
- **Shutdown detection**: Graceful handling when Lightroom exits
- **3 output formats**: `text` / `json` / `table`
- **Tab completion**: Develop parameter name completion
- **Per-command timeout**: Automatic timeout extension for long operations

## Development

```bash
# Development install
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ -v --cov=lightroom_sdk --cov=cli

# Single test file
python -m pytest tests/integration/test_cli_develop.py -v
```

## Project Structure

```
lightroom-cli/
├── cli/                      # Click CLI application
│   ├── main.py               # Entry point (lr command)
│   ├── output.py             # OutputFormatter (json/text/table)
│   ├── helpers.py            # bridge_command decorator
│   ├── completions.py        # Tab completion
│   └── commands/             # Command groups
│       ├── system.py         # lr system
│       ├── catalog.py        # lr catalog
│       ├── develop.py        # lr develop
│       ├── preview.py        # lr preview
│       ├── selection.py      # lr selection
│       └── plugin.py         # lr plugin
├── lightroom_sdk/            # Python SDK
│   ├── paths.py              # OS-agnostic path resolution
│   ├── client.py             # LightroomClient
│   ├── socket_bridge.py      # Dual TCP sockets
│   ├── resilient_bridge.py   # Auto-reconnect + heartbeat
│   ├── retry.py              # Per-command timeout
│   └── protocol.py           # JSON-RPC protocol
├── lightroom-plugin/         # Lua plugin (16 files)
│   ├── PluginInit.lua        # Command router (107 commands)
│   ├── PlatformPaths.lua     # OS-agnostic path resolution
│   ├── SimpleSocketBridge.lua # TCP server
│   ├── DevelopModule.lua     # Develop operations
│   ├── CatalogModule.lua     # Catalog operations
│   ├── SelectionModule.lua   # Selection operations
│   └── PreviewModule.lua     # Preview operations
├── tests/                    # pytest test suite (165+ tests)
└── homebrew/                 # Homebrew Formula template
```

## Requirements

- Python >= 3.10
- Adobe Lightroom Classic
- macOS

### Python Dependencies

- [click](https://click.palletsprojects.com/) >= 8.1 — CLI framework
- [rich](https://rich.readthedocs.io/) >= 13.0 — Table output
- [pydantic](https://docs.pydantic.dev/) >= 2.0 — Data validation
- [platformdirs](https://platformdirs.readthedocs.io/) >= 3.0 — OS-standard paths

## License

[MIT](LICENSE)
```

**Step 2: テスト通過を確認**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

**Step 3: コミット**

```bash
git add README.md
git commit -m "docs: rewrite README.md in English"
```

---

## Phase 6: SKILLS.md

### Task 18: SKILLS.md の作成

**Files:**
- Create: `SKILLS.md`

**Step 1: SKILLS.md を作成**

```markdown
# Lightroom CLI Skills for Claude Code

## Prerequisites

- lightroom-cli installed (`lr --version` to verify)
- Lightroom Classic running with plugin active
- Connection verified (`lr system check-connection`)

## Available Modules

### system — Connection & status

| Command | Description |
|---------|-------------|
| `lr system ping` | Quick connectivity test |
| `lr system status` | Plugin status and uptime |
| `lr system check-connection` | Detailed connection check |
| `lr system reconnect` | Force reconnection |

### catalog — Photo management

| Command | Description |
|---------|-------------|
| `lr catalog get-selected` | Get currently selected photos |
| `lr catalog list --limit N` | List photos |
| `lr catalog search "keyword"` | Search photos by keyword |
| `lr catalog get-info PHOTO_ID` | Get detailed metadata |
| `lr catalog set-rating PHOTO_ID N` | Set star rating (0-5) |
| `lr catalog add-keywords PHOTO_ID kw1 kw2` | Add keywords |
| `lr catalog set-title PHOTO_ID "title"` | Set title |
| `lr catalog collections` | List collections |
| `lr catalog create-collection "name"` | Create collection |
| `lr catalog keywords` | List all keywords |
| `lr catalog rotate-left` | Rotate photo left |
| `lr catalog create-virtual-copy` | Create virtual copy |

### develop — Image editing

| Command | Description |
|---------|-------------|
| `lr develop get-settings` | Get all develop settings |
| `lr develop set PARAM VALUE [PARAM VALUE ...]` | Set parameters |
| `lr develop get PARAM` | Get single parameter |
| `lr develop auto-tone` | Apply AutoTone |
| `lr develop auto-wb` | Apply Auto White Balance |
| `lr develop reset` | Reset to defaults |
| `lr develop apply '{"Exposure": 1.0}'` | Apply JSON settings |
| `lr develop copy-settings` | Copy develop settings |
| `lr develop paste-settings` | Paste develop settings |
| `lr develop preset "name"` | Apply preset |
| `lr develop snapshot "name"` | Create snapshot |

#### Tone Curve

| Command | Description |
|---------|-------------|
| `lr develop curve get` | Get curve points |
| `lr develop curve set '[[0,0],[128,140],[255,255]]'` | Set curve |
| `lr develop curve s-curve` | Apply S-curve preset |
| `lr develop curve linear` | Reset to linear |
| `lr develop curve add-point X Y` | Add point |

#### Masking

| Command | Description |
|---------|-------------|
| `lr develop mask list` | List all masks |
| `lr develop mask create` | Create new mask |
| `lr develop mask add brush` | Add brush to mask |
| `lr develop mask intersect luminance` | Intersect mask |
| `lr develop mask subtract color` | Subtract from mask |
| `lr develop mask invert MASK_ID` | Invert mask |

#### Filters

| Command | Description |
|---------|-------------|
| `lr develop filter graduated` | Graduated filter |
| `lr develop filter radial` | Radial filter |
| `lr develop filter brush` | Brush filter |
| `lr develop filter ai-select` | AI selection |

#### Local Adjustments

| Command | Description |
|---------|-------------|
| `lr develop local set PARAM VALUE` | Set local parameter |
| `lr develop local get PARAM` | Get local parameter |

### preview — Image preview generation

| Command | Description |
|---------|-------------|
| `lr preview generate-current` | Generate preview for selected photo |
| `lr preview generate --size 2048` | Generate with size |
| `lr preview generate-batch` | Batch generate |
| `lr preview info` | Get preview info |

### selection — Navigation & flagging

| Command | Description |
|---------|-------------|
| `lr selection flag` | Set Pick flag |
| `lr selection reject` | Set Reject flag |
| `lr selection unflag` | Remove flag |
| `lr selection get-flag` | Get flag status |
| `lr selection set-rating N` | Set rating (0-5) |
| `lr selection get-rating` | Get rating |
| `lr selection color-label COLOR` | Set color label |
| `lr selection get-color-label` | Get color label |
| `lr selection next` | Next photo |
| `lr selection previous` | Previous photo |
| `lr selection select-all` | Select all |
| `lr selection select-none` | Deselect all |

### plugin — Plugin management

| Command | Description |
|---------|-------------|
| `lr plugin install` | Install plugin (copy) |
| `lr plugin install --dev` | Install plugin (symlink) |
| `lr plugin uninstall` | Remove plugin |
| `lr plugin status` | Check install status |

## Common Workflows

### Batch rate photos by content analysis

```bash
# 1. Get selected photos
lr -o json catalog get-selected

# 2. For each photo, generate preview for analysis
lr preview generate-current

# 3. Set rating based on analysis
lr catalog set-rating PHOTO_ID 5
```

### Apply consistent edits across photos

```bash
# 1. Get settings from reference photo
lr -o json develop get-settings

# 2. Apply to target photos
lr develop apply '{"Exposure": 1.0, "Contrast": 25}'
```

### Organize photos with keywords and collections

```bash
# 1. Search for photos
lr -o json catalog search "sunset"

# 2. Add keywords
lr catalog add-keywords PHOTO_ID sunset landscape golden-hour

# 3. Create and populate collection
lr catalog create-collection "Best Sunsets"
```

### Quick culling workflow

```bash
# Navigate and rate
lr selection next
lr selection set-rating 3
lr selection next
lr selection reject
lr selection next
lr selection flag
```

## Output Formats

All commands support `-o json` for machine-readable output:

```bash
lr -o json develop get-settings    # Full JSON
lr -o table catalog list           # Table format
lr develop get-settings            # Human-readable text
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LR_PORT_FILE` | Port file path | `/tmp/lightroom_ports.txt` |
| `LR_PLUGIN_DIR` | Lightroom Modules dir | Auto-detected |

## Error Handling

- Connection errors: The CLI auto-retries with exponential backoff
- Timeout: Use `-t SECONDS` to increase timeout for slow operations
- Plugin not running: `lr system check-connection` for diagnostics
```

**Step 2: コミット**

```bash
git add SKILLS.md
git commit -m "docs: add SKILLS.md for Claude Code integration"
```

---

## Phase 7: E2E テスト

### Task 19: E2E テスト基盤の作成

**Files:**
- Create: `tests/e2e/__init__.py`
- Create: `tests/e2e/conftest.py`

**Step 1: ディレクトリとファイル作成**

```python
# tests/e2e/__init__.py
```

```python
# tests/e2e/conftest.py
"""E2E テスト用の共通フィクスチャ。

E2E テストは Lightroom Classic が起動中でプラグインがアクティブな環境でのみ実行可能。
CI では実行不可。

実行方法:
    pytest tests/e2e/ -v -m e2e
"""
import pytest
import asyncio
from lightroom_sdk.paths import get_port_file


def pytest_collection_modifyitems(config, items):
    """e2e マーカーが付いたテストにスキップ条件を追加"""
    port_file = get_port_file()
    if not port_file.exists():
        skip_e2e = pytest.mark.skip(
            reason=f"Lightroom not running (port file not found: {port_file})"
        )
        for item in items:
            if "e2e" in item.keywords:
                item.add_marker(skip_e2e)


@pytest.fixture
def lr_bridge():
    """Lightroom への実接続を確立するフィクスチャ"""
    from lightroom_sdk.resilient_bridge import ResilientSocketBridge

    bridge = ResilientSocketBridge()
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(bridge.connect())
        yield bridge, loop
    finally:
        loop.run_until_complete(bridge.disconnect())
        loop.close()
```

**Step 2: コミット**

```bash
git add tests/e2e/__init__.py tests/e2e/conftest.py
git commit -m "feat: add E2E test infrastructure (conftest with auto-skip)"
```

---

### Task 20: E2E テスト — plugin コマンド

**Files:**
- Create: `tests/e2e/test_plugin_workflow.py`

**Step 1: テスト作成**

```python
# tests/e2e/test_plugin_workflow.py
"""lr plugin コマンドの E2E テスト。

Lightroom 不要 — ファイルシステム操作のみ。
"""
import pytest
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.mark.e2e
class TestPluginWorkflow:
    """プラグインのインストール→ステータス→アンインストールの完全ワークフロー"""

    def test_full_lifecycle(self, tmp_path, monkeypatch, runner):
        """install -> status -> uninstall -> status"""
        modules_dir = tmp_path / "Modules"
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))

        # Install
        result = runner.invoke(cli, ["plugin", "install"])
        assert result.exit_code == 0
        assert "installed" in result.output.lower()

        # Status (installed)
        result = runner.invoke(cli, ["plugin", "status"])
        assert result.exit_code == 0
        assert "copy" in result.output.lower()

        # Uninstall
        result = runner.invoke(cli, ["plugin", "uninstall"])
        assert result.exit_code == 0
        assert "uninstalled" in result.output.lower()

        # Status (not installed)
        result = runner.invoke(cli, ["plugin", "status"])
        assert result.exit_code == 0
        assert "not installed" in result.output.lower()

    def test_dev_mode_lifecycle(self, tmp_path, monkeypatch, runner):
        """install --dev -> status -> uninstall"""
        modules_dir = tmp_path / "Modules"
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))

        # Install (dev)
        result = runner.invoke(cli, ["plugin", "install", "--dev"])
        assert result.exit_code == 0
        assert "symlink" in result.output.lower()

        # Status
        result = runner.invoke(cli, ["plugin", "status"])
        assert result.exit_code == 0
        assert "symlink" in result.output.lower()

        # Uninstall
        result = runner.invoke(cli, ["plugin", "uninstall"])
        assert result.exit_code == 0
```

**Step 2: テスト通過を確認**

Run: `python -m pytest tests/e2e/test_plugin_workflow.py -v`
Expected: PASS（ポートファイルがなくてもスキップされるだけ。ただし plugin テストは Lightroom 不要なのでスキップされない場合は PASS）

注意: conftest.py の `pytest_collection_modifyitems` は `e2e` マーカーが付いたテストのみスキップ。ポートファイルが存在しない場合にスキップされる。plugin テストはファイルシステムのみなので、環境変数でパスを上書きすれば常に実行可能。

---

### Task 21: E2E テスト — Lightroom 実機テスト

**Files:**
- Create: `tests/e2e/test_lightroom_commands.py`

**Step 1: テスト作成**

```python
# tests/e2e/test_lightroom_commands.py
"""Lightroom Classic 実機接続テスト。

Lightroom Classic が起動中でプラグインがアクティブな場合のみ実行可能。
ポートファイルが存在しない場合は自動スキップ。

実行: pytest tests/e2e/test_lightroom_commands.py -v -m e2e
"""
import pytest


@pytest.mark.e2e
class TestSystemCommands:
    """system モジュールの実機テスト"""

    def test_ping(self, lr_bridge):
        bridge, loop = lr_bridge
        result = loop.run_until_complete(
            bridge.send_command("system.ping", timeout=5.0)
        )
        assert result.get("success") is True

    def test_status(self, lr_bridge):
        bridge, loop = lr_bridge
        result = loop.run_until_complete(
            bridge.send_command("system.status", timeout=5.0)
        )
        assert result.get("success") is True
        assert "result" in result


@pytest.mark.e2e
class TestCatalogCommands:
    """catalog モジュールの実機テスト"""

    def test_get_selected_photos(self, lr_bridge):
        bridge, loop = lr_bridge
        result = loop.run_until_complete(
            bridge.send_command("catalog.getSelectedPhotos", timeout=10.0)
        )
        assert result.get("success") is True

    def test_get_active_catalog(self, lr_bridge):
        bridge, loop = lr_bridge
        result = loop.run_until_complete(
            bridge.send_command("catalog.getActiveCatalog", timeout=10.0)
        )
        assert result.get("success") is True


@pytest.mark.e2e
class TestDevelopCommands:
    """develop モジュールの実機テスト"""

    def test_get_settings(self, lr_bridge):
        """現像設定の取得（写真が選択されている前提）"""
        bridge, loop = lr_bridge
        result = loop.run_until_complete(
            bridge.send_command("develop.getSettings", timeout=10.0)
        )
        # 写真未選択の場合は error が返る可能性があるが、接続自体は成功
        assert "success" in result or "error" in result

    def test_get_single_param(self, lr_bridge):
        """単一パラメータの取得"""
        bridge, loop = lr_bridge
        result = loop.run_until_complete(
            bridge.send_command(
                "develop.getValue",
                params={"param": "Exposure"},
                timeout=10.0,
            )
        )
        assert "success" in result or "error" in result


@pytest.mark.e2e
class TestSelectionCommands:
    """selection モジュールの実機テスト"""

    def test_get_rating(self, lr_bridge):
        bridge, loop = lr_bridge
        result = loop.run_until_complete(
            bridge.send_command("selection.getRating", timeout=10.0)
        )
        assert "success" in result or "error" in result

    def test_get_flag(self, lr_bridge):
        bridge, loop = lr_bridge
        result = loop.run_until_complete(
            bridge.send_command("selection.getFlag", timeout=10.0)
        )
        assert "success" in result or "error" in result


@pytest.mark.e2e
class TestPreviewCommands:
    """preview モジュールの実機テスト"""

    def test_get_preview_info(self, lr_bridge):
        bridge, loop = lr_bridge
        result = loop.run_until_complete(
            bridge.send_command("preview.getInfo", timeout=15.0)
        )
        assert "success" in result or "error" in result
```

**Step 2: テスト通過を確認**

Lightroom 未起動時:
Run: `python -m pytest tests/e2e/test_lightroom_commands.py -v`
Expected: ALL SKIPPED (ポートファイルが存在しないため)

Lightroom 起動時:
Run: `python -m pytest tests/e2e/test_lightroom_commands.py -v -m e2e`
Expected: PASS

**Step 3: 通常テストが E2E を除外することを確認**

Run: `python -m pytest tests/ -v -m "not e2e"`
Expected: ALL PASS (165+ tests, 0 e2e)

**Step 4: コミット**

```bash
git add tests/e2e/test_plugin_workflow.py tests/e2e/test_lightroom_commands.py
git commit -m "feat: add E2E tests for plugin workflow and Lightroom commands"
```

---

## 最終確認

### Task 22: 全テスト通過確認 & タグ準備

**Step 1: 全テスト実行**

Run:
```bash
pip install -e ".[dev]"
python -m pytest tests/ -v -m "not e2e" --cov=lightroom_sdk --cov=cli
```

Expected: ALL PASS, coverage report generated

**Step 2: lr コマンドの動作確認**

Run:
```bash
lr --version
lr --help
lr plugin --help
lr plugin status
```

Expected: バージョン表示、ヘルプ表示、プラグインステータス表示

**Step 3: 配布パッケージビルド確認**

Run:
```bash
pip install build
python -m build --sdist
```

Expected: dist/ に tarball が生成される

---

## 変更箇所サマリー

### 新規ファイル

| ファイル | 目的 |
|---------|------|
| `lightroom_sdk/paths.py` | OS 横断パス抽象化 |
| `lightroom-plugin/PlatformPaths.lua` | Lua 側パス抽象化 |
| `cli/commands/plugin.py` | lr plugin install/uninstall/status |
| `homebrew/lightroom-cli.rb` | Homebrew Formula テンプレート |
| `README.ja.md` | 日本語 README |
| `SKILLS.md` | Claude Code 用スキルファイル |
| `tests/test_paths.py` | paths.py のユニットテスト |
| `tests/test_cli_plugin.py` | plugin コマンドのテスト |
| `tests/e2e/__init__.py` | E2E テストパッケージ |
| `tests/e2e/conftest.py` | E2E テスト共通フィクスチャ |
| `tests/e2e/test_plugin_workflow.py` | プラグイン E2E テスト |
| `tests/e2e/test_lightroom_commands.py` | Lightroom 実機 E2E テスト |

### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `lightroom_sdk/socket_bridge.py:14` | port_file デフォルトを `None` に変更、paths.py に委譲 |
| `lightroom_sdk/resilient_bridge.py:25` | port_file デフォルトを `None` に変更、paths.py に委譲 |
| `cli/commands/system.py:7,86` | ハードコードパスを paths.py に委譲 |
| `cli/main.py:33` | plugin グループを登録 |
| `scripts/check-connection.py:7` | paths.get_port_file() を使用 |
| `lightroom-plugin/SimpleSocketBridge.lua:71,338-339,438-439` | PlatformPaths.lua を使用 |
| `pyproject.toml` | platformdirs 追加、classifiers、package-data、pytest 設定統合 |
| `.gitignore` | docs/plans/ 追加、/tmp パス削除 |
| `README.md` | 英語化 |

### 削除ファイル

| ファイル | 理由 |
|---------|------|
| `pytest.ini` | pyproject.toml に統合 |
