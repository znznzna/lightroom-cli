# CLI追加 & プラグイン安定化 設計書

**作成日**: 2026-03-04
**対象リポジトリ**: 新規パブリックリポジトリ（lightroom-mcp から fork/再構成）
**ステータス**: Draft

---

## 1. アプローチ比較

### 1.1 CLIアーキテクチャ

| 項目 | A: デコレータ自動登録 | B: コード生成（静的） | C: 汎用コマンドのみ |
|------|----------------------|----------------------|---------------------|
| **概要** | MCPツール定義にCLIデコレータを追加し、同一定義からMCPツールとCLIサブコマンドを同時生成 | MCPツール定義を解析してCLIコードをビルド時に静的生成 | `lr exec <command> [params...]` のような汎用コマンド1つで全操作を実行 |
| **実装コスト** | 中（デコレータ基盤+Click統合） | 高（パーサー+テンプレート+ビルドパイプライン） | 低（SDK呼び出しラッパーのみ） |
| **保守性** | 高（Single Source of Truth） | 中（生成コードの再生成が必要） | 高（コマンド追加不要） |
| **UX品質** | 高（型安全な引数、ヘルプ生成、タブ補完） | 高（同上、ただし生成済みのため） | 低（手動でコマンド名/パラメータを記憶する必要） |
| **100+コマンド対応** | 自動対応（定義追加のみ） | 自動対応（再生成のみ） | 自動対応（定義不要） |
| **テスト容易性** | 高（デコレータ単位でテスト可能） | 中（生成コードのスナップショットテストが必要） | 高（SDK呼び出しのみ） |
| **タブ補完** | Click標準サポート | Click標準サポート | 限定的（コマンド名のみ動的補完が必要） |
| **デバッグ性** | 高（スタックトレースが直接対応） | 中（生成コードのため間接的） | 高（単純構造） |

### 1.2 プラグイン安定化

| 項目 | A: 段階的修正 | B: プロトコル層再設計 | C: HTTPベースに移行 |
|------|-------------|---------------------|---------------------|
| **概要** | 既存TCP dual-socketを維持し、シャットダウン・再接続・タイムアウトを個別修正 | TCP通信層を再設計し、ハートビート・再接続プロトコルを追加 | TCPをHTTP/REST APIに置き換え |
| **実装コスト** | 低〜中 | 高 | 非常に高（Lua HTTP対応が困難） |
| **リスク** | 低（既存動作を維持） | 中（プロトコル変更による互換性喪失） | 高（LrSocket廃止、Luaでのサーバー実装が複雑） |
| **シャットダウン改善** | SHUTDOWN_FIXES.md の修正を完成+追加修正 | 根本的に解決可能 | HTTPなので自然に解決 |
| **再接続改善** | Python側ResilientClientの強化 | プロトコルレベルで対応 | HTTP接続プーリング |
| **Lua側変更** | 最小限 | 大幅 | 全面書き換え |

### 1.3 推奨アプローチ

**CLI: A（デコレータ自動登録）** + **安定化: A（段階的修正）**

理由:
- 100+コマンドの保守でSingle Source of Truthが最も重要
- 既存のMCPツール定義パターン（`setup_*_tools` 関数群）との親和性が高い
- Luaプラグインの大規模変更は高リスク。SHUTDOWN_FIXES.mdで既に方向性が確立済み
- パブリックリリースにはシンプルで理解しやすいアーキテクチャが適切

---

## 2. 推奨アプローチ詳細設計

### 2.1 CLIアーキテクチャ

#### 2.1.1 設計思想

MCPツール定義を「コマンドの真のソース」として扱い、同一の関数定義からMCPツールとCLIサブコマンドの両方を自動生成する。

```
[ツール定義関数]
    ├─ @mcp_tool デコレータ → MCPサーバーに登録
    └─ @cli_command デコレータ → Click CLIに登録
         ↓
    [共通レジストリ]
         ├─ FastMCP server.tool() → MCP公開
         └─ click.command() → CLI公開
```

#### 2.1.2 共通レジストリ設計

```python
# lightroom_sdk/command_registry.py

from dataclasses import dataclass, field
from typing import Callable, Dict, Any, Optional, List, Tuple
import inspect

@dataclass
class CommandDefinition:
    """MCPとCLI両方から使用されるコマンド定義"""
    name: str                    # "develop.adjust_exposure"
    func: Callable               # 実際の実装関数
    category: str                # "develop", "catalog", "system", "preview"
    description: str             # ヘルプテキスト
    parameters: List['ParameterDef'] = field(default_factory=list)
    lr_command: str = ""         # Lightroom SDK側のコマンド名
    requires_photo: bool = False # 写真選択が必要か

@dataclass
class ParameterDef:
    """パラメータ定義"""
    name: str
    type: type           # float, int, str, bool
    description: str
    required: bool = True
    default: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None

class CommandRegistry:
    """MCPツールとCLIコマンドの共通レジストリ"""

    _commands: Dict[str, CommandDefinition] = {}

    @classmethod
    def register(cls, category: str, lr_command: str = "",
                 requires_photo: bool = False):
        """デコレータ: コマンドを登録"""
        def decorator(func):
            # 関数シグネチャからパラメータを自動抽出
            sig = inspect.signature(func)
            params = []
            for param_name, param in sig.parameters.items():
                if param_name in ('self', 'client'):
                    continue
                param_def = ParameterDef(
                    name=param_name,
                    type=param.annotation if param.annotation != inspect.Parameter.empty else str,
                    description="",  # docstringから抽出
                    required=param.default == inspect.Parameter.empty,
                    default=param.default if param.default != inspect.Parameter.empty else None,
                )
                params.append(param_def)

            cmd_name = f"{category}.{func.__name__}"
            cls._commands[cmd_name] = CommandDefinition(
                name=cmd_name,
                func=func,
                category=category,
                description=func.__doc__ or "",
                parameters=params,
                lr_command=lr_command,
                requires_photo=requires_photo,
            )
            return func
        return decorator

    @classmethod
    def get_all(cls) -> Dict[str, CommandDefinition]:
        return cls._commands

    @classmethod
    def get_by_category(cls, category: str) -> Dict[str, CommandDefinition]:
        return {k: v for k, v in cls._commands.items() if v.category == category}
```

