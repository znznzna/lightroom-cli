# Lightroom CLI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** MCP serverを廃止し、Lua Plugin + Python SDK + CLIの3層構成でLightroom Classicをコマンドラインから操作できるツールを構築する
**Architecture:** LightroomのプログラマブルインターフェースであるLuaプラグインがTCPソケットで通信し、Python SDKがその通信を抽象化し、ClickベースのCLIがユーザーインターフェースを提供する。MCPサーバー層は廃止。
**Tech Stack:** Python 3.10+, Click 8.x, Rich 13.x, pytest + pytest-asyncio, Lua (Lightroom SDK)

---

## Architecture Overview

```
[Lightroom Classic]
    └─ Lua Plugin (lightroom-python-bridge.lrdevplugin/)  ← shuttingDownフラグ追加
           ↕ TCP Socket
[Python SDK] (lightroom_sdk/)
    ├─ socket_bridge.py     ← on_event()追加
    ├─ resilient_bridge.py  ← 新規: 状態マシン・ハートビート・再接続
    ├─ retry.py             ← 新規: タイムアウト設定
    └─ client.py            ← time.sleep(0.1)削除
[CLI] (cli/)
    ├─ main.py
    ├─ output.py
    └─ commands/{system,catalog,develop,preview}.py
```

削除: `mcp_server/` 全体

---

## Phase 1: SDK安定化 + テスト基盤

---

### Task 1: MockLightroomServer 作成

**Files:**
- Create: `tests/mocks/__init__.py`
- Create: `tests/mocks/lightroom_mock.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Test: `tests/test_mock_server.py`

**Step 1: 失敗するテストを書く**
```python
# tests/test_mock_server.py
import asyncio
import json
import pytest

@pytest.mark.asyncio
async def test_mock_server_responds_to_command(mock_lr_server):
    """MockServerがコマンドに応答できることを検証"""
    mock_lr_server.register_response("system.ping", {"status": "ok"})

    # ポートファイルからポート取得
    ports = mock_lr_server.port_file.read_text().strip().split(",")
    sender_port, receiver_port = int(ports[0]), int(ports[1])

    # receiver_portに接続してコマンド送信（LRのreceiver = Python側のsend先）
    _, writer = await asyncio.open_connection("localhost", receiver_port)
    reader, _ = await asyncio.open_connection("localhost", sender_port)

    request = {"id": "test-1", "command": "system.ping", "params": {}}
    writer.write(json.dumps(request).encode() + b"\n")
    await writer.drain()

    data = await asyncio.wait_for(reader.readline(), timeout=5.0)
    response = json.loads(data)

    assert response["id"] == "test-1"
    assert response["success"] is True
    assert response["result"]["status"] == "ok"
    writer.close()


@pytest.mark.asyncio
async def test_mock_server_sends_event(mock_lr_server):
    """MockServerがイベントをpushできることを検証"""
    ports = mock_lr_server.port_file.read_text().strip().split(",")
    sender_port = int(ports[0])

    reader, _ = await asyncio.open_connection("localhost", sender_port)

    mock_lr_server.send_event("photo.selected", {"photoId": "abc"})

    data = await asyncio.wait_for(reader.readline(), timeout=5.0)
    event = json.loads(data)

    assert event["event"] == "photo.selected"
    assert event["data"]["photoId"] == "abc"
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/test_mock_server.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'tests.mocks')

**Step 3: 実装**
```python
# tests/mocks/lightroom_mock.py
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Callable, Optional

class MockLightroomServer:
    """デュアルTCPソケットのLightroomプラグインモック"""

    def __init__(self, port_file: str = "/tmp/lightroom_ports_test.txt"):
        self.port_file = Path(port_file)
        self._responses: Dict[str, Any] = {}
        self._sender_server: Optional[asyncio.Server] = None  # LR→Python
        self._receiver_server: Optional[asyncio.Server] = None  # Python→LR
        self._sender_writers: list[asyncio.StreamWriter] = []
        self._sender_port = 0
        self._receiver_port = 0

    def register_response(self, command: str, result: Any) -> None:
        self._responses[command] = result

    async def _handle_receiver(self, reader, writer):
        """Python→LRチャネル: コマンド受信→レスポンス送信（sender経由）"""
        buffer = b""
        while True:
            chunk = await reader.read(8192)
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                msg = json.loads(line)
                result = self._responses.get(msg["command"], {})
                resp = {"id": msg["id"], "success": True, "result": result}
                for w in self._sender_writers:
                    w.write(json.dumps(resp).encode() + b"\n")
                    await w.drain()

    async def _handle_sender(self, reader, writer):
        """LR→Pythonチャネル: senderクライアント登録"""
        self._sender_writers.append(writer)
        try:
            await reader.read()  # 接続維持
        finally:
            self._sender_writers.remove(writer)

    def send_event(self, event_name: str, data: Dict[str, Any]) -> None:
        event = {"event": event_name, "data": data}
        payload = json.dumps(event).encode() + b"\n"
        for w in self._sender_writers:
            w.write(payload)
            # drain()はsync contextから呼べないのでbufferに入れるだけ

    async def start(self) -> None:
        self._sender_server = await asyncio.start_server(
            self._handle_sender, "localhost", 0
        )
        self._receiver_server = await asyncio.start_server(
            self._handle_receiver, "localhost", 0
        )
        self._sender_port = self._sender_server.sockets[0].getsockname()[1]
        self._receiver_port = self._receiver_server.sockets[0].getsockname()[1]
        self.port_file.write_text(f"{self._sender_port},{self._receiver_port}")

    async def stop(self) -> None:
        for s in [self._sender_server, self._receiver_server]:
            if s:
                s.close()
                await s.wait_closed()
        if self.port_file.exists():
            self.port_file.unlink()

# tests/conftest.py
import pytest
from tests.mocks.lightroom_mock import MockLightroomServer

@pytest.fixture
async def mock_lr_server():
    server = MockLightroomServer()
    await server.start()
    yield server
    await server.stop()
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/test_mock_server.py -v`
Expected: PASS

**Step 5: コミット**
```
git add tests/__init__.py tests/mocks/__init__.py tests/mocks/lightroom_mock.py tests/conftest.py tests/test_mock_server.py
git commit -m "feat: add MockLightroomServer for dual-TCP testing (enable offline SDK testing)"
```

---

### Task 2: socket_bridge.py にイベントハンドリング追加

**Files:**
- Modify: `lightroom_sdk/socket_bridge.py`
- Test: `tests/test_socket_bridge_events.py`

**Step 1: 失敗するテストを書く**
```python
# tests/test_socket_bridge_events.py
import asyncio
import pytest
from lightroom_sdk.socket_bridge import SocketBridge

@pytest.mark.asyncio
async def test_on_event_registers_and_fires(mock_lr_server):
    """on_event()で登録したハンドラがイベント受信時に呼ばれる"""
    received = []

    bridge = SocketBridge(
        port_file=str(mock_lr_server.port_file)
    )
    bridge.on_event("photo.selected", lambda data: received.append(data))

    await bridge.connect(retry_attempts=1)

    # MockServerからイベント送信
    mock_lr_server.send_event("photo.selected", {"photoId": "123"})
    await asyncio.sleep(0.3)

    assert len(received) == 1
    assert received[0]["photoId"] == "123"
    await bridge.disconnect()


@pytest.mark.asyncio
async def test_unregistered_event_ignored(mock_lr_server):
    """未登録イベントがエラーにならないことを検証"""
    bridge = SocketBridge(port_file=str(mock_lr_server.port_file))
    await bridge.connect(retry_attempts=1)

    mock_lr_server.send_event("unknown.event", {})
    await asyncio.sleep(0.3)
    # エラーが発生しなければOK

    await bridge.disconnect()
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/test_socket_bridge_events.py -v`
Expected: FAIL (AttributeError: 'SocketBridge' object has no attribute 'on_event')

