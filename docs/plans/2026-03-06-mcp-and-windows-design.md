# MCP Server + Windows 対応 設計書

**作成日**: 2026-03-06
**対象バージョン**: v1.0.0 -> v1.1.0
**ステータス**: Draft

---

## 1. アプローチ比較

### 1.1 MCP Server 実装アプローチ

| 観点 | A: fastmcp | B: mcp 公式 Python SDK | C: 独自 stdio 実装 |
|------|-----------|----------------------|-------------------|
| **実装コスト** | 低（デコレータベースで宣言的） | 中（低レベルAPI、ボイラープレート多め） | 高（プロトコル自前実装） |
| **依存関係** | fastmcp (既にvenvにある) | mcp (既にvenvにある、fastmcpの依存) | なし |
| **ツール定義** | `@mcp.tool()` デコレータ | `@server.call_tool()` ハンドラ | JSON-RPC 手動パース |
| **stdio対応** | 組み込み (`mcp.run()`) | 組み込み | 自前実装 |
| **エラーハンドリング** | 自動変換 | 手動だが型安全 | 完全手動 |
| **メンテナンス性** | 高（ライブラリがプロトコル変更を吸収） | 中 | 低（仕様変更を手動追従） |
| **コミュニティ** | 活発、Claude Desktop公式推奨 | 公式だがfastmcpに比べ冗長 | なし |
| **柔軟性** | 中（抽象化の制約あり） | 高 | 最高 |

**推奨: A (fastmcp)**

理由:
- venv に既にインストール済み（fastmcp 3.1.0, mcp 1.26.0）
- デコレータベースで 123 コマンドのマッピングを宣言的に記述可能
- stdio transport が組み込み
- YAGNI: 独自実装や低レベルAPIの柔軟性は不要

### 1.2 Windows Lua 対応アプローチ

| 観点 | A: LrPathUtils.getStandardFilePath("temp") | B: Lua sandbox 内判定 | C: Python→Lua 逆方向通信 |
|------|------------------------------------------|---------------------|------------------------|
| **実装コスト** | 低（1行変更） | 中（OS判定ロジック必要） | 高（通信プロトコル拡張） |
| **信頼性** | 高（Lightroom SDK公式API） | 中（sandbox制約で不確実） | 高だが複雑 |
| **macOS互換** | 要検証（macOSでも `/tmp` を返すか） | OS判定が必要 | 透過的 |
| **Lua sandbox制約** | SDK APIなので安全 | `os.getenv` 不可で困難 | SDK外通信が必要 |
| **メンテナンス性** | 高 | 低 | 低 |

**推奨: A (LrPathUtils.getStandardFilePath("temp"))**

理由:
- Lightroom SDK の公式 API で、sandbox 制約を受けない
- 最小変更（PlatformPaths.lua を1箇所修正するだけ）
- macOS では `LrPathUtils.getStandardFilePath("temp")` は `/tmp` を返すため後方互換
- Windows では `%TEMP%` 相当のパスを自動返却

**要検証事項**: `LrPathUtils.getStandardFilePath("temp")` の macOS での戻り値が `/tmp` であることを実機確認する必要がある。`/private/tmp` が返る可能性があるが、Python 側 paths.py は `/tmp/lightroom_ports.txt` をハードコードしているため、`/private/tmp` が返った場合でも symlink 経由で同一パスを指す（macOS では `/tmp` -> `/private/tmp`）。ただし念のため Python 側も `LrPathUtils` と同等のロジックに揃えるべき。

---

## 2. 推奨アプローチの詳細設計

### 2.1 アーキテクチャ

```
[Lightroom Classic]
    └── Lua Plugin (lightroom_sdk/plugin/)
           ↕ TCP Socket (dual: sender + receiver)
[Python SDK] (lightroom_sdk/)
    ├── socket_bridge.py
    ├── resilient_bridge.py
    ├── client.py             # 共有SDK層
    └── ...
        ↑                  ↑
   [CLI Layer]         [MCP Server Layer]      ← NEW
   cli/main.py         mcp_server/server.py
   (Click)             (fastmcp, stdio)
                            ↕ stdio
                    [Claude Desktop / Cowork]
```

