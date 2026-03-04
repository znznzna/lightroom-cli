# Lightroom CLI — Task Board & Roadmap

## Completed

### v2.0.0 配布準備 (2026-03-04 ~ 03-05)

- [x] SDK full coverage (107 commands, 189 tests)
- [x] Public GitHub repo 作成 + README/LICENSE/CHANGELOG 整備
- [x] CI (GitHub Actions: Python 3.10/3.11/3.12)
- [x] `lightroom_sdk/paths.py` — OS横断パス抽象化
- [x] `PlatformPaths.lua` — Lua側パス抽象化 (Lightroom sandbox対応済み)
- [x] `lr plugin install/uninstall/status` コマンド
- [x] pyproject.toml 整備 (platformdirs, classifiers, URLs, pytest統合)
- [x] .gitignore クリーンアップ (docs/plans/ 除外)
- [x] Homebrew Formula テンプレート (`homebrew/lightroom-cli.rb`)
- [x] README 英語/日本語 (README.md + README.ja.md)
- [x] SKILLS.md (Claude Code用スキルファイル)
- [x] E2E テスト基盤 (conftest, auto-skip, plugin workflow tests, Lightroom live tests)
- [x] プラグイン名変更: Lightroom CLI Bridge (`com.znznzna.lightroom.cli-bridge`)
- [x] Lightroom 実機接続成功 (ping/status OK)
- [x] `bridge.connect()` 抜け修正 (全CLIコマンド)

### 発見・修正した問題

- `.lrdevplugin` は Modules ディレクトリの自動検出で認識されない → `.lrplugin` に変更
- Lightroom Lua sandbox に `os.getenv`, `package` が存在しない → ハードコード化
- シンリンクは Modules ディレクトリで認識されない → コピーインストール必須
- Plugin Manager の「Add」でソースフォルダ直接読み込みに失敗する → 要調査
- CLI コマンドが `connect()` なしで `send_command()` を呼んでいた → 修正済み

---

## In Progress

### E2E テスト実行
- [x] `_lr-cli-test` コレクションの写真で全コマンド網羅テスト → 145 E2Eテスト実装完了 (10 phase files)
- [x] E2E テストコード修正 (conftest の lr_bridge fixture がポートファイル存在時にスキップされない問題)
- [x] SKILLS.md をスキルとして実際に使ってみる → 検証完了、65+コマンド追加修正済み

---

## Backlog

### 配布

- [ ] PyPI 公開 (リリースGO判断後)
- [ ] Homebrew Tap リポ作成 + Formula 公開 (リリースGO判断後)
- [ ] SKILLS.md を Claude Code スキルとして配布する導線整備
  - インストール手順に `~/.claude/skills/` への配置を含める
  - `lr skill install` コマンドの検討

### 開発体験

- [ ] Plugin Manager「Add」でソース直接読み込み失敗の原因調査
  - `.lrdevplugin` 拡張子付きシンリンク or リネームで解決できるか
- [ ] `lr plugin install --dev` の改善 (Plugin Manager 手動追加の案内表示)

### Windows版 (別リポ)

- [ ] 別リポで Windows 対応を検討
- [ ] `paths.py` の Windows 分岐は準備済み
- [ ] `PlatformPaths.lua` は Lightroom sandbox 制約により `os.getenv` 不可 → 別アプローチ必要

### Claude Cowork 対応

- [ ] Claude Cowork (マルチエージェント) での利用を想定したインターフェース設計
- [ ] MCP Server としての公開検討
- [ ] エージェント間での写真編集ワークフロー共有

### 品質

- [ ] コードレビュー (Codex CLI)
- [ ] カバレッジレポート
- [ ] ruff / mypy 導入