**Step 3: 実装**
```python
# lightroom_sdk/socket_bridge.py - 変更箇所のみ

class SocketBridge:
    def __init__(self, host: str = 'localhost', port_file: str = '/tmp/lightroom_ports.txt'):
        # ... (既存コード)
        self._event_handlers: Dict[str, list[Callable]] = {}  # 追加

    def on_event(self, event_name: str, handler: Callable) -> None:
        """イベントハンドラを登録"""
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(handler)

    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """Route received messages to appropriate handlers"""
        if 'event' in message:
            event_name = message['event']
            logger.debug(f"Event received: {event_name}")
            for handler in self._event_handlers.get(event_name, []):
                try:
                    handler(message.get('data', {}))
                except Exception as e:
                    logger.error(f"Event handler error for {event_name}: {e}")
            return

        # ... (既存のレスポンスハンドリングはそのまま)
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/test_socket_bridge_events.py -v`
Expected: PASS

**Step 5: コミット**
```
git add lightroom_sdk/socket_bridge.py tests/test_socket_bridge_events.py
git commit -m "feat: add on_event() to SocketBridge (enable event-driven communication)"
```

---

### Task 3: ResilientSocketBridge 新規作成

**Files:**
- Create: `lightroom_sdk/resilient_bridge.py`
- Test: `tests/test_resilient_bridge.py`

**Step 1: 失敗するテストを書く**
```python
# tests/test_resilient_bridge.py
import asyncio
import pytest
from lightroom_sdk.resilient_bridge import ResilientSocketBridge, ConnectionState

@pytest.mark.asyncio
async def test_initial_state_is_disconnected():
    bridge = ResilientSocketBridge(port_file="/tmp/nonexistent.txt")
    assert bridge.state == ConnectionState.DISCONNECTED


@pytest.mark.asyncio
async def test_connect_transitions_to_connected(mock_lr_server):
    mock_lr_server.register_response("system.ping", {"status": "ok"})
    bridge = ResilientSocketBridge(
        port_file=str(mock_lr_server.port_file)
    )
    await bridge.connect()
    assert bridge.state == ConnectionState.CONNECTED
    await bridge.disconnect()


@pytest.mark.asyncio
async def test_auto_reconnect_on_send_failure(mock_lr_server):
    """接続断後のsend_command()が自動再接続する"""
    mock_lr_server.register_response("system.ping", {"status": "ok"})
    bridge = ResilientSocketBridge(
        port_file=str(mock_lr_server.port_file),
        max_reconnect_attempts=2,
        heartbeat_interval=0,  # テスト用: ハートビート無効
    )
    await bridge.connect()

    # 内部bridgeを強制切断
    bridge._bridge._connected = False

    # send_commandが自動再接続を試みる
    result = await bridge.send_command("system.ping")
    assert result["result"]["status"] == "ok"
    assert bridge.state == ConnectionState.CONNECTED
    await bridge.disconnect()


@pytest.mark.asyncio
async def test_shutdown_event_transitions_to_shutdown(mock_lr_server):
    """server.shutdownイベントでSHUTDOWN状態になる"""
    bridge = ResilientSocketBridge(
        port_file=str(mock_lr_server.port_file),
        heartbeat_interval=0,
    )
    await bridge.connect()

    mock_lr_server.send_event("server.shutdown", {"reason": "test"})
    await asyncio.sleep(0.3)

    assert bridge.state == ConnectionState.SHUTDOWN
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/test_resilient_bridge.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'lightroom_sdk.resilient_bridge')

**Step 3: 実装**
```python
# lightroom_sdk/resilient_bridge.py
import asyncio
import enum
import logging
from typing import Optional, Dict, Any, Callable

from .socket_bridge import SocketBridge

logger = logging.getLogger(__name__)

class ConnectionState(enum.Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    SHUTDOWN = "shutdown"

class ResilientSocketBridge:
    """自動再接続・ハートビート付きSocketBridgeラッパー"""

    def __init__(
        self,
        host: str = "localhost",
        port_file: str = "/tmp/lightroom_ports.txt",
        max_reconnect_attempts: int = 5,
        heartbeat_interval: float = 30.0,
    ):
        self._host = host
        self._port_file = port_file
        self._max_reconnect = max_reconnect_attempts
        self._heartbeat_interval = heartbeat_interval
        self._bridge: Optional[SocketBridge] = None
        self._state = ConnectionState.DISCONNECTED
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._event_handlers: Dict[str, list[Callable]] = {}

    @property
    def state(self) -> ConnectionState:
        return self._state

    def on_event(self, event_name: str, handler: Callable) -> None:
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(handler)

    async def connect(self) -> None:
        self._state = ConnectionState.CONNECTING
        self._bridge = SocketBridge(self._host, self._port_file)

        # イベントハンドラを転送
        for name, handlers in self._event_handlers.items():
            for h in handlers:
                self._bridge.on_event(name, h)

        # シャットダウンイベント監視
        self._bridge.on_event("server.shutdown", self._handle_shutdown_event)

        await self._bridge.connect(retry_attempts=1)
        self._state = ConnectionState.CONNECTED

        if self._heartbeat_interval > 0:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def send_command(self, command: str, params=None, timeout=30.0):
        if self._state == ConnectionState.SHUTDOWN:
            raise ConnectionError("Lightroom is shutting down")

        try:
            return await self._bridge.send_command(command, params, timeout)
        except Exception:
            if self._state == ConnectionState.SHUTDOWN:
                raise
            await self._reconnect()
            return await self._bridge.send_command(command, params, timeout)

    async def _reconnect(self) -> None:
        self._state = ConnectionState.RECONNECTING
        delay = 1.0
        for attempt in range(self._max_reconnect):
            try:
                self._bridge = SocketBridge(self._host, self._port_file)
                for name, handlers in self._event_handlers.items():
                    for h in handlers:
                        self._bridge.on_event(name, h)
                self._bridge.on_event("server.shutdown", self._handle_shutdown_event)
                await self._bridge.connect(retry_attempts=1)
                self._state = ConnectionState.CONNECTED
                return
            except Exception:
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30.0)
        self._state = ConnectionState.DISCONNECTED
        raise ConnectionError("Reconnection failed")

    # ... (heartbeat_loop, disconnect, _handle_shutdown_event 実装省略)

    def _handle_shutdown_event(self, data: Dict[str, Any]) -> None:
        logger.info(f"Shutdown event received: {data}")
        self._state = ConnectionState.SHUTDOWN

    async def disconnect(self) -> None:
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._bridge:
            await self._bridge.disconnect()
        self._state = ConnectionState.DISCONNECTED

    async def _heartbeat_loop(self) -> None:
        while self._state == ConnectionState.CONNECTED:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                await self._bridge.send_command("system.ping", timeout=5.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/test_resilient_bridge.py -v`
Expected: PASS

**Step 5: コミット**
```
git add lightroom_sdk/resilient_bridge.py tests/test_resilient_bridge.py
git commit -m "feat: add ResilientSocketBridge with state machine and auto-reconnect (improve connection reliability)"
```

---

### Task 4: retry.py 新規作成

**Files:**
- Create: `lightroom_sdk/retry.py`
- Test: `tests/test_retry.py`

**Step 1: 失敗するテストを書く**
```python
# tests/test_retry.py
import pytest
from lightroom_sdk.retry import RetryConfig, get_timeout

def test_exact_command_timeout():
    assert get_timeout("system.ping") == 5.0

def test_wildcard_command_timeout():
    assert get_timeout("preview.generate") == 120.0
    assert get_timeout("preview.get_info") == 120.0

def test_default_timeout():
    assert get_timeout("unknown.command") == 30.0

def test_retry_config_defaults():
    cfg = RetryConfig()
    assert cfg.max_retries == 3
    assert cfg.backoff_factor == 2.0
    assert cfg.max_delay == 30.0

def test_retry_config_custom():
    cfg = RetryConfig(max_retries=5, initial_delay=0.5)
    assert cfg.max_retries == 5
    assert cfg.initial_delay == 0.5
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/test_retry.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'lightroom_sdk.retry')

