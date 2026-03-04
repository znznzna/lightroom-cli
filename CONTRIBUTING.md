# Contributing

## Setup

```bash
git clone https://github.com/znznzna/lightroom-cli.git
cd lightroom-cli
pip install -e ".[dev]"
```

## Running Tests

```bash
# 全テスト
python -m pytest tests/ -v

# 特定テストファイル
python -m pytest tests/integration/test_cli_develop.py -v

# カバレッジ付き
python -m pytest tests/ -v --cov=lightroom_sdk --cov=cli
```

## Coding Conventions

- **Python 3.10+** — type hints, `match` 文OK
- **asyncio + async/await** — SDK 通信は全て非同期
- CLI コマンドは `run_async()` で1回だけイベントループを作成
- `bridge.disconnect()` は必ず `finally` で呼ぶ
- Lua コマンド名はプラグイン側の `router:register()` 名と完全一致させる

## Adding a New Command

1. **Lua 側**: `lightroom-plugin/` 内の該当モジュールにハンドラを追加し、`PluginInit.lua` で `router:register()` する
2. **CLI 側**: `cli/commands/` 内の該当ファイルにコマンドを追加
3. **テスト**: `tests/integration/` にテストを追加（`@patch("cli.commands.<module>.get_bridge")` + `AsyncMock` パターン）
4. テストが全件パスすることを確認

## PR Guidelines

- テストを書く（TDD 推奨）
- `python -m pytest` が全件パスすること
- コミットメッセージは `<type>: <what> (<why>)` 形式
  - type: `feat` / `fix` / `refactor` / `test` / `docs` / `ci`

## Architecture Overview

```
[Lightroom Classic] ← Lua Plugin (TCP) → [Python SDK] → [CLI (lr)]
```

- **Lua Plugin**: Lightroom SDK API を呼び出し、結果を JSON-RPC で返す
- **Python SDK**: デュアルソケット接続、自動再接続、ハートビート
- **CLI**: Click ベース、3 出力形式対応
