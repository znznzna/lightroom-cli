# Contributing

## セットアップ

```bash
git clone <repo-url> && cd lightroom-cli
pip install -e ".[dev]"
```

## テスト実行

```bash
# 全テスト
python -m pytest tests/ -v

# 特定テストファイル
python -m pytest tests/test_retry.py -v

# カバレッジ付き
python -m pytest tests/ -v --cov=lightroom_sdk --cov=cli
```

## コーディング規約

- Python 3.10+
- asyncio + async/await パターン
- CLI コマンドは `run_async()` で1回だけイベントループを作成
- `bridge.disconnect()` は必ず `finally` で呼ぶ
- Lua コマンド名はプラグイン側の登録名と完全一致させる

## PRガイドライン

- テストを書く（TDD推奨）
- `python -m pytest` が全件パスすること
- コミットメッセージは `<type>: <what> (<why>)` 形式
  - type: `feat` / `fix` / `refactor` / `test` / `docs` / `ci`