**Step 3: 実装**
```python
# lightroom_sdk/retry.py
import fnmatch
from dataclasses import dataclass, field

COMMAND_TIMEOUTS: dict[str, float] = {
    "system.ping": 5.0,
    "system.status": 5.0,
    "system.reconnect": 10.0,
    "preview.*": 120.0,
    "develop.set_parameter": 10.0,
    "develop.set_parameters": 15.0,
    "develop.get_current_settings": 10.0,
    "catalog.search_photos": 60.0,
    "catalog.get_all_photos": 60.0,
}

DEFAULT_TIMEOUT = 30.0

def get_timeout(command: str) -> float:
    """コマンド名に対応するタイムアウト値を返す（ワイルドカード対応）"""
    if command in COMMAND_TIMEOUTS:
        return COMMAND_TIMEOUTS[command]
    for pattern, timeout in COMMAND_TIMEOUTS.items():
        if fnmatch.fnmatch(command, pattern):
            return timeout
    return DEFAULT_TIMEOUT

@dataclass
class RetryConfig:
    max_retries: int = 3
    initial_delay: float = 1.0
    backoff_factor: float = 2.0
    max_delay: float = 30.0
    retryable_exceptions: tuple = field(default_factory=lambda: (ConnectionError, TimeoutError))
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/test_retry.py -v`
Expected: PASS

**Step 5: コミット**
```
git add lightroom_sdk/retry.py tests/test_retry.py
git commit -m "feat: add retry.py with command-specific timeouts (prevent preview timeouts and enable fine-grained control)"
```

---

### Task 5: client.py 修正 + Luaシャットダウン修正

**Files:**
- Modify: `lightroom_sdk/client.py`
- Modify: `lightroom-python-bridge.lrdevplugin/SimpleSocketBridge.lua`
- Modify: `lightroom-python-bridge.lrdevplugin/AppShutdown.lua`
- Modify: `lightroom-python-bridge.lrdevplugin/PluginShutdown.lua`
- Test: `tests/test_client.py`

**Step 1: 失敗するテストを書く**
```python
# tests/test_client.py
import asyncio
import time
import pytest
from lightroom_sdk.client import LightroomClient

@pytest.mark.asyncio
async def test_execute_command_no_blocking_sleep(mock_lr_server):
    """time.sleep(0.1)が削除され、コマンド実行がブロックしないことを検証"""
    mock_lr_server.register_response("system.ping", {"status": "ok"})

    client = LightroomClient.__new__(LightroomClient)
    from lightroom_sdk.socket_bridge import SocketBridge
    client._bridge = SocketBridge(port_file=str(mock_lr_server.port_file))
    await client._bridge.connect(retry_attempts=1)

    start = time.monotonic()
    for _ in range(10):
        await client.execute_command("system.ping")
    elapsed = time.monotonic() - start

    # 10回実行して1秒未満ならsleep(0.1)が除去されている
    assert elapsed < 1.0, f"10 commands took {elapsed:.2f}s (expected <1.0s without sleep)"
    await client.disconnect()


@pytest.mark.asyncio
async def test_ping_returns_result(mock_lr_server):
    """ping()がresultを返すことを検証"""
    mock_lr_server.register_response("system.ping", {"status": "ok"})

    client = LightroomClient.__new__(LightroomClient)
    from lightroom_sdk.socket_bridge import SocketBridge
    client._bridge = SocketBridge(port_file=str(mock_lr_server.port_file))
    await client._bridge.connect(retry_attempts=1)

    result = await client.ping()
    assert result["status"] == "ok"
    await client.disconnect()
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/test_client.py -v`
Expected: FAIL (10回実行が1秒以上かかる = sleep(0.1)が残っている)

**Step 3: 実装**

**client.py変更（Python）:**
```python
# lightroom_sdk/client.py - execute_command メソッドのみ
    async def execute_command(self, command, params=None, timeout=30.0):
        response = await self._bridge.send_command(command, params, timeout)
        lr_response = LightroomResponse(**response)
        if not lr_response.success:
            error = lr_response.error or {}
            error_code = error.get('code', 'UNKNOWN')
            error_message = error.get('message', 'Unknown error')
            exception_class = ERROR_CODE_MAP.get(error_code, LightroomSDKError)
            raise exception_class(error_message, code=error_code, details=error)
        # time.sleep(0.1) を削除
        return lr_response.result or {}
```

**SimpleSocketBridge.lua変更（onClosed/onError）:**
```lua
-- onClosed に shuttingDown チェック追加
onClosed = function(socket)
    logger:info("Sender socket closed")
    local bridge = _G.LightroomPythonBridge
    if bridge and bridge.shuttingDown then
        logger:info("shuttingDown=true, not restarting")
        return
    end
    if bridge and bridge.socketServerRunning then
        restartSocketServer()
    end
end,
-- onError も同様のパターン
```

**AppShutdown.lua変更:**
```lua
-- AppShutdown.lua - shuttingDownフラグ + 二重実行防止
if bridge then
    if bridge.shuttingDown then
        logger:info("App shutdown already in progress - skipping")
        return  -- 二重実行防止
    end
    bridge.shuttingDown = true  -- 最初に設定（ソケット再起動を防止）
    bridge.running = false
    -- ... (実装省略: 既存のSimpleSocketBridge.stop()呼び出し)
end
```

**PluginShutdown.lua変更:**
```lua
-- PluginShutdown.lua - 同様のパターン
if bridge then
    if bridge.shuttingDown then
        logger:info("Plugin shutdown already in progress - skipping")
        return
    end
    bridge.shuttingDown = true
    bridge.running = false
    -- ... (実装省略: 既存のSimpleSocketBridge.stop()呼び出し)
end
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/test_client.py -v`
Expected: PASS

