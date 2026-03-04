[English](README.md)

# Lightroom CLI

[![Test](https://github.com/znznzna/lightroom-cli/actions/workflows/test.yml/badge.svg)](https://github.com/znznzna/lightroom-cli/actions/workflows/test.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Adobe Lightroom Classic をコマンドラインから完全操作するCLIツール。**

現像パラメータ調整、マスキング、トーンカーブ、カタログ管理、セレクション操作など **107コマンド** を提供します。バッチ処理やスクリプト自動化に最適です。

## Architecture

```
┌─────────────────────┐     TCP Socket (JSON-RPC)     ┌──────────────┐
│  Lightroom Classic   │◄────────────────────────────►│  Python SDK  │
│  (Lua Plugin)        │   Dual socket: send/receive   │              │
└─────────────────────┘                                └──────┬───────┘
                                                              │
                                                       ┌──────┴───────┐
                                                       │   CLI (lr)   │
                                                       │   Click app  │
                                                       └──────────────┘
```

Lua プラグインが Lightroom Classic 内で動作し、デュアル TCP ソケット（送信用/受信用）で Python SDK と JSON-RPC 通信します。CLI は `lr` コマンドとして動作し、SDK 経由で Lightroom を操作します。

## Quick Start

### Prerequisites

- **Python 3.10+**
- **Adobe Lightroom Classic** (デスクトップ版)
- macOS (Windows は未テスト)

### Installation

```bash
git clone https://github.com/znznzna/lightroom-cli.git
cd lightroom-cli
./scripts/install.sh
```

`install.sh` は以下を自動で実行します:
1. Python パッケージをインストール (`pip install -e .`)
2. Lua プラグインを Lightroom のプラグインディレクトリにシンボリックリンク

### 接続確認

```bash
# Lightroom Classic を起動した状態で
lr system ping
# → pong

lr system status
```

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

## Global Options

```bash
lr --output json ...    # JSON 出力 (-o json)
lr --output table ...   # テーブル出力 (-o table)
lr --verbose ...        # デバッグログ (-v)
lr --timeout 60 ...     # タイムアウト秒数 (-t 60)
lr --version            # バージョン表示
```

## Features

- **自動再接続**: Lightroom との接続が切れても自動リトライ（指数バックオフ）
- **ハートビート**: 30 秒間隔の接続監視
- **シャットダウン検知**: Lightroom 終了時のグレースフルハンドリング
- **3 出力形式**: `text` / `json` / `table`
- **タブ補完**: 現像パラメータ名の補完サポート
- **コマンド別タイムアウト**: プレビュー生成など長時間処理は自動延長

## Development

```bash
# 開発用インストール
pip install -e ".[dev]"

# テスト実行
python -m pytest tests/ -v

# カバレッジ付き
python -m pytest tests/ -v --cov=lightroom_sdk --cov=cli

# 単一テストファイル
python -m pytest tests/integration/test_cli_develop.py -v
```

## Project Structure

```
lightroom-cli/
├── cli/                      # Click CLI アプリケーション
│   ├── main.py               # エントリポイント (lr コマンド)
│   ├── output.py             # OutputFormatter (json/text/table)
│   ├── helpers.py            # bridge_command デコレータ
│   ├── completions.py        # タブ補完
│   └── commands/             # コマンドグループ
│       ├── system.py         # lr system
│       ├── catalog.py        # lr catalog
│       ├── develop.py        # lr develop (+ curve/mask/local/filter/debug/color)
│       ├── preview.py        # lr preview
│       └── selection.py      # lr selection
├── lightroom_sdk/            # Python SDK
│   ├── client.py             # LightroomClient
│   ├── socket_bridge.py      # デュアル TCP ソケット
│   ├── resilient_bridge.py   # 自動再接続 + ハートビート
│   ├── retry.py              # コマンド別タイムアウト
│   └── protocol.py           # JSON-RPC プロトコル
├── lightroom-plugin/         # Lua プラグイン
│   ├── PluginInit.lua        # コマンドルーター (107 commands)
│   ├── DevelopModule.lua     # 現像操作
│   ├── CatalogModule.lua     # カタログ操作
│   ├── SelectionModule.lua   # 選択操作
│   ├── PreviewModule.lua     # プレビュー操作
│   └── SocketServer.lua      # TCP サーバー
├── scripts/                  # インストールスクリプト
├── tests/                    # pytest テストスイート (165 tests)
└── docs/                     # ドキュメント
```

## Requirements

- Python >= 3.10
- Adobe Lightroom Classic
- macOS (Windows 未テスト)

### Python Dependencies

- [click](https://click.palletsprojects.com/) >= 8.1 — CLI フレームワーク
- [rich](https://rich.readthedocs.io/) >= 13.0 — テーブル出力
- [pydantic](https://docs.pydantic.dev/) >= 2.0 — データバリデーション

## License

[MIT](LICENSE)