**ポイント**:
- MCP Server は CLI と**並列のインターフェース層**。SDK（client.py）を直接使用する
- CLI を subprocess で呼ぶのではなく、`LightroomClient.execute_command()` を直接呼ぶ
- これにより CLI の Click パースオーバーヘッドを回避し、構造化データをネイティブにやりとりできる

### 2.2 MCP Server 設計

#### 2.2.1 ファイル構成

```
mcp_server/
    __init__.py
    server.py           # FastMCP サーバー定義 + ツール登録
    tool_registry.py    # schema.py → MCP ツール自動生成
    connection.py       # LightroomClient ライフサイクル管理
```

#### 2.2.2 ツールマッピング戦略

**方針: スキーマ駆動の自動生成（1:1 マッピング）**

123 コマンドを手動で MCP ツール化するのは非現実的。`lightroom_sdk/schema.py` の `COMMAND_SCHEMAS` を利用して自動生成する。

```python
# tool_registry.py（概念コード）
from lightroom_sdk.schema import COMMAND_SCHEMAS, CommandSchema

def register_all_tools(mcp: FastMCP, client: LightroomClient):
    for name, schema in COMMAND_SCHEMAS.items():
        # schema からパラメータ型を動的に構築
        tool_fn = create_tool_function(schema, client)
        mcp.tool(
            name=sanitize_tool_name(name),  # "catalog.searchPhotos" → "catalog_search_photos"
            description=schema.description,
        )(tool_fn)
```

**ツール名の変換規則**:
- `catalog.searchPhotos` → `lr_catalog_search_photos`（`lr_` prefix + snake_case）
- prefix `lr_` を付けて他の MCP ツールとの名前衝突を防止
- MCP ツール名は英数字とアンダースコアのみ許可

**パラメータマッピング**:

| schema.py ParamType | MCP JSON Schema type |
|---------------------|---------------------|
| STRING | `{"type": "string"}` |
| INTEGER | `{"type": "integer"}` |
| FLOAT | `{"type": "number"}` |
| BOOLEAN | `{"type": "boolean"}` |
| JSON_OBJECT | `{"type": "object"}` |
| JSON_ARRAY | `{"type": "array"}` |
| ENUM | `{"type": "string", "enum": [...]}` |

`required` フィールドと `description` はそのまま転写。`min`/`max` は JSON Schema の `minimum`/`maximum` に変換。

#### 2.2.3 グルーピングの検討と却下

MCP ツールの数が多い（123個）点について:
- Claude Desktop / Cowork は大量のツールを扱える（MCP プロトコルに上限なし）
- エージェントは `lr schema` 相当のディスカバリをツール一覧で自動的に行える
- グルーピング（例: `lr_develop` に全 develop コマンドを統合）は、パラメータが複雑になりすぎて逆にエージェントが迷う
- **結論: 1:1 マッピングを採用**。ただし `plugin.*` の3コマンド（install/uninstall/status）は MCP 経由で意味がないため除外 → **実質 120 ツール**

#### 2.2.4 接続ライフサイクル

```python
# connection.py（概念コード）
class ConnectionManager:
    """MCP Server のライフタイム中、LightroomClient の接続を管理"""

    def __init__(self):
        self._client: LightroomClient | None = None

    async def get_client(self) -> LightroomClient:
        if self._client is None:
            self._client = LightroomClient()
            await self._client.connect()
        return self._client

    async def shutdown(self):
        if self._client:
            await self._client.disconnect()
            self._client = None
```

- MCP Server は stdio ベースのため、プロセス起動 = セッション開始
- 初回ツール呼び出し時に lazy connect（起動時に Lightroom が未起動の可能性あり）
- 接続エラー時は MCP エラーレスポンスとして返す（プロセスは落とさない）

#### 2.2.5 エラーハンドリング方針