**Step 5: コミット**
```
git add lightroom_sdk/client.py lightroom-python-bridge.lrdevplugin/SimpleSocketBridge.lua lightroom-python-bridge.lrdevplugin/AppShutdown.lua lightroom-python-bridge.lrdevplugin/PluginShutdown.lua tests/test_client.py
git commit -m "fix: remove blocking sleep and add shuttingDown flag (eliminate 100ms per-command delay and prevent restart during shutdown)"
```

---

## Phase 2: プロジェクト再構成 + CLIフレームワーク基盤

---

### Task 6: mcp_server/ 削除 + pyproject.toml 更新

**Files:**
- Delete: `mcp_server/` ディレクトリ全体
- Modify: `pyproject.toml`
- Test: `tests/test_project_structure.py`

**Step 1: 失敗するテストを書く**
```python
# tests/test_project_structure.py
from pathlib import Path
import tomllib

PROJECT_ROOT = Path(__file__).parent.parent

def test_mcp_server_dir_removed():
    """mcp_server/ディレクトリが存在しないことを検証"""
    assert not (PROJECT_ROOT / "mcp_server").exists()

def test_pyproject_has_cli_entry_point():
    """pyproject.tomlに lr コマンドが定義されていることを検証"""
    pyproject = PROJECT_ROOT / "pyproject.toml"
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)
    scripts = data.get("project", {}).get("scripts", {})
    assert "lr" in scripts
    assert scripts["lr"] == "cli.main:cli"

def test_pyproject_no_fastmcp_dependency():
    """fastmcp依存が削除されていることを検証"""
    pyproject = PROJECT_ROOT / "pyproject.toml"
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)
    deps = data.get("project", {}).get("dependencies", [])
    assert not any("fastmcp" in d for d in deps)

def test_pyproject_has_click_dependency():
    """click依存が追加されていることを検証"""
    pyproject = PROJECT_ROOT / "pyproject.toml"
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)
    deps = data.get("project", {}).get("dependencies", [])
    assert any("click" in d for d in deps)
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/test_project_structure.py -v`
Expected: FAIL (mcp_server/ がまだ存在、scriptsセクションなし)

**Step 3: 実装**
```bash
# mcp_server/ 削除
rm -rf mcp_server/
```

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "lightroom-cli"
version = "0.2.0"
description = "CLI tool for Adobe Lightroom Classic"
requires-python = ">=3.10"
dependencies = [
    "click>=8.1",
    "rich>=13.0",
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
]

[project.scripts]
lr = "cli.main:cli"

[tool.setuptools]
packages = ["lightroom_sdk", "cli", "cli.commands"]
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/test_project_structure.py -v`
Expected: PASS

**Step 5: コミット**
```
git add -A mcp_server/ pyproject.toml tests/test_project_structure.py
git commit -m "refactor: remove mcp_server and restructure for CLI (migrate from MCP server to standalone CLI tool)"
```

---

### Task 7: cli/main.py エントリポイント

**Files:**
- Create: `cli/__init__.py`
- Create: `cli/main.py`
- Test: `tests/test_cli_main.py`

**Step 1: 失敗するテストを書く**
```python
# tests/test_cli_main.py
import pytest
from click.testing import CliRunner
from cli.main import cli

@pytest.fixture
def runner():
    return CliRunner()

def test_cli_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Lightroom Classic CLI" in result.output

def test_cli_output_option(runner):
    result = runner.invoke(cli, ["--help"])
    assert "--output" in result.output or "-o" in result.output

def test_cli_verbose_option(runner):
    result = runner.invoke(cli, ["--help"])
    assert "--verbose" in result.output or "-v" in result.output

def test_cli_timeout_option(runner):
    result = runner.invoke(cli, ["--help"])
    assert "--timeout" in result.output or "-t" in result.output

def test_cli_version(runner):
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/test_cli_main.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'cli')

**Step 3: 実装**
```python
# cli/main.py
import click
import logging

@click.group()
@click.version_option(version="0.2.0", prog_name="lr")
@click.option("--output", "-o", type=click.Choice(["json", "text", "table"]),
              default="text", help="Output format")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--timeout", "-t", type=float, default=30.0,
              help="Default command timeout in seconds")
@click.pass_context
def cli(ctx, output, verbose, timeout):
    """Lightroom Classic CLI - control Lightroom from the command line."""
    ctx.ensure_object(dict)
    ctx.obj["output"] = output
    ctx.obj["verbose"] = verbose
    ctx.obj["timeout"] = timeout

    if verbose:
        logging.basicConfig(level=logging.DEBUG)

# サブコマンドグループの登録（後続Taskで実装）
# from cli.commands.system import system
# cli.add_command(system)
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/test_cli_main.py -v`
Expected: PASS

**Step 5: コミット**
```
git add cli/__init__.py cli/main.py tests/test_cli_main.py
git commit -m "feat: add CLI entry point with global options (establish Click-based command framework)"
```

---

### Task 8: cli/output.py OutputFormatter

**Files:**
- Create: `cli/output.py`
- Test: `tests/test_output_formatter.py`

**Step 1: 失敗するテストを書く**
```python
# tests/test_output_formatter.py
import json
import pytest
from cli.output import OutputFormatter

def test_json_output():
    data = {"status": "ok", "version": "1.0"}
    result = OutputFormatter.format(data, "json")
    parsed = json.loads(result)
    assert parsed["status"] == "ok"

def test_text_output_flat():
    data = {"name": "photo.jpg", "rating": 5}
    result = OutputFormatter.format(data, "text")
    assert "name" in result
    assert "photo.jpg" in result

def test_table_output_list():
    data = [
        {"name": "a.jpg", "rating": 3},
        {"name": "b.jpg", "rating": 5},
    ]
    result = OutputFormatter.format(data, "table")
    assert "a.jpg" in result
    assert "b.jpg" in result

def test_text_output_nested():
    data = {"settings": {"exposure": 1.5, "contrast": 10}}
    result = OutputFormatter.format(data, "text")
    assert "exposure" in result

def test_format_error():
    result = OutputFormatter.format_error("Something went wrong", "text")
    assert "Error" in result or "error" in result.lower()
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/test_output_formatter.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'cli.output')

**Step 3: 実装**
```python
# cli/output.py
import json
from io import StringIO
from typing import Any, Union
from rich.console import Console
from rich.table import Table