#### 2.1.3 コマンド体系設計

```
lr <category> <action> [OPTIONS]

カテゴリ:
  system     接続管理・ステータス
  catalog    カタログ操作（写真選択、検索、メタデータ）
  develop    現像パラメータ操作
  preview    プレビュー生成
  config     CLI設定管理

例:
  lr system ping
  lr system status
  lr catalog list --limit 50 --offset 0
  lr catalog select <photo-id>
  lr catalog search --rating-min 3 --keyword landscape
  lr develop get-settings
  lr develop set exposure 0.5
  lr develop set --param Exposure --value 0.5
  lr develop adjust exposure 0.5
  lr develop adjust contrast 20 highlights -30 shadows 15
  lr develop batch --settings '{"Exposure": 0.5, "Contrast": 20}'
  lr develop auto-tone
  lr develop reset
  lr develop apply-style portrait
  lr preview generate --format jpeg --size 1024
  lr config show
  lr config set timeout 60
```

#### 2.1.4 CLI実装構造

```python
# cli/main.py
import click
import asyncio
import json
import sys
from lightroom_sdk import LightroomClient

@click.group()
@click.option('--output', '-o', type=click.Choice(['json', 'text', 'table']),
              default='text', help='出力フォーマット')
@click.option('--verbose', '-v', is_flag=True, help='詳細ログ出力')
@click.option('--timeout', '-t', type=float, default=30.0, help='コマンドタイムアウト(秒)')
@click.pass_context
def cli(ctx, output, verbose, timeout):
    """Lightroom Classic CLI - コマンドラインから Lightroom を操作"""
    ctx.ensure_object(dict)
    ctx.obj['output'] = output
    ctx.obj['verbose'] = verbose
    ctx.obj['timeout'] = timeout

# --- 自動登録メカニズム ---

def register_commands_from_registry(cli_group: click.Group):
    """CommandRegistryからClickコマンドを自動生成"""
    from lightroom_sdk.command_registry import CommandRegistry

    for cmd_name, cmd_def in CommandRegistry.get_all().items():
        category, action = cmd_name.split('.', 1)

        # カテゴリグループを取得または作成
        if category not in cli_group.commands:
            group = click.Group(name=category, help=f"{category} commands")
            cli_group.add_command(group)
        else:
            group = cli_group.commands[category]

        # パラメータからClickオプション/引数を生成
        params = []
        for p in cmd_def.parameters:
            if p.required:
                params.append(click.Argument([p.name], type=_map_type(p.type)))
            else:
                opt_name = f"--{p.name.replace('_', '-')}"
                params.append(click.Option(
                    [opt_name], type=_map_type(p.type),
                    default=p.default, help=p.description
                ))

        # コマンド関数を生成
        cmd = _make_click_command(cmd_def, params)
        group.add_command(cmd)

def _make_click_command(cmd_def, params):
    """CommandDefinitionからClickコマンドを生成"""
    @click.pass_context
    def command(ctx, **kwargs):
        output_format = ctx.obj.get('output', 'text')
        timeout = ctx.obj.get('timeout', 30.0)

        result = asyncio.run(_execute_command(cmd_def, kwargs, timeout))
        _format_output(result, output_format)

    command.__name__ = cmd_def.name.split('.')[-1].replace('_', '-')
    command.__doc__ = cmd_def.description

    cmd = click.Command(
        name=command.__name__,
        callback=command,
        params=params,
        help=cmd_def.description,
    )
    return cmd

async def _execute_command(cmd_def, kwargs, timeout):
    """SDKを直接使用してコマンドを実行"""
    async with LightroomClient() as client:
        return await cmd_def.func(client, **kwargs)
```

#### 2.1.5 出力フォーマット

```python
# cli/output.py

import json
import sys
from typing import Any, Dict

class OutputFormatter:
    """CLI出力フォーマッター"""

    @staticmethod
    def format(data: Dict[str, Any], mode: str = 'text') -> str:
        if mode == 'json':
            return json.dumps(data, indent=2, ensure_ascii=False)
        elif mode == 'table':
            return OutputFormatter._format_table(data)
        else:
            return OutputFormatter._format_text(data)

    @staticmethod
    def _format_text(data: Dict[str, Any], indent: int = 0) -> str:
        """人間が読みやすいテキスト形式"""
        lines = []
        prefix = "  " * indent
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(OutputFormatter._format_text(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}: ({len(value)} items)")
                for i, item in enumerate(value[:10]):  # 最大10件
                    if isinstance(item, dict):
                        lines.append(f"{prefix}  [{i}]:")
                        lines.append(OutputFormatter._format_text(item, indent + 2))
                    else:
                        lines.append(f"{prefix}  - {item}")
                if len(value) > 10:
                    lines.append(f"{prefix}  ... and {len(value) - 10} more")
            else:
                lines.append(f"{prefix}{key}: {value}")
        return "\n".join(lines)

    @staticmethod
    def _format_table(data: Dict[str, Any]) -> str:
        """テーブル形式（パラメータ一覧向け）"""
        # 単純なkey-valueの場合
        if all(not isinstance(v, (dict, list)) for v in data.values()):
            max_key_len = max(len(str(k)) for k in data.keys())
            lines = []
            for k, v in data.items():
                lines.append(f"  {str(k):<{max_key_len}}  {v}")
            return "\n".join(lines)

        # リスト of dict の場合（テーブル表示）
        for key, value in data.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return OutputFormatter._dict_list_to_table(value)

        return OutputFormatter._format_text(data)
```

#### 2.1.6 develop set 特殊コマンド設計

100+のdevelopパラメータを個別のサブコマンドにせず、統一的に扱う:

```
# 単一パラメータ設定
lr develop set exposure 0.5
lr develop set contrast 20
lr develop set --param Temperature --value 5500

# 複数パラメータ一括設定
lr develop set exposure 0.5 contrast 20 highlights -30
lr develop batch --file settings.json

# パラメータ情報取得
lr develop get exposure
lr develop get --all
lr develop range exposure  # 有効範囲を表示: -5.0 ~ +5.0

# パラメータ一覧
lr develop params           # 全パラメータ一覧
lr develop params --group basic  # basicグループのみ
```

パラメータ名はタブ補完で補完できるようにする:

```python
# cli/completions.py

from lightroom_sdk.types.develop import DEVELOP_PARAMETER_RANGES

def complete_develop_param(ctx, param, incomplete):
    """developパラメータ名のタブ補完"""
    params = list(DEVELOP_PARAMETER_RANGES.keys())
    # case-insensitiveマッチ
    return [p for p in params if p.lower().startswith(incomplete.lower())]
```

### 2.2 プラグイン安定化

#### 2.2.1 Luaシャットダウン問題の完全修正

**現状分析**:
- `SHUTDOWN_FIXES.md` の修正は適用済みだが、根本原因がいくつか残存
- `LrFunctionContext.callWithContext` 内のソケットが `context` のスコープ外で参照される場合のクラッシュ
- `PluginShutdown.lua` と `AppShutdown.lua` がほぼ同一コードで冗長

**修正方針**:

1. **シャットダウンシーケンスの明確化**

```
[Lightroom終了]
    ↓
[AppShutdown.lua] ← LrApplicationがコール
    ├─ _G.LightroomPythonBridge.shuttingDown = true を設定
    ├─ SimpleSocketBridge.stop() を呼出し
    │    ├─ socketServerRunning = false
    │    ├─ server.shutdown イベント送信 (500ms待機)
    │    ├─ ポートファイル削除
    │    └─ commandRouter クリーンアップ
    └─ 即座に return（ブロッキング禁止）

[PluginShutdown.lua] ← プラグイン無効化時のみ
    ├─ AppShutdown と同じ処理（ただし shuttingDown チェック）
    └─ 二重実行を防止
```

2. **`shuttingDown` フラグの追加**

```lua
-- SimpleSocketBridge.lua 修正
local function stopSocketServer()
    local logger = getLogger()

    -- グローバルシャットダウンフラグを最初に設定
    if _G.LightroomPythonBridge then
        _G.LightroomPythonBridge.shuttingDown = true
        _G.LightroomPythonBridge.socketServerRunning = false
    end

    -- シャットダウン通知（タイムアウト付き）
    if commandRouter and commandRouter.socketBridge then
        local notifySent = false
        pcall(function()
            commandRouter:sendEvent("server.shutdown", { reason = "Lightroom closing" })
            notifySent = true
        end)
        if notifySent then
            -- Python側に切断の猶予を与える（最大500ms）
            LrTasks.sleep(0.5)
        end
    end

    -- 状態リセット（pcallで保護）
    pcall(function()
        bothSocketsReady = false
        messageQueue = {}
        isRestarting = false
        globalSender = nil
        senderSocket = nil
        commandRouter = nil
    end)

    -- ポートファイル削除
    pcall(function()
        os.remove("/tmp/lightroom_ports.txt")
    end)
end
```

3. **PluginShutdown.lua / AppShutdown.lua の統一**

```lua
-- AppShutdown.lua (新)
local LrLogger = import 'LrLogger'
local myLogger = LrLogger('AppShutdown')
myLogger:enable("logfile")

local bridge = _G.LightroomPythonBridge

if bridge then
    -- 既にシャットダウン中なら何もしない
    if bridge.shuttingDown then
        myLogger:info("Shutdown already in progress - skipping")
        return
    end

    local logger = bridge.logger or myLogger
    logger:info("Application shutdown initiated")

    bridge.running = false
    bridge.shuttingDown = true

    local SimpleSocketBridge = require 'SimpleSocketBridge'
    if SimpleSocketBridge.isRunning() then
        logger:info("Stopping socket server...")
        SimpleSocketBridge.stop()
    end

    logger:info("Application shutdown complete")
else
    myLogger:warn("Plugin global state not found during shutdown")
end
```

4. **onClosed / onError ハンドラの防御的実装**

```lua
-- SimpleSocketBridge.lua の onClosed/onError 修正
onClosed = function(socket)
    -- shuttingDown フラグチェック（socketServerRunning より先に確認）
    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.shuttingDown then
        -- シャットダウン中: 何もしない
        return
    end

    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning then
        restartSocketServer()
    end
end,

onError = function(socket, err)
    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.shuttingDown then
        return  -- シャットダウン中のエラーは無視
    end

    local logger = getLogger()
    logger:error("Socket error: " .. tostring(err))

    if err == "timeout" and _G.LightroomPythonBridge
       and _G.LightroomPythonBridge.socketServerRunning then
        pcall(function() socket:reconnect() end)
    end
end
```

#### 2.2.2 Python側 再接続ロジック改善

**現状の問題**:
- `ResilientClientManager.execute_with_retry()` は接続エラー文字列のパターンマッチに依存
- 再接続後の状態検証（ping）がない
- `server.shutdown` イベントを受信してもハンドリングしていない

**改善設計**:

```python
# lightroom_sdk/resilient_socket_bridge.py

import asyncio
import logging
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    SHUTDOWN = "shutdown"  # サーバー側からのシャットダウン通知後

class ResilientSocketBridge:
    """再接続機能を備えたソケットブリッジ"""

    def __init__(self, host: str = 'localhost',
                 port_file: str = '/tmp/lightroom_ports.txt',
                 max_reconnect_attempts: int = 5,
                 reconnect_base_delay: float = 1.0,
                 heartbeat_interval: float = 30.0):
        self._host = host
        self._port_file = port_file
        self._max_reconnect_attempts = max_reconnect_attempts
        self._reconnect_base_delay = reconnect_base_delay
        self._heartbeat_interval = heartbeat_interval

        self._state = ConnectionState.DISCONNECTED
        self._bridge: Optional[SocketBridge] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._reconnect_lock = asyncio.Lock()
        self._on_disconnect_callbacks = []
        self._on_reconnect_callbacks = []

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == ConnectionState.CONNECTED

    async def connect(self) -> None:
        """初回接続"""
        self._state = ConnectionState.CONNECTING
        from .socket_bridge import SocketBridge
        self._bridge = SocketBridge(self._host, self._port_file)

        # シャットダウンイベントハンドラを登録
        self._bridge.on_event('server.shutdown', self._handle_shutdown_event)

        await self._bridge.connect()
        self._state = ConnectionState.CONNECTED

        # ハートビート開始
        self._start_heartbeat()

    async def send_command(self, command: str, params: Optional[Dict] = None,
                           timeout: float = 30.0) -> Dict[str, Any]:
        """コマンド送信（自動再接続付き）"""
        if self._state == ConnectionState.SHUTDOWN:
            raise ConnectionError("Lightroom has shut down")

        last_error = None
        for attempt in range(self._max_reconnect_attempts):
            try:
                if not self.is_connected:
                    await self._reconnect()

                return await self._bridge.send_command(command, params, timeout)

            except Exception as e:
                last_error = e
                if self._is_connection_error(e):
                    logger.warning(
                        f"Connection error (attempt {attempt + 1}/"
                        f"{self._max_reconnect_attempts}): {e}"
                    )
                    self._state = ConnectionState.DISCONNECTED
                    if attempt < self._max_reconnect_attempts - 1:
                        delay = self._reconnect_base_delay * (2 ** attempt)
                        await asyncio.sleep(min(delay, 30.0))  # 最大30秒
                        continue
                else:
                    raise  # 接続エラー以外は即座にraise

        raise last_error

    async def _reconnect(self) -> None:
        """再接続処理"""
        async with self._reconnect_lock:
            if self.is_connected:
                return  # 別スレッドで既に再接続済み

            self._state = ConnectionState.RECONNECTING
            logger.info("Attempting reconnection to Lightroom...")

            # 既存接続のクリーンアップ
            if self._bridge:
                try:
                    await self._bridge.disconnect()
                except Exception:
                    pass

            # 新規接続
            from .socket_bridge import SocketBridge
            self._bridge = SocketBridge(self._host, self._port_file)
            self._bridge.on_event('server.shutdown', self._handle_shutdown_event)
            await self._bridge.connect()

            # 接続検証
            await self._bridge.send_command("system.ping", timeout=5.0)

            self._state = ConnectionState.CONNECTED
            logger.info("Reconnection successful")

            for callback in self._on_reconnect_callbacks:
                try:
                    await callback()
                except Exception as e:
                    logger.error(f"Reconnect callback error: {e}")

    async def _handle_shutdown_event(self, event_data: Dict) -> None:
        """サーバーからのシャットダウン通知を処理"""
        logger.info(f"Received shutdown notification: {event_data}")
        self._state = ConnectionState.SHUTDOWN
        self._stop_heartbeat()

        if self._bridge:
            try:
                await self._bridge.disconnect()
            except Exception:
                pass

    def _start_heartbeat(self) -> None:
        """ハートビートタスクを開始"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    def _stop_heartbeat(self) -> None:
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

    async def _heartbeat_loop(self) -> None:
        """定期的に接続を確認"""
        while self._state == ConnectionState.CONNECTED:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                if self._bridge and self.is_connected:
                    await self._bridge.send_command("system.ping", timeout=5.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")
                self._state = ConnectionState.DISCONNECTED

    @staticmethod
    def _is_connection_error(error: Exception) -> bool:
        """接続エラーかどうかを判定"""
        from .exceptions import ConnectionError as LRConnectionError, TimeoutError as LRTimeoutError

        if isinstance(error, (LRConnectionError, LRTimeoutError)):
            return True

        error_str = str(error).lower()
        connection_indicators = [
            'connection reset', 'broken pipe', 'connection lost',
            'connection closed', 'connection refused',
            'errno 54', 'errno 32', 'errno 61',
            'not connected', 'eof', 'peer closed'
        ]
        return any(ind in error_str for ind in connection_indicators)

    async def disconnect(self) -> None:
        """明示的な切断"""
        self._stop_heartbeat()
        self._state = ConnectionState.DISCONNECTED
        if self._bridge:
            await self._bridge.disconnect()
```

#### 2.2.3 ソケットブリッジのイベントハンドリング追加

現在の `socket_bridge.py` の `_handle_message` は event を受信しても何もしない。これを改善する:

```python
# socket_bridge.py への追加

class SocketBridge:
    def __init__(self, ...):
        # 既存フィールド
        self._event_handlers: Dict[str, List[Callable]] = {}

    def on_event(self, event_name: str, handler: Callable) -> None:
        """イベントハンドラを登録"""
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(handler)

    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """受信メッセージのルーティング"""
        # イベントハンドリング
        if 'event' in message:
            event_name = message['event']
            event_data = message.get('data', {})
            logger.debug(f"Event received: {event_name}")

            handlers = self._event_handlers.get(event_name, [])
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event_data)
                    else:
                        handler(event_data)
                except Exception as e:
                    logger.error(f"Event handler error for {event_name}: {e}")
            return

        # レスポンスハンドリング（既存コード）
        request_id = message.get('id')
        if request_id and request_id in self._pending_requests:
            future = self._pending_requests.pop(request_id)
            if not future.cancelled():
                future.set_result(message)
```

#### 2.2.4 タイムアウト・リトライ戦略

