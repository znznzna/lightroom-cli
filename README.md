# Lightroom CLI

Adobe Lightroom Classicをコマンドラインから操作するツール。

## アーキテクチャ

```
[Lightroom Classic] ← Lua Plugin (TCP Socket) → [Python SDK] → [CLI (lr)]
```

Luaプラグインがデュアルソケット（sender/receiver）でPython SDKと通信し、CLIがコマンドをJSON RPCで送受信します。

## クイックスタート

```bash
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
lr develop auto-tone                       # AutoTone適用
lr catalog list --limit 10                 # カタログ写真を一覧表示
```

## グローバルオプション

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--output` | `-o` | `text` | 出力形式 (`json` / `text` / `table`) |
| `--verbose` | `-v` | `false` | デバッグログを有効化 |
| `--timeout` | `-t` | `30.0` | デフォルトタイムアウト（秒） |

```bash
# JSON出力
lr -o json catalog get-selected

# テーブル形式
lr -o table develop get-settings
```

## コマンドグループ

| Group | Description | 主なコマンド |
|-------|-------------|-------------|
| `lr system` | 接続管理 | `ping`, `status`, `reconnect`, `check-connection` |
| `lr catalog` | 写真カタログ操作 | `get-selected`, `list`, `search`, `get-info`, `set-rating`, `add-keywords` |
| `lr develop` | 現像設定 | `get-settings`, `set`, `auto-tone`, `reset` |
| `lr preview` | プレビュー生成 | `generate-current`, `generate`, `generate-batch` |

詳細は [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) を参照してください。

## ディレクトリ構造

```
lightroom-cli/
├── cli/                  # Click CLIアプリケーション
│   ├── main.py           # エントリポイント (lr コマンド)
│   ├── output.py         # OutputFormatter (json/text/table)
│   ├── completions.py    # タブ補完
│   └── commands/         # コマンドグループ
├── lightroom_sdk/        # Python SDK (ソケット通信)
│   ├── client.py         # LightroomClient
│   ├── socket_bridge.py  # デュアルTCPソケット
│   ├── resilient_bridge.py # 自動再接続ラッパー
│   └── retry.py          # コマンド別タイムアウト
├── lightroom-plugin/     # Lua プラグイン (Lightroom側)
├── scripts/              # インストールスクリプト
├── tests/                # pytest テストスイート
└── docs/                 # ドキュメント
```

> `lightroom-plugin/` はリポジトリ内の名称です。`scripts/install-plugin.sh` でインストールすると、Lightroomが認識する `.lrdevplugin` サフィックス付きのシンボリックリンクが作成されます。

## 開発

```bash
# 開発用インストール
pip install -e ".[dev]"

# テスト実行
python -m pytest tests/ -v

# カバレッジ付き
python -m pytest tests/ -v --cov=lightroom_sdk --cov=cli
```

## ライセンス

MIT