class OutputFormatter:
    @staticmethod
    def format(data: Any, mode: str = "text") -> str:
        if mode == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)
        elif mode == "table":
            return OutputFormatter._format_table(data)
        else:
            return OutputFormatter._format_text(data)

    @staticmethod
    def _format_text(data: Any, indent: int = 0) -> str:
        if isinstance(data, dict):
            lines = []
            for k, v in data.items():
                if isinstance(v, (dict, list)):
                    lines.append(f"{'  ' * indent}{k}:")
                    lines.append(OutputFormatter._format_text(v, indent + 1))
                else:
                    lines.append(f"{'  ' * indent}{k}: {v}")
            return "\n".join(lines)
        elif isinstance(data, list):
            return "\n".join(OutputFormatter._format_text(item, indent) for item in data)
        return str(data)

    @staticmethod
    def _format_table(data: Any) -> str:
        if not isinstance(data, list) or not data:
            return OutputFormatter._format_text(data)
        console = Console(file=StringIO(), force_terminal=False)
        table = Table()
        for key in data[0].keys():
            table.add_column(key)
        for row in data:
            table.add_row(*[str(v) for v in row.values()])
        console.print(table)
        return console.file.getvalue()

    @staticmethod
    def format_error(message: str, mode: str = "text") -> str:
        if mode == "json":
            return json.dumps({"error": message})
        return f"Error: {message}"
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/test_output_formatter.py -v`
Expected: PASS

**Step 5: コミット**
```
git add cli/output.py tests/test_output_formatter.py
git commit -m "feat: add OutputFormatter with json/text/table modes (provide flexible CLI output rendering)"
```

---

### Task 9: cli/commands/system.py

**Files:**
- Create: `cli/commands/__init__.py`
- Create: `cli/commands/system.py`
- Modify: `cli/main.py` (system コマンド登録)
- Test: `tests/test_cli_system.py`

**Step 1: 失敗するテストを書く**
```python
# tests/test_cli_system.py
import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli

@pytest.fixture
def runner():
    return CliRunner()

@patch("cli.commands.system.get_bridge")
def test_system_ping(mock_get_bridge, runner):
    """lr system ping がpingコマンドを送信する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True, "result": {"status": "ok", "timestamp": 123}
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["system", "ping"])
    assert result.exit_code == 0
    assert "ok" in result.output

@patch("cli.commands.system.get_bridge")
def test_system_status(mock_get_bridge, runner):
    """lr system status がstatusコマンドを送信する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"connected": True, "version": "1.0"}
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["system", "status"])
    assert result.exit_code == 0

def test_system_check_connection_no_port_file(runner):
    """ポートファイルがない場合にエラーメッセージ表示"""
    result = runner.invoke(cli, ["system", "check-connection",
                                  "--port-file", "/tmp/nonexistent_test.txt"])
    assert result.exit_code == 0 or result.exit_code == 1
    # ポートファイルなし → 接続不可メッセージ
    assert "not" in result.output.lower() or "error" in result.output.lower() \
        or "unavailable" in result.output.lower()
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/test_cli_system.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'cli.commands')

**Step 3: 実装**
```python
# cli/commands/system.py
import asyncio
import click
from pathlib import Path
from cli.output import OutputFormatter

def get_bridge():
    """ResilientSocketBridgeインスタンスを取得（遅延import）"""
    from lightroom_sdk.resilient_bridge import ResilientSocketBridge
    return ResilientSocketBridge()

def run_async(coro):
    """CLIからasync関数を実行するヘルパー"""
    return asyncio.get_event_loop().run_until_complete(coro)

@click.group()
def system():
    """System commands (ping, status, reconnect, check-connection)"""
    pass

@system.command()
@click.pass_context
def ping(ctx):
    """Test connection to Lightroom"""
    bridge = get_bridge()
    try:
        result = run_async(bridge.send_command("system.ping"))
        fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
        click.echo(OutputFormatter.format(result.get("result", result), fmt))
    except Exception as e:
        click.echo(OutputFormatter.format_error(str(e)))
    finally:
        run_async(bridge.disconnect())

@system.command()
@click.pass_context
def status(ctx):
    """Get Lightroom bridge status"""
    bridge = get_bridge()
    # ... (実装省略: ping と同様のパターン)
    try:
        result = run_async(bridge.send_command("system.status"))
        fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
        click.echo(OutputFormatter.format(result.get("result", result), fmt))
    except Exception as e:
        click.echo(OutputFormatter.format_error(str(e)))
    finally:
        run_async(bridge.disconnect())

@system.command()
def reconnect():
    """Force reconnection to Lightroom"""
    bridge = get_bridge()
    # ... (実装省略: disconnect→connect)
    click.echo("Reconnected")

@system.command("check-connection")
@click.option("--port-file", default="/tmp/lightroom_ports.txt")
def check_connection(port_file):
    """Check if Lightroom is available"""
    port_path = Path(port_file)
    if not port_path.exists():
        click.echo("Lightroom connection unavailable: port file not found")
        return
    bridge = get_bridge()
    try:
        run_async(bridge.connect())
        result = run_async(bridge.send_command("system.ping", timeout=5.0))
        click.echo("Lightroom connection: ok")
    except Exception as e:
        click.echo(f"Lightroom connection unavailable: {e}")
    finally:
        run_async(bridge.disconnect())

# cli/main.py に追加
# from cli.commands.system import system
# cli.add_command(system)
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/test_cli_system.py -v`
Expected: PASS

**Step 5: コミット**
```
git add cli/commands/__init__.py cli/commands/system.py cli/main.py tests/test_cli_system.py
git commit -m "feat: add system commands (ping/status/reconnect/check-connection) (first CLI command group for Lightroom control)"
```

---

## Completion Criteria

Phase 1 完了時:
- [x] `python -m pytest tests/ -v` 全テスト通過
- [x] MockLightroomServerでオフラインテスト可能
- [x] SocketBridgeがイベントをハンドリング
- [x] ResilientSocketBridgeが状態マシンで自動再接続
- [x] time.sleep(0.1) 除去済み
- [x] Luaプラグインのシャットダウンが安全

Phase 2 完了時:
- [x] `mcp_server/` 完全削除
- [x] `lr --help` が動作
- [x] `lr system ping` がMockServer経由でテスト通過
- [x] OutputFormatterが3形式対応
- [x] `pip install -e .` で `lr` コマンドが使える

---

## Phase 3: CLIコマンド実装

---

### Task 10: cli/commands/catalog.py

**Files:**
- Create: `cli/commands/catalog.py`
- Test: `tests/integration/test_cli_catalog.py`

**Step 1: 失敗するテストを書く**
```python
# tests/integration/test_cli_catalog.py
import json
import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli

@pytest.fixture
def runner():
    return CliRunner()

@patch("cli.commands.catalog.get_bridge")
def test_catalog_get_selected(mock_get_bridge, runner):
    """lr catalog get-selected が選択中の写真を返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": [{"id": "photo-1", "filename": "IMG_001.jpg"}],
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "get-selected"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.getSelectedPhotos", {}, timeout=30.0
    )

@patch("cli.commands.catalog.get_bridge")
def test_catalog_list_with_options(mock_get_bridge, runner):
    """lr catalog list --limit 10 --offset 5 がパラメータを渡す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "2", "success": True, "result": [],
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "list", "--limit", "10", "--offset", "5"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.getAllPhotos", {"limit": 10, "offset": 5}, timeout=30.0
    )

@patch("cli.commands.catalog.get_bridge")
def test_catalog_set_rating(mock_get_bridge, runner):
    """lr catalog set-rating photo-1 5 がratingを設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "3", "success": True, "result": {"rating": 5},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "set-rating", "photo-1", "5"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.setRating", {"photoId": "photo-1", "rating": 5}, timeout=30.0
    )

# ... (実装省略: search, get-info, select, add-keywords のテストも同様パターン)
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/integration/test_cli_catalog.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'cli.commands.catalog')

**Step 3: 実装**
```python
# cli/commands/catalog.py
import asyncio
import click
from cli.output import OutputFormatter

