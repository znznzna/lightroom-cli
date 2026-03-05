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

### Agent-First CLI 最適化 (2026-03-05)

設計書: `docs/plans/2026-03-05-agent-first-hardening-design.md`
実装計画: `docs/plans/2026-03-05-agent-first-hardening.md`

- [x] Phase 1-9: TTY検出, --fields, 構造化エラー, execute_command, lr schema, バリデーション, --dry-run, --json, 既存コマンド移行, SKILLS.md, テスト
- [x] P1: min/max range validation, string sanitization, cli_constraints (supports_dry_run/requires_confirm/risk_level)
- [x] P2: risk_level in dry-run, output sanitization, schema_hash, system status metadata
- [x] 3モデルレビュー (Opus 42/Sonnet 38/Codex) → 討論 → MUST FIX 2件 + SHOULD FIX 5件 修正
  - develop.resetMasking requires_confirm=True (risk_level不整合修正)
  - JSON truncation に _truncated フラグ追加
  - JSON_OBJECT/JSON_ARRAY 再帰サニタイズ
  - SKILLS.md: mutating応答例, exit code リカバリ, JSON構造例追加
- [x] SKILLS.md restructure: schema-first discovery (559→226行, 5,500→2,100トークン, 62%削減)
- [x] 3モデル最終確認: Opus 46/50, Sonnet 46/50, Codex 合格 — 全会一致 Ship it

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

## Next Sprint: リリース & 配布

リリースGO判断済み (2026-03-05)。

### Sprint 1: ruff + Plugin化 + PyPI

- [ ] **ruff 導入 + CI** — 設定なしですぐ動く。既存コード修正は数件程度
- [ ] **Claude Code Plugin化** — `.claude-plugin/plugin.json` + `skills/lightroom-cli/SKILL.md`
  - `/plugin install motokiendo/lightroom-cli` でインストール可能に
  - SKILLS.md → SKILL.md リネーム + YAMLフロントマター追加
- [ ] **PyPI 公開** — `pip install lightroom-cli`

### Sprint 2: MCP Server + Homebrew

- [ ] **MCP Server** (`lightroom_sdk/mcp_server.py`) — 既存SDKのラッパー
  - Claude Desktop / Cowork 対応 (Research Preview, 2026年1月〜)
  - `lr-mcp` エントリポイント追加 (pyproject.toml)
  - `.mcp.json` で Claude Desktop から自動認識
- [ ] **Homebrew Tap** リポ作成 + Formula 公開

### Backlog (保留)

- [ ] NDJSON streaming — Lua側もストリーミング化が必要でコスト重い。`--limit/--offset` ページネーションで代替可能
- [ ] `lr invoke` — 汎用エントリポイント。107コマンドCLI化済みのため緊急性ゼロ
- [ ] 監査ログ — 3つの中で最も実用的だが `--verbose` で当面代替可能
- [ ] mypy — 型アノテーション不足で大量エラー出る。段階的導入が現実的
- [ ] カバレッジレポート

### 開発体験

- [ ] Plugin Manager「Add」でソース直接読み込み失敗の原因調査
- [ ] `lr plugin install --dev` の改善

### Windows版 (別リポ)

- [ ] 別リポで Windows 対応を検討
- [ ] `paths.py` の Windows 分岐は準備済み
- [ ] `PlatformPaths.lua` — Lightroom sandbox 制約で `os.getenv` 不可 → 別アプローチ必要