```python
# lightroom_sdk/retry.py

from dataclasses import dataclass
from typing import Optional

@dataclass
class RetryConfig:
    """リトライ設定"""
    max_attempts: int = 3
    base_delay: float = 0.5       # 初回リトライまでの待機(秒)
    max_delay: float = 30.0       # 最大待機時間(秒)
    backoff_factor: float = 2.0   # 指数バックオフ係数

    # コマンドカテゴリごとのタイムアウト
    default_timeout: float = 30.0
    preview_timeout: float = 120.0  # プレビュー生成は時間がかかる
    batch_timeout: float = 300.0    # バッチ操作

# デフォルト設定
DEFAULT_RETRY_CONFIG = RetryConfig()

# コマンド別タイムアウトマッピング
COMMAND_TIMEOUTS = {
    "system.ping": 5.0,
    "system.status": 10.0,
    "preview.generatePreview": 120.0,
    "preview.generateBatchPreviews": 300.0,
    "develop.batchApplySettings": 60.0,
    # その他はデフォルト（30秒）
}
```

### 2.3 リポジトリ構成

#### 2.3.1 ディレクトリ構造

```
lightroom-mcp/
├── README.md                    # クイックスタート + 概要
├── LICENSE                      # MIT License
├── CONTRIBUTING.md              # コントリビュータガイド
├── CHANGELOG.md                 # リリースノート
├── pyproject.toml               # パッケージ定義 + CLI エントリポイント
├── Makefile                     # 一般的な開発タスク
│
├── lightroom_sdk/               # Python SDK（コアライブラリ）
│   ├── __init__.py
│   ├── client.py                # LightroomClient
│   ├── socket_bridge.py         # TCPソケット通信
│   ├── resilient_bridge.py      # 再接続機能付きブリッジ (新規)
│   ├── protocol.py              # リクエスト/レスポンス定義
│   ├── exceptions.py            # エラー定義
│   ├── retry.py                 # リトライ設定 (新規)
│   ├── command_registry.py      # コマンドレジストリ (新規)
│   └── types/
│       ├── __init__.py
│       ├── develop.py           # パラメータ範囲定義
│       └── catalog.py           # カタログ型定義
│
├── cli/                         # CLI アプリケーション (新規)
│   ├── __init__.py
│   ├── main.py                  # Click エントリポイント
│   ├── output.py                # 出力フォーマッター
│   ├── completions.py           # タブ補完
│   ├── config.py                # CLI設定管理
│   └── commands/                # コマンド定義（自動登録）
│       ├── __init__.py
│       ├── system.py
│       ├── catalog.py
│       ├── develop.py
│       └── preview.py
│
├── mcp_server/                  # MCPサーバー
│   ├── __init__.py
│   ├── main.py                  # FastMCP composition
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── error_handler.py
│   ├── servers/
│   │   ├── __init__.py
│   │   ├── system.py
│   │   ├── catalog.py
│   │   ├── develop/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── basic_tools.py
│   │   │   ├── parameter_management.py
│   │   │   ├── tone_curves.py
│   │   │   ├── color_tools.py
│   │   │   ├── detail_tools.py
│   │   │   ├── effects_tools.py
│   │   │   ├── lens_tools.py
│   │   │   ├── calibration_tools.py
│   │   │   └── helper_tools.py
│   │   └── preview.py
│   └── shared/
│       ├── __init__.py
│       ├── base.py
│       ├── client.py
│       └── resilient_client.py
│
├── lightroom-plugin/            # Lua プラグイン（名称変更）
│   ├── Info.lua
│   ├── PluginInit.lua
│   ├── PluginShutdown.lua
│   ├── AppShutdown.lua
│   ├── SimpleSocketBridge.lua
│   ├── CommandRouter.lua
│   ├── MessageProtocol.lua
│   ├── Config.lua
│   ├── Logger.lua
│   ├── ErrorUtils.lua
│   ├── CatalogModule.lua
│   ├── DevelopModule.lua
│   ├── PreviewModule.lua
│   ├── MenuActions.lua
│   └── StopMenuAction.lua
│
├── scripts/                     # ユーティリティスクリプト (新規)
│   ├── install.sh               # ワンライナーインストール
│   ├── install-plugin.sh        # Luaプラグインのインストール
│   └── check-connection.py      # 接続診断ツール
│
├── tests/                       # テスト (新規/再構成)
│   ├── conftest.py              # 共通フィクスチャ
│   ├── mocks/
│   │   ├── __init__.py
│   │   ├── lightroom_mock.py    # Lightroom応答のモック
│   │   └── socket_mock.py       # ソケット通信のモック
│   ├── unit/
│   │   ├── test_client.py
│   │   ├── test_socket_bridge.py
│   │   ├── test_resilient_bridge.py
│   │   ├── test_protocol.py
│   │   ├── test_command_registry.py
│   │   ├── test_cli_commands.py
│   │   └── test_output_formatter.py
│   ├── integration/
│   │   ├── test_mcp_server.py
│   │   ├── test_cli_e2e.py
│   │   └── test_reconnection.py
│   └── fixtures/
│       ├── responses/           # Lightroom応答のJSONフィクスチャ
│       │   ├── ping.json
│       │   ├── get_settings.json
│       │   ├── get_selected_photos.json
│       │   └── ...
│       └── commands/            # コマンド入力のフィクスチャ
│           └── ...
│
└── docs/
    ├── API_REFERENCE.md
    ├── API_DEVELOP_REFERENCE.md
    ├── CLI_REFERENCE.md         # CLI コマンドリファレンス (新規)
    ├── INSTALL.md               # 詳細インストールガイド (新規)
    ├── ARCHITECTURE.md          # アーキテクチャ概要 (新規)
    └── plans/
        └── 2026-03-04-cli-and-stabilization-design.md
```

#### 2.3.2 pyproject.toml

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "lightroom-mcp"
version = "1.0.0"
description = "MCP server and CLI for Adobe Lightroom Classic"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.10"
authors = [
    {name = "motokiendo"}
]
keywords = ["lightroom", "mcp", "photo-editing", "cli"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Multimedia :: Graphics",
]

dependencies = [
    "click>=8.1",
    "fastmcp>=0.1",
    "httpx>=0.25",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "Pillow>=10.0",
    "rich>=13.0",         # リッチなターミナル出力
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
    "pytest-mock>=3.10",
    "ruff>=0.1",
    "mypy>=1.5",
]

[project.scripts]
lr = "cli.main:cli"
lightroom-mcp = "mcp_server.main:main_server"