def get_bridge():
    from lightroom_sdk.resilient_bridge import ResilientSocketBridge
    return ResilientSocketBridge()

def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)

@click.group()
def catalog():
    """Catalog commands (list, search, select, get-info, set-rating, add-keywords)"""
    pass

@catalog.command("get-selected")
@click.pass_context
def get_selected(ctx):
    """Get currently selected photos"""
    bridge = get_bridge()
    try:
        timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
        result = run_async(bridge.send_command("catalog.getSelectedPhotos", {}, timeout=timeout))
        fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
        click.echo(OutputFormatter.format(result.get("result", result), fmt))
    except Exception as e:
        click.echo(OutputFormatter.format_error(str(e)))
    finally:
        run_async(bridge.disconnect())

@catalog.command("list")
@click.option("--limit", default=50, type=int, help="Max photos to return")
@click.option("--offset", default=0, type=int, help="Offset for pagination")
@click.pass_context
def list_photos(ctx, limit, offset):
    """List photos in catalog"""
    bridge = get_bridge()
    try:
        timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
        result = run_async(bridge.send_command(
            "catalog.getAllPhotos", {"limit": limit, "offset": offset}, timeout=timeout
        ))
        fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
        click.echo(OutputFormatter.format(result.get("result", result), fmt))
    except Exception as e:
        click.echo(OutputFormatter.format_error(str(e)))
    finally:
        run_async(bridge.disconnect())

@catalog.command("set-rating")
@click.argument("photo_id")
@click.argument("rating", type=int)
@click.pass_context
def set_rating(ctx, photo_id, rating):
    """Set photo rating (0-5)"""
    bridge = get_bridge()
    # ... (実装省略: send_command("catalog.setRating", {...}) と同様パターン)
    try:
        timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
        result = run_async(bridge.send_command(
            "catalog.setRating", {"photoId": photo_id, "rating": rating}, timeout=timeout
        ))
        fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
        click.echo(OutputFormatter.format(result.get("result", result), fmt))
    except Exception as e:
        click.echo(OutputFormatter.format_error(str(e)))
    finally:
        run_async(bridge.disconnect())

# ... (実装省略: select, search, get-info, add-keywords も同様パターン)
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/integration/test_cli_catalog.py -v`
Expected: PASS

**Step 5: コミット**
```
git add cli/commands/catalog.py tests/integration/__init__.py tests/integration/test_cli_catalog.py cli/main.py
git commit -m "feat: add catalog CLI commands (enable photo management from command line)"
```

---

### Task 11: cli/commands/develop.py

**Files:**
- Create: `cli/commands/develop.py`
- Test: `tests/integration/test_cli_develop.py`

**Step 1: 失敗するテストを書く**
```python
# tests/integration/test_cli_develop.py
import json
import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli

@pytest.fixture
def runner():
    return CliRunner()

@patch("cli.commands.develop.get_bridge")
def test_develop_get_settings(mock_get_bridge, runner):
    """lr develop get-settings が現在の設定を返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"Exposure": 0.5, "Contrast": 25},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "get-settings"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.getSettings", {}, timeout=30.0
    )

@patch("cli.commands.develop.get_bridge")
def test_develop_set_single_param(mock_get_bridge, runner):
    """lr develop set Exposure 1.5 が単一パラメータを設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "2", "success": True, "result": {"Exposure": 1.5},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "set", "Exposure", "1.5"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.setValue", {"parameter": "Exposure", "value": 1.5}, timeout=30.0
    )

@patch("cli.commands.develop.get_bridge")
def test_develop_set_multiple_params(mock_get_bridge, runner):
    """lr develop set Exposure 1.5 Contrast 25 が複数パラメータを一括設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "3", "success": True, "result": {},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "set", "Exposure", "1.5", "Contrast", "25"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.batchSetValues",
        {"settings": {"Exposure": 1.5, "Contrast": 25.0}},
        timeout=30.0,
    )

@patch("cli.commands.develop.get_bridge")
def test_develop_auto_tone(mock_get_bridge, runner):
    """lr develop auto-tone がautoToneを実行する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "4", "success": True, "result": {"applied": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "auto-tone"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.autoTone", {}, timeout=30.0
    )

# ... (実装省略: get, range, params, reset, apply-style, batch のテストも同様パターン)
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/integration/test_cli_develop.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'cli.commands.develop')

**Step 3: 実装**
```python
# cli/commands/develop.py
import asyncio
import json
import click
from pathlib import Path
from cli.output import OutputFormatter

def get_bridge():
    from lightroom_sdk.resilient_bridge import ResilientSocketBridge
    return ResilientSocketBridge()

def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)

def _parse_pairs(pairs: tuple) -> dict:
    """可変長引数 (param, value, param, value, ...) を辞書に変換"""
    if len(pairs) % 2 != 0:
        raise click.BadParameter("Parameters must be in 'param value' pairs")
    result = {}
    for i in range(0, len(pairs), 2):
        result[pairs[i]] = float(pairs[i + 1])
    return result

@click.group()
def develop():
    """Develop commands (get-settings, set, range, auto-tone, reset, etc.)"""
    pass

@develop.command("get-settings")
@click.pass_context
def get_settings(ctx):
    """Get all current develop settings"""
    bridge = get_bridge()
    try:
        timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
        result = run_async(bridge.send_command("develop.getSettings", {}, timeout=timeout))
        fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
        click.echo(OutputFormatter.format(result.get("result", result), fmt))
    except Exception as e:
        click.echo(OutputFormatter.format_error(str(e)))
    finally:
        run_async(bridge.disconnect())

@develop.command("set")
@click.argument("pairs", nargs=-1, required=True)
@click.pass_context
def set_values(ctx, pairs):
    """Set develop parameter(s): lr develop set <param> <value> [<param2> <value2> ...]"""
    bridge = get_bridge()
    try:
        timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
        parsed = _parse_pairs(pairs)
        if len(parsed) == 1:
            param, value = next(iter(parsed.items()))
            result = run_async(bridge.send_command(
                "develop.setValue", {"parameter": param, "value": value}, timeout=timeout
            ))
        else:
            result = run_async(bridge.send_command(
                "develop.batchSetValues", {"settings": parsed}, timeout=timeout
            ))
        fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
        click.echo(OutputFormatter.format(result.get("result", result), fmt))
    except Exception as e:
        click.echo(OutputFormatter.format_error(str(e)))
    finally:
        run_async(bridge.disconnect())

@develop.command("auto-tone")
@click.pass_context
def auto_tone(ctx):
    """Apply auto tone adjustments"""
    bridge = get_bridge()
    try:
        timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
        result = run_async(bridge.send_command("develop.autoTone", {}, timeout=timeout))
        fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
        click.echo(OutputFormatter.format(result.get("result", result), fmt))
    except Exception as e:
        click.echo(OutputFormatter.format_error(str(e)))
    finally:
        run_async(bridge.disconnect())

# ... (実装省略: get, range, params, reset, apply-style, batch も同様パターン)
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/integration/test_cli_develop.py -v`
Expected: PASS

**Step 5: コミット**
```
git add cli/commands/develop.py tests/integration/test_cli_develop.py cli/main.py
git commit -m "feat: add develop CLI commands with variable-length param pairs (enable develop module control from CLI)"
```