| SDK 例外 | MCP レスポンス |
|---------|--------------|
| `ConnectionError` | `isError: true`, message: "Lightroom に接続できません。Lightroom Classic が起動し、CLI Bridge プラグインが有効であることを確認してください。" |
| `TimeoutError` | `isError: true`, message: "コマンドがタイムアウトしました ({timeout}秒)。" |
| `LightroomSDKError` (VALIDATION) | `isError: true`, message: バリデーションエラー詳細 |
| `LightroomSDKError` (その他) | `isError: true`, message: エラー詳細 + suggestions |

- 全ツールで try/except し、構造化エラーメッセージを返す
- `suggestions` フィールドがある場合は MCP レスポンスに含める（エージェントの自己回復を支援）

#### 2.2.6 リソース定義

MCP Resources は**最小限**に留める:

| リソース URI | 説明 |
|-------------|------|
| `lightroom://status` | 接続状態 + Lightroom バージョン情報 |
| `lightroom://schema` | 全コマンドスキーマ一覧（エージェントのディスカバリ用） |

理由: Lightroom の写真データは大量で動的なため、Resource として静的に公開するのは不適切。ツール経由でクエリするのが自然。

#### 2.2.7 プロンプト定義

MCP Prompts は**設定しない**。

理由:
- SKILL.md が既にエージェント向けの詳細なガイドを提供している
- MCP Prompts は Claude Desktop UI からの手動呼び出し用だが、本ツールはエージェントファースト設計
- YAGNI

### 2.3 Windows 対応設計

#### 2.3.1 Lua 側修正 (PlatformPaths.lua)

```lua
-- 修正後
local LrPathUtils = import "LrPathUtils"

local PlatformPaths = {}

function PlatformPaths.getPortFilePath()
    local tempDir = LrPathUtils.getStandardFilePath("temp")
    return LrPathUtils.child(tempDir, "lightroom_ports.txt")
end

return PlatformPaths
```

変更点:
- `LrPathUtils.getStandardFilePath("temp")` で OS 非依存の temp ディレクトリ取得
- `LrPathUtils.child()` でパス結合（OS のパス区切り文字を自動処理）
- ハードコード `/tmp/lightroom_ports.txt` を完全除去

#### 2.3.2 Python 側修正 (paths.py)

現状の `get_port_file()` は既に win32 分岐済みだが、Lua 側と完全に一致させる:

```python
# 修正案: tempfile.gettempdir() を使用して OS に委ねる
import tempfile

def get_port_file() -> Path:
    env = os.environ.get("LR_PORT_FILE")
    if env:
        return Path(env)
    return Path(tempfile.gettempdir()) / "lightroom_ports.txt"
```

- `tempfile.gettempdir()` は macOS で `/tmp`、Windows で `%TEMP%` を返す
- Lua 側の `LrPathUtils.getStandardFilePath("temp")` と同じセマンティクス
- プラットフォーム分岐の if/elif を排除してシンプル化

#### 2.3.3 plugin.py 修正

| # | 問題 | 修正 |
|---|------|------|
| 1 | `--dev` symlink が Windows で管理者権限必須 | `os.name == "nt"` の場合、`--dev` を使用不可にする（`shutil.copytree` にフォールバックして警告表示） |
| 2 | 警告メッセージが不正確 | "Warning: --dev mode uses directory junction on Windows (no admin required)" に変更し、`os.symlink` の代わりに `subprocess.run(["cmd", "/c", "mklink", "/J", ...])` でジャンクション作成 |

**推奨: シンプルに `--dev` を Windows では警告つきで `copytree` にフォールバック**

理由:
- ジャンクション作成は追加の複雑性
- `--dev` は開発者向け機能で、Windows ユーザー（best effort コミュニティ）には必須でない
- copytree フォールバックなら追加の依存やOS API不要

#### 2.3.4 pyproject.toml 修正

```toml
classifiers = [
    ...
    "Operating System :: MacOS",
    "Operating System :: Microsoft :: Windows",  # 追加
]
```

### 2.4 配布設計

#### 2.4.1 pyproject.toml 変更