[project.urls]
Homepage = "https://github.com/motokiendo/lightroom-mcp"
Documentation = "https://github.com/motokiendo/lightroom-mcp/tree/main/docs"
Issues = "https://github.com/motokiendo/lightroom-mcp/issues"

[tool.setuptools.packages.find]
include = ["lightroom_sdk*", "mcp_server*", "cli*"]

[tool.ruff]
target-version = "py310"
line-length = 100

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
```

#### 2.3.3 インストール手順設計

**ワンライナーインストール**:

```bash
# scripts/install.sh
#!/bin/bash
set -euo pipefail

echo "=== Lightroom MCP Installer ==="
echo ""

# 1. Python環境チェック
PYTHON=$(command -v python3 || true)
if [ -z "$PYTHON" ]; then
    echo "ERROR: Python 3.10+ is required"
    exit 1
fi

PY_VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python version: $PY_VERSION"

# 2. パッケージインストール
echo "Installing lightroom-mcp..."
pip install -e ".[dev]"

# 3. Lightroom プラグイン検出
LR_PLUGIN_DIR="$HOME/Library/Application Support/Adobe/Lightroom/Modules"
if [ ! -d "$LR_PLUGIN_DIR" ]; then
    mkdir -p "$LR_PLUGIN_DIR"
fi

# 4. プラグインのシンボリックリンク作成
SCRIPT_DIR=$(cd "$(dirname "$0")/.." && pwd)
PLUGIN_SRC="$SCRIPT_DIR/lightroom-plugin"
PLUGIN_DEST="$LR_PLUGIN_DIR/lightroom-python-bridge.lrdevplugin"

if [ -L "$PLUGIN_DEST" ] || [ -d "$PLUGIN_DEST" ]; then
    echo "Plugin already installed at $PLUGIN_DEST"
    read -p "Overwrite? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$PLUGIN_DEST"
    else
        echo "Skipping plugin installation"
        SKIP_PLUGIN=true
    fi
fi

if [ "${SKIP_PLUGIN:-false}" != "true" ]; then
    ln -s "$PLUGIN_SRC" "$PLUGIN_DEST"
    echo "Plugin linked: $PLUGIN_DEST -> $PLUGIN_SRC"
fi

# 5. MCP設定ファイルの雛形生成
MCP_CONFIG="$HOME/.claude/mcp.json"
echo ""
echo "To add to Claude Desktop, add this to $MCP_CONFIG:"
echo ""
echo "  \"lightroom-mcp\": {"
echo "    \"command\": \"$PYTHON\","
echo "    \"args\": [\"-m\", \"mcp_server.main\"],"
echo "    \"cwd\": \"$SCRIPT_DIR\""
echo "  }"
echo ""

# 6. 接続テスト
echo "Testing connection..."
if lr system ping 2>/dev/null; then
    echo "SUCCESS: Connected to Lightroom"
else
    echo "NOTE: Lightroom is not running or plugin is not active"
    echo "      Start Lightroom and enable the plugin, then run: lr system ping"
fi

echo ""
echo "=== Installation complete ==="
echo "Run 'lr --help' to see available commands"
```

### 2.4 主要な技術的判断とその根拠

| 判断 | 選択 | 根拠 |
|------|------|------|
| CLIフレームワーク | Click | Python標準的CLIフレームワーク。サブコマンド・ネスト・タブ補完・ヘルプ生成が充実。Typerより依存が少なく安定 |
| 出力ライブラリ | Rich | テーブル・プログレスバー・シンタックスハイライト対応。JSON出力と人間可読出力の切替に最適 |
| MCPとCLIの関係 | 独立パス（両方がlightroom_sdkを直接使用） | CLIがMCPサーバーを経由するとMCPサーバーの起動が必要になり、UXが悪化。SDKを直接使うことで即座に実行可能 |
| プラグインディレクトリ名 | `lightroom-plugin/` に変更 | `.lrdevplugin` サフィックスはシンボリックリンク先で維持。リポジトリ内ではシンプルな名前に |
| パラメータバリデーション | SDK層（types/develop.py）で一元管理 | MCPサーバー・CLI両方で同じバリデーションを使用。DRY原則 |
| 再接続戦略 | 指数バックオフ + ハートビート | ネットワーク障害のベストプラクティス。ハートビートで接続切れの早期検出 |
| イベント通信 | 既存socket_bridgeに`on_event`追加 | 新規プロトコルの導入なしでシャットダウン通知を受信可能。最小変更原則 |
| Python最低バージョン | 3.10 | match文・パターンマッチングを活用可能。主要OS標準で3.10+が利用可能 |
| テストフレームワーク | pytest + pytest-asyncio + pytest-mock | 非同期テスト対応。フィクスチャベースのモック戦略と親和性が高い |
| `time.sleep(0.1)` in client.py | 削除 | 同期的なブロッキングsleepがasyncio内で使われている。非同期スリープに置換するか、必要性を再評価して削除 |

### 2.5 テスト戦略

#### 2.5.1 基本方針

Lightroomを必要としないテストを最大化する。テストピラミッドの各層を明確に分離する。

```
[E2E テスト] ← Lightroom実機が必要（手動/CI外）
    ↓
[インテグレーションテスト] ← モックソケットで通信を再現
    ↓
[ユニットテスト] ← 各コンポーネント単体テスト（大量）
```

#### 2.5.2 モック戦略

```python
# tests/mocks/lightroom_mock.py

import asyncio
import json
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field

@dataclass
class MockLightroomResponse:
    """Lightroomの応答をシミュレート"""
    command: str
    response: Dict[str, Any]
    delay: float = 0.0  # 応答遅延（タイムアウトテスト用）