---

### Task 12: cli/commands/preview.py + cli/completions.py

**Files:**
- Create: `cli/commands/preview.py`
- Create: `cli/completions.py`
- Test: `tests/integration/test_cli_preview.py`

**Step 1: 失敗するテストを書く**
```python
# tests/integration/test_cli_preview.py
import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli

@pytest.fixture
def runner():
    return CliRunner()

@patch("cli.commands.preview.get_bridge")
def test_preview_generate_current(mock_get_bridge, runner):
    """lr preview generate-current が現在の写真のプレビューを生成する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"path": "/tmp/preview.jpg"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["preview", "generate-current"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "preview.generateCurrentPreview", {}, timeout=120.0
    )

@patch("cli.commands.preview.get_bridge")
def test_preview_generate_with_options(mock_get_bridge, runner):
    """lr preview generate --size 2048 --format png がオプションを渡す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "2", "success": True,
        "result": {"path": "/tmp/preview.png"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["preview", "generate", "--size", "2048", "--format", "png"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "preview.generatePreview", {"size": 2048, "format": "png"}, timeout=120.0
    )

@patch("cli.commands.preview.get_bridge")
def test_preview_generate_batch(mock_get_bridge, runner):
    """lr preview generate-batch がバッチプレビュー生成する（タイムアウト300秒）"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "3", "success": True,
        "result": {"count": 5},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["preview", "generate-batch"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "preview.generateBatchPreviews", {}, timeout=300.0
    )

def test_complete_develop_param():
    """タブ補完がパラメータ候補を返す"""
    from cli.completions import complete_develop_param
    # incomplete="Exp" → "Exposure" が候補に含まれる
    completions = complete_develop_param(None, None, "Exp")
    names = [c.value if hasattr(c, "value") else c for c in completions]
    assert "Exposure" in names

def test_complete_develop_param_empty():
    """空文字列で全候補を返す"""
    from cli.completions import complete_develop_param
    completions = complete_develop_param(None, None, "")
    assert len(completions) > 10  # 十分な数のパラメータが返る
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/integration/test_cli_preview.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'cli.commands.preview')

**Step 3: 実装**
```python
# cli/commands/preview.py
import asyncio
import click
from cli.output import OutputFormatter

def get_bridge():
    from lightroom_sdk.resilient_bridge import ResilientSocketBridge
    return ResilientSocketBridge()

def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)

@click.group()
def preview():
    """Preview commands (generate, get-info, comparison, batch)"""
    pass

@preview.command("generate-current")
@click.pass_context
def generate_current(ctx):
    """Generate preview for currently selected photo"""
    bridge = get_bridge()
    try:
        result = run_async(bridge.send_command(
            "preview.generateCurrentPreview", {}, timeout=120.0
        ))
        fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
        click.echo(OutputFormatter.format(result.get("result", result), fmt))
    except Exception as e:
        click.echo(OutputFormatter.format_error(str(e)))
    finally:
        run_async(bridge.disconnect())

@preview.command("generate")
@click.option("--size", default=1024, type=int, help="Preview size in pixels")
@click.option("--format", "fmt", default="jpeg", type=click.Choice(["jpeg", "png"]))
@click.pass_context
def generate(ctx, size, fmt):
    """Generate preview with specified size and format"""
    bridge = get_bridge()
    try:
        result = run_async(bridge.send_command(
            "preview.generatePreview", {"size": size, "format": fmt}, timeout=120.0
        ))
        output = ctx.obj.get("output", "text") if ctx.obj else "text"
        click.echo(OutputFormatter.format(result.get("result", result), output))
    except Exception as e:
        click.echo(OutputFormatter.format_error(str(e)))
    finally:
        run_async(bridge.disconnect())

@preview.command("generate-batch")
@click.pass_context
def generate_batch(ctx):
    """Generate batch previews (timeout: 300s)"""
    bridge = get_bridge()
    try:
        result = run_async(bridge.send_command(
            "preview.generateBatchPreviews", {}, timeout=300.0
        ))
        fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
        click.echo(OutputFormatter.format(result.get("result", result), fmt))
    except Exception as e:
        click.echo(OutputFormatter.format_error(str(e)))
    finally:
        run_async(bridge.disconnect())

# ... (実装省略: get-info, generate-comparison も同様パターン)
```

```python
# cli/completions.py
from click.shell_completion import CompletionItem

DEVELOP_PARAMETER_RANGES = {
    "Exposure": (-5.0, 5.0),
    "Contrast": (-100, 100),
    "Highlights": (-100, 100),
    "Shadows": (-100, 100),
    "Whites": (-100, 100),
    "Blacks": (-100, 100),
    "Clarity": (-100, 100),
    "Dehaze": (-100, 100),
    "Vibrance": (-100, 100),
    "Saturation": (-100, 100),
    "Temperature": (2000, 50000),
    "Tint": (-150, 150),
    "Texture": (-100, 100),
    "Sharpness": (0, 150),
    # ... (実装省略: 他のパラメータも同様に定義)
}

def complete_develop_param(ctx, param, incomplete: str) -> list:
    """develop set コマンド用のタブ補完"""
    return [
        CompletionItem(name)
        for name in DEVELOP_PARAMETER_RANGES.keys()
        if name.lower().startswith(incomplete.lower())
    ]
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/.claude/mcp-servers/lightroom-mcp && python -m pytest tests/integration/test_cli_preview.py -v`
Expected: PASS

**Step 5: コミット**
```
git add cli/commands/preview.py cli/completions.py tests/integration/test_cli_preview.py cli/main.py
git commit -m "feat: add preview commands and tab completion (complete CLI command coverage with shell UX)"
```

---

## Phase 4: パブリックリリース準備

---

### Task 13: scripts/ 作成

**Files:**
- Create: `scripts/install.sh`
- Create: `scripts/install-plugin.sh`
- Create: `scripts/check-connection.py`

**Step 1: TDDなし（スクリプト）。手動テストのみ。**

**Step 2: 実装**

```bash
# scripts/install.sh
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Lightroom CLI Installer ==="

# Python バージョン確認
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
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

# MCP設定のヒント表示
echo ""
echo "=== Setup Complete ==="
echo "Run 'lr system check-connection' to verify Lightroom connection."

# 接続テスト
python3 "$SCRIPT_DIR/check-connection.py" || true
```

```bash
# scripts/install-plugin.sh
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PLUGIN_SRC="$PROJECT_DIR/lightroom-plugin"
# ... (実装省略: OS判定、LR Modules ディレクトリ特定、シンボリックリンク作成)
LR_MODULES="$HOME/Library/Application Support/Adobe/Lightroom/Modules"
PLUGIN_DEST="$LR_MODULES/lightroom-python-bridge.lrdevplugin"

mkdir -p "$LR_MODULES"
if [ -L "$PLUGIN_DEST" ] || [ -e "$PLUGIN_DEST" ]; then
    echo "Plugin already exists at $PLUGIN_DEST"
    echo "Remove it first if you want to reinstall."
    exit 0
fi