```toml
[project.scripts]
lr = "cli.main:cli"
lr-mcp = "mcp_server.server:main"    # NEW

[project.optional-dependencies]
mcp = [
    "fastmcp>=3.0",
]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
    "ruff>=0.4",
    "fastmcp>=3.0",                  # dev には含める
]

[tool.setuptools]
packages = ["lightroom_sdk", "lightroom_sdk.types", "cli", "cli.commands", "mcp_server"]  # mcp_server 追加
```

**fastmcp をオプション依存にする理由**:
- CLI ユーザーは MCP 不要（Click + Rich のみで動作）
- `pip install lightroom-cli` は最小依存のまま
- `pip install lightroom-cli[mcp]` で MCP 機能追加
- ただし `lr-mcp` エントリポイントは常に登録（import 時にエラーメッセージで `pip install lightroom-cli[mcp]` を案内）

#### 2.4.2 `lr mcp install` コマンド

Claude Desktop の設定ファイルに MCP Server 設定を自動追加するコマンド。

```
cli/commands/mcp.py  # NEW
```

**動作**:
1. Claude Desktop 設定ファイルのパスを特定:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
2. 既存の設定を読み込み（なければ空オブジェクト作成）
3. `mcpServers` に `lightroom-cli` エントリを追加:

```json
{
  "mcpServers": {
    "lightroom-cli": {
      "command": "lr-mcp",
      "args": []
    }
  }
}
```

4. 既存エントリがある場合は上書き確認
5. 設定ファイルを書き出し

**サブコマンド**:
- `lr mcp install` — 設定追加
- `lr mcp uninstall` — 設定削除
- `lr mcp status` — 設定状態表示
- `lr mcp test` — MCP Server の起動テスト（接続確認して即終了）

#### 2.4.3 lr-mcp エントリポイント

```python
# mcp_server/server.py
def main():
    """MCP Server エントリポイント (stdio)"""
    try:
        from fastmcp import FastMCP
    except ImportError:
        print(
            "Error: fastmcp is not installed. "
            "Install with: pip install lightroom-cli[mcp]",
            file=sys.stderr,
        )
        sys.exit(1)

    mcp = create_server()
    mcp.run(transport="stdio")
```

### 2.5 テスト戦略

#### 2.5.1 MCP Server テスト

| レイヤー | テスト方法 | ファイル |
|---------|----------|--------|
| tool_registry | schema.py → MCP ツール変換の単体テスト | `tests/test_mcp_tool_registry.py` |
| server | fastmcp の TestClient でツール呼び出し | `tests/test_mcp_server.py` |
| connection | MockLightroomServer との結合テスト | `tests/test_mcp_connection.py` |
| E2E | `lr mcp test` で Lightroom 実機テスト | `tests/e2e/test_mcp_e2e.py` |

**fastmcp TestClient の活用**:
```python
# 概念コード
from fastmcp.testing import TestClient

async def test_ping():
    server = create_server()
    async with TestClient(server) as client:
        result = await client.call_tool("lr_system_ping", {})
        assert result is not None
```

**MockLightroomServer との結合**:
- 既存の `tests/mocks/lightroom_mock.py` をそのまま活用
- MCP Server → SDK → MockServer の経路でテスト

#### 2.5.2 Windows CI

**方針: GitHub Actions に Windows matrix を追加**

```yaml
strategy:
  matrix:
    os: [macos-latest, windows-latest]
    python-version: ["3.10", "3.12"]
```

- Windows では E2E テスト（Lightroom 実機）は除外
- 単体テスト + MockServer テストのみ実行
- paths.py のプラットフォーム分岐テストを追加

#### 2.5.3 テスト追加リスト

| テスト | 内容 |
|-------|------|
| `test_paths_windows.py` | `get_port_file()` が win32 で `%TEMP%\lightroom_ports.txt` を返すことを monkeypatch で確認 |
| `test_mcp_tool_count.py` | 登録ツール数が `len(COMMAND_SCHEMAS) - 3` (plugin除外) と一致 |
| `test_mcp_tool_names.py` | ツール名が `lr_` prefix + snake_case の規則に従うことを確認 |
| `test_mcp_error_handling.py` | SDK 例外が MCP エラーレスポンスに正しく変換されることを確認 |
| `test_mcp_install_command.py` | `lr mcp install` が claude_desktop_config.json を正しく生成/更新することを確認 |