class MockLightroomServer:
    """Lightroom Luaプラグインのモックサーバー"""

    def __init__(self):
        self._responses: Dict[str, MockLightroomResponse] = {}
        self._request_log: list = []
        self._sender_server: Optional[asyncio.Server] = None
        self._receiver_server: Optional[asyncio.Server] = None
        self._client_writer: Optional[asyncio.StreamWriter] = None
        self._port_file = '/tmp/lightroom_ports_test.txt'

    def register_response(self, command: str, result: Dict[str, Any],
                          success: bool = True, delay: float = 0.0):
        """コマンドに対する応答を登録"""
        self._responses[command] = MockLightroomResponse(
            command=command,
            response={
                "success": success,
                "result": result if success else None,
                "error": result if not success else None,
            },
            delay=delay,
        )

    def register_default_responses(self):
        """よく使う応答をまとめて登録"""
        self.register_response("system.ping", {"pong": True, "timestamp": 1234567890})
        self.register_response("system.status", {
            "connected": True, "uptime": 3600, "requestCount": 42
        })
        self.register_response("catalog.getSelectedPhotos", {
            "count": 1, "photos": [{"id": "photo-1", "fileName": "test.CR3"}]
        })
        self.register_response("develop.getSettings", {
            "photoId": "photo-1",
            "settings": {"Exposure": 0.0, "Contrast": 0, "Highlights": 0}
        })
        self.register_response("develop.setValue", {
            "photoId": "photo-1", "param": "Exposure", "value": 0.5
        })

    async def start(self) -> tuple[int, int]:
        """モックサーバーを起動してポート番号を返す"""
        # Sender server (Python receives FROM here)
        self._sender_server = await asyncio.start_server(
            self._handle_sender_connection, 'localhost', 0
        )
        sender_port = self._sender_server.sockets[0].getsockname()[1]

        # Receiver server (Python sends TO here)
        self._receiver_server = await asyncio.start_server(
            self._handle_receiver_connection, 'localhost', 0
        )
        receiver_port = self._receiver_server.sockets[0].getsockname()[1]

        # ポートファイル書き込み
        with open(self._port_file, 'w') as f:
            f.write(f"{sender_port},{receiver_port}")

        return sender_port, receiver_port

    async def stop(self):
        """モックサーバーを停止"""
        if self._sender_server:
            self._sender_server.close()
        if self._receiver_server:
            self._receiver_server.close()

        import os
        try:
            os.remove(self._port_file)
        except FileNotFoundError:
            pass

    async def _handle_sender_connection(self, reader, writer):
        """Sender接続ハンドラ（Pythonにデータを送信）"""
        self._client_writer = writer

    async def _handle_receiver_connection(self, reader, writer):
        """Receiver接続ハンドラ（Pythonからデータを受信）"""
        buffer = b""
        while True:
            try:
                data = await reader.read(8192)
                if not data:
                    break

                buffer += data
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    request = json.loads(line.decode('utf-8'))
                    self._request_log.append(request)

                    # 応答を送信
                    await self._send_response(request)
            except Exception:
                break

    async def _send_response(self, request: Dict[str, Any]):
        """リクエストに対応する応答を送信"""
        command = request.get('command', '')
        request_id = request.get('id', '')

        mock_response = self._responses.get(command)
        if mock_response:
            if mock_response.delay > 0:
                await asyncio.sleep(mock_response.delay)

            response = {
                "id": request_id,
                **mock_response.response,
            }
        else:
            response = {
                "id": request_id,
                "success": False,
                "error": {"code": "UNKNOWN_COMMAND", "message": f"Unknown: {command}"}
            }

        if self._client_writer:
            data = json.dumps(response) + '\n'
            self._client_writer.write(data.encode('utf-8'))
            await self._client_writer.drain()

    async def send_event(self, event_name: str, data: Dict[str, Any]):
        """イベントを送信（シャットダウン通知テスト等）"""
        if self._client_writer:
            event = {"event": event_name, "data": data}
            event_data = json.dumps(event) + '\n'
            self._client_writer.write(event_data.encode('utf-8'))
            await self._client_writer.drain()
```

#### 2.5.3 テストフィクスチャ

```python
# tests/conftest.py

import pytest
import asyncio
from tests.mocks.lightroom_mock import MockLightroomServer
from lightroom_sdk import LightroomClient

@pytest.fixture
async def mock_lightroom():
    """モックLightroomサーバーを起動"""
    server = MockLightroomServer()
    server.register_default_responses()
    ports = await server.start()
    yield server
    await server.stop()

@pytest.fixture
async def connected_client(mock_lightroom):
    """接続済みクライアント"""
    client = LightroomClient()
    client._bridge.port_file = mock_lightroom._port_file
    await client.connect()
    yield client
    await client.disconnect()

@pytest.fixture
def cli_runner():
    """Click CLIテストランナー"""
    from click.testing import CliRunner
    return CliRunner()
```

#### 2.5.4 テストカテゴリ

| カテゴリ | Lightroom不要 | テスト内容 | 例 |
|---------|-------------|-----------|-----|
| ユニット: プロトコル | はい | LightroomRequest/Response のシリアライズ | `test_protocol.py` |
| ユニット: バリデーション | はい | パラメータ範囲チェック | `test_develop_params()` |
| ユニット: コマンドレジストリ | はい | デコレータによる登録・取得 | `test_command_registry.py` |
| ユニット: 出力フォーマッター | はい | JSON/テキスト/テーブル変換 | `test_output_formatter.py` |
| ユニット: リトライロジック | はい | 指数バックオフ計算 | `test_retry.py` |
| 統合: ソケット通信 | はい(モック) | 接続・コマンド送受信・切断 | `test_socket_bridge.py` |
| 統合: 再接続 | はい(モック) | 接続切れ→自動再接続→コマンド再実行 | `test_reconnection.py` |
| 統合: シャットダウン | はい(モック) | server.shutdownイベント受信→状態遷移 | `test_shutdown.py` |
| 統合: タイムアウト | はい(モック) | コマンドタイムアウト→リトライ | `test_timeout.py` |
| 統合: CLIコマンド | はい(モック) | `lr system ping` の出力検証 | `test_cli_commands.py` |
| 統合: MCPサーバー | はい(モック) | FastMCPツール呼び出し→SDK→モック | `test_mcp_server.py` |
| E2E | いいえ | 実際のLightroomとの通信 | 手動テスト |

#### 2.5.5 テスト例

```python
# tests/unit/test_command_registry.py