ln -s "$PLUGIN_SRC" "$PLUGIN_DEST"
echo "Plugin symlinked: $PLUGIN_DEST -> $PLUGIN_SRC"
```

```python
# scripts/check-connection.py
#!/usr/bin/env python3
"""Lightroom接続チェックスクリプト"""
import sys
from pathlib import Path

PORT_FILE = Path("/tmp/lightroom_ports.txt")

def main():
    # ポートファイル存在確認
    if not PORT_FILE.exists():
        print("[ ] Port file not found. Is Lightroom running with the plugin?")
        sys.exit(1)

    # ping テスト
    try:
        import asyncio
        from lightroom_sdk.resilient_bridge import ResilientSocketBridge
        bridge = ResilientSocketBridge()
        result = asyncio.get_event_loop().run_until_complete(
            bridge.send_command("system.ping", timeout=5.0)
        )
        asyncio.get_event_loop().run_until_complete(bridge.disconnect())
        print("[OK] Lightroom connection successful")
        sys.exit(0)
    except Exception as e:
        print(f"[ ] Connection failed: {e}")
        sys.exit(1)
    # ... (実装省略: エラーハンドリング詳細)

if __name__ == "__main__":
    main()
```

**Step 3: コミット**
```
git add scripts/install.sh scripts/install-plugin.sh scripts/check-connection.py
git commit -m "feat: add installation scripts (streamline setup for new users)"
```

---

### Task 14: lightroom-plugin/ ディレクトリ名変更

**Files:**
- Rename: `lightroom-python-bridge.lrdevplugin/` → `lightroom-plugin/`
- Modify: `scripts/install-plugin.sh` (シンボリックリンク元パス更新)

**Step 1: TDDなし。**

**Step 2: 実装**

```bash
# ディレクトリリネーム
git mv lightroom-python-bridge.lrdevplugin/ lightroom-plugin/
```

`scripts/install-plugin.sh` の `PLUGIN_SRC` は既に `lightroom-plugin` を指しているため変更不要。

README に以下の注記を追加（Task 15で実施）:
> `lightroom-plugin/` はリポジトリ内の名称です。`scripts/install-plugin.sh` でインストールすると、Lightroomが認識する `.lrdevplugin` サフィックス付きのシンボリックリンクが作成されます。

**Step 3: コミット**
```
git add -A
git commit -m "refactor: rename plugin directory to lightroom-plugin (cleaner repo structure with symlink-based LR integration)"
```

---

### Task 15: ドキュメント整備

**Files:**
- Rewrite: `README.md`
- Create: `docs/CLI_REFERENCE.md`
- Create: `CONTRIBUTING.md`
- Create: `CHANGELOG.md`

**Step 1: TDDなし。**

**Step 2: 実装**

```markdown
<!-- README.md（核心部分のみ） -->
# Lightroom CLI

Adobe Lightroom Classicをコマンドラインから操作するツール。

## クイックスタート

\```bash
# インストール
git clone <repo-url> && cd lightroom-cli
./scripts/install.sh

# Lightroomを起動（プラグインが自動ロードされる）

# 接続確認
lr system ping

# 使用例
lr catalog get-selected                    # 選択中の写真を取得
lr develop set Exposure 1.5 Contrast 25    # 現像パラメータを設定
lr preview generate-current                # プレビュー生成
\```

## アーキテクチャ

\```
[Lightroom Classic] ← Lua Plugin (TCP Socket) → [Python SDK] → [CLI]
\```

<!-- ... (実装省略: 詳細セクション) -->
```

```markdown
<!-- docs/CLI_REFERENCE.md（核心部分のみ） -->
# CLI Reference

## Global Options
| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| --output | -o | text | Output format (json/text/table) |
| --verbose | -v | false | Enable debug logging |
| --timeout | -t | 30.0 | Default timeout in seconds |

## lr system
- `lr system ping` - Test connection
- `lr system status` - Get bridge status
<!-- ... (実装省略: 全コマンドのリファレンス) -->

## lr catalog
- `lr catalog get-selected` - Get selected photos
- `lr catalog list [--limit N] [--offset N]` - List photos
<!-- ... (実装省略) -->

## lr develop
- `lr develop set <param> <value> [...]` - Set parameters
<!-- ... (実装省略) -->

## lr preview
- `lr preview generate-current` - Generate current preview
<!-- ... (実装省略) -->
```

```markdown
<!-- CONTRIBUTING.md（核心部分のみ） -->
# Contributing

## セットアップ
\```bash
git clone <repo-url> && cd lightroom-cli
pip install -e ".[dev]"
\```

## テスト実行
\```bash
python -m pytest tests/unit/ tests/integration/ -v
\```

## PR ガイドライン
- テストを書く（TDD推奨）
- `python -m pytest` が通ること
<!-- ... (実装省略) -->
```

```markdown
<!-- CHANGELOG.md -->
# Changelog

## [1.0.0] - 2026-03-XX

### Added
- CLI tool (`lr`) with system/catalog/develop/preview commands
- ResilientSocketBridge with auto-reconnect and heartbeat
- Tab completion for develop parameters
- Installation scripts (`scripts/install.sh`)
- Comprehensive test suite (unit + integration)

### Changed
- Removed MCP server dependency
- Renamed plugin directory to `lightroom-plugin/`
- Removed `time.sleep(0.1)` from client.py

### Fixed
- Lua plugin shutdown race condition (shuttingDown flag)
```

**Step 3: コミット**
```
git add README.md docs/CLI_REFERENCE.md CONTRIBUTING.md CHANGELOG.md
git commit -m "docs: add public release documentation (README, CLI reference, contributing guide, changelog)"
```

---

### Task 16: GitHub Actions CI

**Files:**
- Create: `.github/workflows/test.yml`

**Step 1: TDDなし。**

**Step 2: 実装**

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: python -m pytest tests/unit/ tests/integration/ -v --cov=lightroom_sdk --cov=cli
```

**Step 3: コミット**
```
git add .github/workflows/test.yml
git commit -m "ci: add GitHub Actions test workflow (automated testing across Python 3.10-3.12)"
```

---

## Completion Criteria (continued)

Phase 3 完了時:
- [ ] `lr catalog get-selected` がMockServer経由でテスト通過
- [ ] `lr catalog list --limit 10` がパラメータを正しく送信
- [ ] `lr develop set Exposure 1.5 Contrast 25` が複数パラメータに対応
- [ ] `lr develop auto-tone` が動作
- [ ] `lr preview generate-current` がタイムアウト120秒で実行
- [ ] `lr preview generate-batch` がタイムアウト300秒で実行
- [ ] タブ補完が develop パラメータ候補を返す
- [ ] `python -m pytest tests/integration/ -v` 全テスト通過

Phase 4 完了時:
- [ ] `scripts/install.sh` がPythonバージョン確認→インストール→プラグインリンク→接続テスト
- [ ] `lightroom-python-bridge.lrdevplugin/` が `lightroom-plugin/` にリネーム済み
- [ ] シンボリックリンクで `.lrdevplugin` サフィックスが付与される
- [ ] README.md にクイックスタートが記載
- [ ] docs/CLI_REFERENCE.md に全コマンドのリファレンス
- [ ] CHANGELOG.md に v1.0.0 エントリ
- [ ] GitHub Actions CI が Python 3.10/3.11/3.12 でテスト実行