### 2.6 SKILL.md への影響

#### 2.6.1 更新方針

SKILL.md は **CLI 向けのまま維持**する。MCP Server 経由のエージェントには SKILL.md は不要（MCP ツール定義自体がドキュメント）。

追加するセクション:

```markdown
## MCP Server (Claude Desktop / Cowork)

CLI の代わりに MCP Server を使用する場合:

1. `pip install lightroom-cli[mcp]`
2. `lr mcp install` で Claude Desktop に設定追加
3. Claude Desktop を再起動

MCP ツール名は `lr_` prefix + snake_case (例: `lr_catalog_search_photos`)。
パラメータは CLI と同一。
```

#### 2.6.2 MCP ツールの description

各ツールの `description` は `CommandSchema.description` をそのまま使用。追加のコンテキスト（risk_level, requires_confirm 等）は description 末尾に付記:

```
"Search photos by various criteria. [read] Timeout: 60s"
"Remove photo from catalog. [destructive, requires confirm] Timeout: 30s"
```

---

## 3. 不確実な点・要確認事項

### 3.1 要実機検証

| # | 項目 | リスク | 検証方法 |
|---|------|--------|---------|
| 1 | `LrPathUtils.getStandardFilePath("temp")` が macOS で返す値 | `/private/tmp` の可能性。Python 側との一致が必要 | Lightroom のスクリプトコンソールで確認 |
| 2 | `LrPathUtils.getStandardFilePath("temp")` が Windows で返す値 | `%TEMP%` 相当だが実パスが未確認 | Windows 実機で確認 |
| 3 | fastmcp 3.x の TestClient API | バージョンにより API が異なる可能性 | fastmcp ドキュメント確認 |

### 3.2 設計判断の確認

| # | 判断 | 代替案 | 確認理由 |
|---|------|--------|---------|
| 1 | fastmcp をオプション依存にする | 必須依存にする | `pip install lightroom-cli` の最小依存を維持したいが、ユーザーの利便性とのトレードオフ |
| 2 | plugin.* コマンドを MCP から除外 | 含める | MCP 経由でプラグインインストールは意味がないと判断したが、status は有用かもしれない |
| 3 | MCP ツール 120 個の一括登録 | カテゴリ別に分割登録 | Claude Desktop が 120 ツールをパフォーマンス劣化なく扱えるか |
| 4 | `--dev` を Windows で copytree フォールバック | ジャンクション作成 | 開発者体験とのトレードオフ |

### 3.3 将来課題（スコープ外）

- **MCP Sampling**: エージェントが LLM を呼び出して写真の編集方針を判断する機能（将来版）
- **MCP Streamable HTTP**: リモートサーバー化（現在は stdio のみ、ローカル通信前提）
- **Linux 対応**: paths.py の Linux 分岐（Lightroom Classic が Linux 非対応なので優先度低）

---

## 4. 実装順序（推奨）

| Phase | 内容 | 見積もり |
|-------|------|---------|
| 1 | Windows Lua/Python 修正（PlatformPaths.lua + paths.py + plugin.py） | 1-2h |
| 2 | mcp_server/ 骨格 + tool_registry.py（スキーマ駆動自動生成） | 2-3h |
| 3 | connection.py + エラーハンドリング | 1-2h |
| 4 | `lr mcp install/uninstall/status/test` コマンド | 1-2h |
| 5 | テスト（MCP + Windows paths） | 2-3h |
| 6 | pyproject.toml + SKILL.md 更新 | 0.5h |
| 7 | Windows CI (GitHub Actions) | 1h |

**合計見積もり**: 8-13h

Phase 1 と Phase 2-3 は並行可能。Phase 4 は Phase 2-3 完了後。
