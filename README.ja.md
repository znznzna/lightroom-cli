[English](README.md)

# Lightroom CLI

[![Test](https://github.com/znznzna/lightroom-cli/actions/workflows/test.yml/badge.svg)](https://github.com/znznzna/lightroom-cli/actions/workflows/test.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Adobe Lightroom Classic をコマンドラインから完全操作 — 107コマンド。**

現像パラメータ調整、マスキング、トーンカーブ、カタログ管理、セレクション操作など。バッチ処理やスクリプト自動化に最適です。

## Architecture

```
+---------------------+     TCP Socket (JSON-RPC)     +--------------+
|  Lightroom Classic  |<----------------------------->|  Python SDK  |
|  (Lua Plugin)       |   Dual socket: send/receive   |              |
+---------------------+                               +------+-------+
                                                              |
                                              +---------------+---------------+
                                              |               |               |
                                       +------+-------+ +-----+------+ +------+------+
                                       |   CLI (lr)   | | MCP Server | | Python SDK  |
                                       |   Click app  | | (lr-mcp)   | |   Direct    |
                                       +--------------+ +------------+ +-------------+
```

Lua プラグインが Lightroom Classic 内で動作し、デュアル TCP ソケットで Python SDK と通信します。3つのインターフェースが利用可能です: `lr` CLI、Claude Desktop/Cowork 向け MCP Server、Python SDK の直接利用。

## Quick Start

### Prerequisites

- **Python 3.10+**
- **Adobe Lightroom Classic** (デスクトップ版)
- macOS / Windows (Windows はサポートされていますが実機テストは未実施 — [問題があれば報告してください](https://github.com/znznzna/lightroom-cli/issues))

### Installation

```bash
pip install lightroom-cli
```

次に Lightroom プラグインをインストールし、Lightroom Classic を再起動してください：

```bash
lr plugin install
```

プラグインは **File > Plug-in Manager** に「Lightroom CLI Bridge」として表示されます。

### Upgrading

```bash
pip install --upgrade lightroom-cli
lr plugin install
```

アップグレード後、Lightroom Classic を再起動して更新されたプラグインを読み込んでください。

### 利用方法を選択

#### Option A: Claude Code（SKILL ベース）

**Claude Code** ユーザー向け — Claude Code Plugin をインストールすると、エージェントが SKILL ファイルを通じて全107コマンドを発見・利用できます：

```bash
/plugin marketplace add znznzna/lightroom-cli
/plugin install lightroom-cli@lightroom-cli
```

エージェントは `SKILL.md` を読んで利用可能なコマンド、パラメータ、ワークフローを把握します。手動でコマンドを打つ必要はありません。

#### Option B: Claude Desktop / Cowork（MCP Server）

**Claude Desktop** または **Cowork** ユーザー向け — MCP Server を登録してください：

```bash
lr mcp install
```

Claude Desktop / Cowork を再起動してください。全107コマンドが `lr_` プレフィックス付きの MCP ツールとして利用可能です（例: `lr_system_ping`, `lr_catalog_list`）。

MCP のステータス確認：

```bash
lr mcp status
lr mcp test      # Lightroom への接続テスト
```

#### Option C: 直接 CLI / スクリプト

`lr` コマンドを直接使ってシェルスクリプトや自動化に活用できます：

```bash
lr system ping
lr catalog list --limit 10
lr develop set Exposure 1.5
```

### 接続確認

1. Lightroom Classic を起動
2. **File > Plugin Extras > Start CLI Bridge** を選択
3. 以下のコマンドを実行：

```bash
lr system ping
# → pong

lr system status
```

> **注意:** ブリッジは自動起動しません。Lightroom を起動するたびに「Start CLI Bridge」をメニューから選択する必要があります。

## Usage Examples

```bash
# 選択中の写真を取得
lr catalog get-selected

# 現像パラメータを設定
lr develop set Exposure 1.5 Contrast 25 Clarity 30

# AutoTone 適用
lr develop auto-tone

# トーンカーブに S カーブを適用
lr develop curve s-curve

# マスクを作成してブラシを追加
lr develop mask create
lr develop mask add brush

# プリセット適用
lr develop preset "Vivid Landscape"

# レーティングとフラグ操作
lr selection set-rating 5
lr selection flag

# カタログ検索
lr catalog search "landscape" --limit 20

# JSON 出力
lr -o json develop get-settings

# テーブル形式で一覧
lr -o table catalog list --limit 10
```

## Command Groups

| Group | Commands | Description |
|-------|----------|-------------|
| [`lr system`](#lr-system) | 4 | 接続管理・ステータス確認 |
| [`lr catalog`](#lr-catalog) | 27 | カタログ操作・写真検索・メタデータ |
| [`lr develop`](#lr-develop) | 55 | 現像設定・マスク・カーブ・フィルタ |
| [`lr preview`](#lr-preview) | 4 | プレビュー生成・情報取得 |
| [`lr selection`](#lr-selection) | 17 | 選択操作・フラグ・レーティング・ラベル |
| [`lr plugin`](#lr-plugin) | 3 | プラグインのインストール・管理 |
| [`lr mcp`](#lr-mcp) | 4 | MCP Server の管理 |

**全 107 コマンドの詳細は [CLI Reference](docs/CLI_REFERENCE.md) を参照してください。**

### lr system

```bash
lr system ping                # 接続テスト
lr system status              # ブリッジステータス
lr system reconnect           # 強制再接続
lr system check-connection    # 接続詳細チェック
```

### lr catalog

```bash
lr catalog get-selected               # 選択中の写真を取得
lr catalog list --limit 10            # 写真一覧
lr catalog search "keyword"           # 検索
lr catalog get-info <photo_id>        # 詳細メタデータ
lr catalog set-rating <id> 5          # レーティング設定
lr catalog add-keywords <id> kw1 kw2  # キーワード追加
lr catalog set-title <id> "Title"     # タイトル設定
lr catalog collections                # コレクション一覧
lr catalog create-collection "name"   # コレクション作成
lr catalog keywords                   # キーワード一覧
lr catalog set-view-filter <json>     # ビューフィルタ設定
lr catalog rotate-left                # 左回転
lr catalog create-virtual-copy        # 仮想コピー作成
```

### lr develop

```bash
# 基本操作
lr develop get-settings               # 全現像設定を取得
lr develop set Exposure 1.5           # パラメータ設定
lr develop get Exposure               # 単一パラメータ取得
lr develop auto-tone                  # AutoTone
lr develop auto-wb                    # Auto White Balance
lr develop reset                      # リセット
lr develop apply '{"Exposure": 1.0}'  # JSON で一括適用

# トーンカーブ
lr develop curve get                  # カーブ取得
lr develop curve set '[[0,0],[128,140],[255,255]]'
lr develop curve s-curve              # S カーブプリセット
lr develop curve linear               # リニアリセット
lr develop curve add-point 128 140    # ポイント追加

# マスキング
lr develop mask list                  # 全マスク一覧
lr develop mask create                # 新規マスク作成
lr develop mask add brush             # ブラシ追加
lr develop mask intersect luminance   # インターセクト
lr develop mask subtract color        # サブトラクト
lr develop mask invert mask-1         # マスク反転

# フィルタ
lr develop filter graduated           # 段階フィルタ
lr develop filter radial              # 円形フィルタ
lr develop filter brush               # ブラシフィルタ
lr develop filter ai-select           # AI 選択

# ローカル補正
lr develop local set Exposure 0.5     # ローカルパラメータ設定
lr develop local get Exposure         # ローカルパラメータ取得

# ツール・プリセット・スナップショット
lr develop tool crop                  # ツール選択
lr develop preset "Preset Name"       # プリセット適用
lr develop snapshot "Snapshot Name"   # スナップショット作成
lr develop copy-settings              # 設定コピー
lr develop paste-settings             # 設定ペースト
```

### lr preview

```bash
lr preview generate-current           # 選択写真のプレビュー生成
lr preview generate --size 2048       # サイズ指定
lr preview generate-batch             # バッチ生成
lr preview info                       # プレビュー情報
```

### lr selection

```bash
lr selection flag                     # Pick フラグ
lr selection reject                   # Reject フラグ
lr selection unflag                   # フラグ解除
lr selection get-flag                 # フラグ状態取得
lr selection set-rating 5             # レーティング設定 (0-5)
lr selection get-rating               # レーティング取得
lr selection color-label red          # カラーラベル設定
lr selection get-color-label          # カラーラベル取得
lr selection toggle-label red         # ラベルトグル
lr selection next                     # 次の写真
lr selection previous                 # 前の写真
lr selection select-all               # 全選択
lr selection select-none              # 全解除
lr selection select-inverse           # 選択反転
lr selection extend --direction right # 選択範囲拡張
```

### lr mcp

```bash
lr mcp install                # MCP Server を Claude Desktop の設定に登録
lr mcp install --force        # 既存エントリを上書き
lr mcp uninstall              # MCP Server エントリを削除
lr mcp status                 # インストール状況を表示
lr mcp test                   # MCP 経由で接続テスト
```

## Global Options

```bash
lr --output json ...    # JSON 出力 (-o json)
lr --output table ...   # テーブル出力 (-o table)
lr --verbose ...        # デバッグログ (-v)
lr --timeout 60 ...     # タイムアウト秒数 (-t 60)
lr --version            # バージョン表示
```

## Configuration

| 環境変数 | 説明 |
|---------|------|
| `LR_PORT_FILE` | ソケット通信に使用するポートファイルのパス |
| `LR_PLUGIN_DIR` | Lightroom プラグインディレクトリのパス |

## Features

- **自動再接続**: Lightroom との接続が切れても自動リトライ（指数バックオフ）
- **ハートビート**: 30 秒間隔の接続監視
- **シャットダウン検知**: Lightroom 終了時のグレースフルハンドリング
- **3 出力形式**: `text` / `json` / `table`
- **タブ補完**: 現像パラメータ名の補完サポート
- **コマンド別タイムアウト**: プレビュー生成など長時間処理は自動延長
- **MCP Server**: Claude Desktop および Cowork とのネイティブ連携

## Development

### コントリビューター向け

> **一般ユーザーはこのセクションをスキップしてください。** `pip install lightroom-cli` だけで利用できます。

```bash
git clone https://github.com/znznzna/lightroom-cli.git
cd lightroom-cli
pip install -e ".[dev]"
lr plugin install --dev
```

```bash
# テスト実行
python -m pytest tests/ -v

# カバレッジ付き
python -m pytest tests/ -v --cov=lightroom_sdk --cov=cli --cov=mcp_server

# 単一テストファイル
python -m pytest tests/integration/test_cli_develop.py -v
```

## Project Structure

```
lightroom-cli/
├── cli/                      # Click CLI アプリケーション
│   ├── main.py               # エントリポイント (lr コマンド)
│   ├── output.py             # OutputFormatter (json/text/table)
│   ├── helpers.py            # コマンド実行ヘルパー
│   └── commands/             # コマンドグループ
│       ├── system.py         # lr system
│       ├── catalog.py        # lr catalog
│       ├── develop.py        # lr develop (+ curve/mask/local/filter/debug/color)
│       ├── preview.py        # lr preview
│       ├── selection.py      # lr selection
│       ├── plugin.py         # lr plugin
│       └── mcp.py            # lr mcp
├── mcp_server/               # MCP Server (FastMCP)
│   ├── server.py             # エントリポイント (lr-mcp コマンド)
│   ├── tool_registry.py      # スキーマ駆動ツール登録
│   ├── connection.py         # ブリッジ接続管理
│   └── instructions.py       # MCP Server 命令文
├── lightroom_sdk/            # Python SDK
│   ├── client.py             # LightroomClient
│   ├── socket_bridge.py      # デュアル TCP ソケット
│   ├── resilient_bridge.py   # 自動再接続 + ハートビート
│   ├── schema.py             # コマンドスキーマ（Single Source of Truth）
│   ├── validation.py         # 入力バリデーション + サニタイズ
│   ├── retry.py              # コマンド別タイムアウト
│   ├── protocol.py           # JSON-RPC プロトコル
│   ├── paths.py              # パス解決ユーティリティ
│   └── plugin/               # Lua プラグイン (バンドル)
│       ├── PluginInit.lua    # コマンドルーター (107 commands)
│       ├── DevelopModule.lua # 現像操作
│       └── CatalogModule.lua # カタログ操作
├── tests/                    # pytest テストスイート (750+ tests)
```

## Requirements

- Python >= 3.10
- Adobe Lightroom Classic
- macOS / Windows

> **Windows ユーザーへ:** Windows サポートは v1.1.0 で追加されましたが、実機でのテストは行われていません。問題が発生した場合は [Issue を作成](https://github.com/znznzna/lightroom-cli/issues)してください。

### Python Dependencies

- [click](https://click.palletsprojects.com/) >= 8.1 — CLI フレームワーク
- [rich](https://rich.readthedocs.io/) >= 13.0 — テーブル出力
- [pydantic](https://docs.pydantic.dev/) >= 2.0 — データバリデーション
- [platformdirs](https://platformdirs.readthedocs.io/) >= 3.0 — プラットフォーム固有のディレクトリパス
- [fastmcp](https://github.com/jlowin/fastmcp) >= 3.0 — MCP Server フレームワーク

## License

[MIT](LICENSE)