from lightroom_sdk.command_registry import CommandRegistry, CommandDefinition

def test_register_command():
    @CommandRegistry.register(category="develop", lr_command="setValue")
    async def adjust_exposure(value: float, photo_id: str = None):
        """Adjust exposure"""
        pass

    commands = CommandRegistry.get_all()
    assert "develop.adjust_exposure" in commands

    cmd = commands["develop.adjust_exposure"]
    assert cmd.category == "develop"
    assert len(cmd.parameters) == 2
    assert cmd.parameters[0].name == "value"
    assert cmd.parameters[0].required == True
    assert cmd.parameters[1].name == "photo_id"
    assert cmd.parameters[1].required == False


# tests/unit/test_output_formatter.py

from cli.output import OutputFormatter

def test_json_output():
    data = {"status": "connected", "latency_ms": 12.5}
    output = OutputFormatter.format(data, mode='json')
    import json
    parsed = json.loads(output)
    assert parsed["status"] == "connected"

def test_text_output():
    data = {"exposure": 0.5, "contrast": 20}
    output = OutputFormatter.format(data, mode='text')
    assert "exposure: 0.5" in output
    assert "contrast: 20" in output


# tests/integration/test_reconnection.py

import pytest

@pytest.mark.asyncio
async def test_auto_reconnect_after_connection_lost(mock_lightroom):
    """接続切れ後の自動再接続"""
    from lightroom_sdk.resilient_bridge import ResilientSocketBridge, ConnectionState

    bridge = ResilientSocketBridge(port_file=mock_lightroom._port_file)
    await bridge.connect()
    assert bridge.state == ConnectionState.CONNECTED

    # サーバー停止→再起動をシミュレート
    await mock_lightroom.stop()
    await mock_lightroom.start()

    # コマンド実行時に自動再接続
    result = await bridge.send_command("system.ping")
    assert result["success"] == True
    assert bridge.state == ConnectionState.CONNECTED

@pytest.mark.asyncio
async def test_shutdown_event_handling(mock_lightroom):
    """シャットダウンイベント受信時の動作"""
    from lightroom_sdk.resilient_bridge import ResilientSocketBridge, ConnectionState

    bridge = ResilientSocketBridge(port_file=mock_lightroom._port_file)
    await bridge.connect()

    # シャットダウンイベント送信
    await mock_lightroom.send_event("server.shutdown", {"reason": "Lightroom closing"})
    await asyncio.sleep(0.1)

    assert bridge.state == ConnectionState.SHUTDOWN


# tests/integration/test_cli_commands.py

from click.testing import CliRunner
from cli.main import cli

def test_cli_ping(cli_runner, mock_lightroom):
    result = cli_runner.invoke(cli, ['system', 'ping'])
    assert result.exit_code == 0
    assert "connected" in result.output

def test_cli_json_output(cli_runner, mock_lightroom):
    result = cli_runner.invoke(cli, ['-o', 'json', 'system', 'ping'])
    assert result.exit_code == 0
    import json
    data = json.loads(result.output)
    assert data["status"] == "connected"

def test_cli_develop_set(cli_runner, mock_lightroom):
    result = cli_runner.invoke(cli, ['develop', 'set', 'exposure', '0.5'])
    assert result.exit_code == 0
    assert "Exposure" in result.output
```

---

## 3. 実装フェーズ

### Phase 1: SDK安定化 (1-2週間)

1. `socket_bridge.py` にイベントハンドリング追加
2. `resilient_bridge.py` 新規作成（再接続・ハートビート・シャットダウンイベント対応）
3. `retry.py` 新規作成
4. `client.py` の `time.sleep(0.1)` 削除
5. Lua側シャットダウン修正（`shuttingDown` フラグ追加）
6. テスト: `MockLightroomServer` + 再接続/タイムアウト/シャットダウンのテスト

### Phase 2: CLIフレームワーク (1-2週間)

1. `command_registry.py` 新規作成
2. `cli/main.py` Clickエントリポイント作成
3. `cli/output.py` 出力フォーマッター作成
4. systemコマンド群を実装（ping, status, reconnect）
5. `pyproject.toml` にCLIエントリポイント追加
6. テスト: CLIコマンドのユニット/統合テスト

### Phase 3: コマンド移植 (1-2週間)

1. catalogコマンド群をCLIに移植
2. developコマンド群をCLIに移植（`develop set` 統合コマンド含む）
3. previewコマンド群をCLIに移植
4. タブ補完実装
5. テスト: 全コマンドのテスト

### Phase 4: パブリックリリース準備 (1週間)

1. ディレクトリ名変更（`lightroom-python-bridge.lrdevplugin` → `lightroom-plugin`）
2. `scripts/install.sh` 作成
3. README.md 書き直し
4. CLI_REFERENCE.md 作成
5. CONTRIBUTING.md 作成
6. CHANGELOG.md 作成
7. GitHub Actions CI設定

---

## 4. 未解決の設計判断

| 項目 | 選択肢 | 推奨 | 要確認事項 |
|------|--------|------|-----------|
| パッケージ配布 | PyPI vs GitHub Releases | PyPI（`pip install lightroom-mcp`） | PyPIアカウント・名前空間の確保 |
| Luaプラグインのバージョン管理 | リポジトリ内同梱 vs 別配布 | 同梱（symlink install） | Lightroom Plugin Manager対応は将来検討 |
| MCPサーバーとCLIの`ResilientClient`共有 | 共通インスタンス vs 独立インスタンス | 独立（CLIは短命、MCPは長命） | メモリ/接続リソースの考慮 |
| ハートビート間隔 | 15秒 / 30秒 / 60秒 | 30秒 | Lightroomへの負荷とのバランス |
| Lua側のログレベル制御 | Config.lua vs 環境変数 | Config.lua（既存パターン維持） | デバッグ時の切替容易性 |
