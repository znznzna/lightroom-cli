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
- [x] E2E テストコード修正 (conftest の auto-skip 改善 + ScopeMismatch 修正)
- [x] SKILLS.md をスキルとして実際に使ってみる → 検証完了、65+コマンド追加修正済み
- [x] 145 E2Eテスト実装完了 (10 phase files)

### ソケット安定化 (2026-03-05)

- [x] 固定ポート化 (port=0 → Config.lua: 54322/54323)
- [x] 非同期リスタートパターン導入 (onClosed内のreconnect全廃)
- [x] Lightroomハング問題修正 (別ソケットコールバックからの操作禁止)
- [x] startSocketServer多重起動ガード
- [x] Python側リトライ強化 (retry_attempts=3, retry_delay=0.5)
- [x] シャットダウン高速化 (PluginShutdown/AppShutdown フラグセットのみ)
- [x] 5連続ping + 全systemコマンド動作確認済み

### AI Mask API 実装 (2026-03-05)

- [x] `lightroom_sdk/presets.py` — 5プリセット定義 (darken-sky, brighten-subject, blur-background, warm-skin, enhance-landscape)
- [x] SDK タイムアウト追加 (createAIMaskWithAdjustments: 60s, batchAIMask: 300s)
- [x] `LightroomClient.create_ai_mask()` / `batch_ai_mask()` メソッド
- [x] `cli/commands/ai_mask.py` — `lr develop ai` グループ (subject/sky/background/objects/people/landscape)
- [x] `--part` オプション (people: eyes/hair/skin等, landscape: mountain/water等)
- [x] `--adjust` JSON / `--adjust-preset` プリセット適用
- [x] `lr develop ai presets` / `list` / `reset` / `batch` コマンド
- [x] batch: `--photos`, `--all-selected`, `--dry-run`, `--continue-on-error`
- [x] Lua `createAIMaskWithAdjustments` (hang guard + adjustment support)
- [x] Lua `batchAIMask` (multi-photo, continueOnError)
- [x] 既存 mask/filter コマンド13個削除、deprecated警告追加
- [x] E2E テスト11件 ALL PASS (実機検証済み)
- [x] ユニット/統合テスト 215件 ALL PASS

### 発見・修正した問題

- `.lrdevplugin` は Modules ディレクトリの自動検出で認識されない → `.lrplugin` に変更
- Lightroom Lua sandbox に `os.getenv`, `package` が存在しない → ハードコード化
- シンリンクは Modules ディレクトリで認識されない → コピーインストール必須
- Plugin Manager の「Add」でソースフォルダ直接読み込みに失敗する → 要調査
- CLI コマンドが `connect()` なしで `send_command()` を呼んでいた → 修正済み
- LrSocket `reconnect()` を別ソケットのコールバックから呼ぶと Lightroom がハング → 非同期リスタートに変更
- LrSocket mode="send" はクライアント切断を検知しない → 仕様として受容、フルリスタートで対応
- シャットダウン時 `LrTasks.sleep()` が「応答していません」ダイアログを引き起こす → フラグセットのみに簡素化

---

## In Progress

### Agent-First CLI 最適化 (2026-03-05 ~)

設計書: `docs/plans/2026-03-05-agent-first-cli-design.md`
実装計画: `docs/plans/2026-03-05-agent-first-cli-implementation.md` (22タスク / 9 Phase)

- [x] Phase 1: TTY検出 + 環境変数 (Task 1-3) — middleware, main.py統合
- [ ] Phase 2: --fields レスポンスフィルタ + 構造化エラー + execute_command (Task 4-6)
- [ ] Phase 3: スキーマ定義 + lr schema コマンド (Task 7-9)
- [ ] Phase 4: 入力バリデーション (Task 10-11)
- [ ] Phase 5: --dry-run 全mutating (Task 12-13)
- [ ] Phase 6: --json 入力統一 (Task 14-15)
- [ ] Phase 7: 既存コマンド移行 (Task 16-20)
- [ ] Phase 8: SKILLS.md 更新 (Task 21)
- [ ] Phase 9: 全テスト + バージョンバンプ (Task 22)

---

## Backlog

### CLI 最適化

- [x] コードレビュー (Codex CLI) — P1-P3 修正済み
- [ ] CLI パフォーマンス改善 (起動時間等) — Agent-First最適化とは別

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

- [x] コードレビュー (Codex CLI) — AI mask 実装レビュー完了
- [ ] カバレッジレポート
- [ ] ruff / mypy 導入
