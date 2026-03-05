# Agent Feedback Fixes Design

生成日: 2026-03-05
ステータス: Codexレビュー済み・修正済み

## 背景

Agent-First CLI 最適化（22タスク完了、450テスト全パス）の後、3つのAIモデル（Opus、Codex、Sonnet）に「初見のAIエージェントとして使いやすいか」を評価させた。17項目のフィードバックが得られた。

## フィードバック一覧

| # | 重要度 | 概要 | 一致モデル数 |
|---|--------|------|-------------|
| 1 | Critical | 生トレースバック露出（`_parse_pairs` float変換） | 3 |
| 2 | Critical | `--json`/`--json-stdin` 未実装（デコレータ未適用） | 3 |
| 3 | Critical | 接続ログ stdout 混入 | 3 |
| 4 | Critical | exit code 不一致（3=connection, 4=timeout が実際は全て1） | 3 |
| 5 | Important | `--fields` が動作しない | 2-3 |
| 6 | Important | schema response_fields 常に空配列 | 2-3 |
| 7 | Important | schema description 空文字のパラメータ多数 | 2-3 |
| 8 | Important | `lr schema foobar` が exit code 0 | 2-3 |
| 9 | Important | SKILLS.md と実装の乖離 | 2-3 |
| 10 | Structural | catalog/selection の責務重複 | 複数 |
| 11 | Structural | develop reset-* の統合提案 | 複数 |
| 12 | Structural | schema に develop.ai.* が含まれない | 複数 |
| 13 | Structural | suggestions フィールドが実際のエラーレスポンスに未出現 | 複数 |
| 14 | Structural | check-connection の出力が非構造化 | 複数 |
| 15 | Documentation | Develop パラメータ名の一覧がない | 複数 |
| 16 | Documentation | PHOTO_ID の取得フローが不明瞭 | 複数 |
| 17 | Documentation | catalog/selection 使い分けガイド | 複数 |

---

## アプローチ比較

### A: 全部一気に修正

| 項目 | 評価 |
|------|------|
| 修正範囲 | 17項目すべてを1ブランチで修正 |
| 所要タスク数 | ~12タスク |
| メリット | 1回のレビューで完了、整合性を一括保証 |
| デメリット | PR が巨大（推定 800+ 行変更）、レビュー困難、bisect 不能 |
| リスク | 変更の相互作用でデグレ発見が遅れる |
| 推奨度 | **非推奨** |

### B: 重要度別 Phase 分割（Critical → Important → Structural → Docs）

| 項目 | 評価 |
|------|------|
| 修正範囲 | 4 Phase に分割、各 Phase でコミット＋テスト＋レビュー |
| 所要タスク数 | ~16タスク（4 Phase x 4タスク平均） |
| メリット | 重要度順で段階的に品質向上、各 Phase で動作確認可能 |
| デメリット | Phase 間の依存関係あり（例: exit code 修正が Structural に波及） |
| リスク | Phase 2-3 で Phase 1 の修正を前提とする箇所が多い |
| 推奨度 | **良** |

### C: 機能クラスタ別 Phase 分割（推奨）

| 項目 | 評価 |
|------|------|
| 修正範囲 | 変更対象ファイルの関連性でクラスタリングし、4 Phase に分割 |
| 所要タスク数 | ~18タスク |
| メリット | 各 Phase が独立テスト可能、変更の影響範囲が明確、bisect 容易 |
| デメリット | タスク数がやや多い |
| リスク | 低（各 Phase の依存が最小化されている） |
| 推奨度 | **最推奨** |

**アプローチ C を推奨する理由:**

1. **ファイル衝突の最小化**: Critical #1 と #2 は両方 `cli/commands/develop.py` を変更するため、同じ Phase にまとめることでマージコンフリクトを回避
2. **テスト戦略の明確化**: 各 Phase で「何をテストすべきか」が自明
3. **Codex レビューの効率化**: 1 Phase あたり 100-200 行の変更に収まり、レビューが実質的に機能する
4. **段階的デプロイ**: Phase 1（エラーハンドリング）だけでもエージェント体験が大幅改善

---

## 推奨アプローチ C: 詳細設計

### Phase 1: エラーハンドリング正常化（#1, #3, #4, #8, #14）

**テーマ**: エージェントが構造化されたエラーを受け取れるようにする

#### Task 1: `_parse_pairs()` のトレースバック修正 (#1)

**現状**: `develop.py` L13 で `float(pairs[i + 1])` が `ValueError` を投げ、Python traceback が stdout に出力される。

**修正内容**:
- `_parse_pairs()` 内で `ValueError` をキャッチし、`click.BadParameter` に変換
- エラーメッセージに「期待される形式」と「実際の値」を含める

**影響ファイル**: `cli/commands/develop.py`
**テスト**: `tests/integration/test_cli_develop.py` に `lr develop set Exposure abc` のテスト追加

```python
# 修正案
def _parse_pairs(pairs: tuple) -> dict:
    if len(pairs) % 2 != 0:
        raise click.BadParameter("Parameters must be in 'param value' pairs")
    result = {}
    for i in range(0, len(pairs), 2):
        try:
            result[pairs[i]] = float(pairs[i + 1])
        except ValueError:
            raise click.BadParameter(
                f"Invalid numeric value '{pairs[i + 1]}' for parameter '{pairs[i]}'. "
                f"Expected a number (e.g., 0.5, -1.0, 100)"
            )
    return result
```

#### Task 2: 接続ログの stderr 分離確認 (#3)

**調査結果**: `logging.basicConfig()` はデフォルトで stderr に出力する。実機検証で `lr system ping 2>/dev/null` はJSON結果のみ、`2>&1 1>/dev/null` でログのみ出力されることを確認済み。**ログは既にstderrに正しく分離されている**。

ただし、エラー出力（`format_error`）が `click.echo(..., err=True)` で stderr に出るコマンドと、stdout に出るコマンドが混在している。

**修正内容**:
- 全エラー出力を `click.echo(..., err=True)` に統一（一部コマンドで `err=True` が欠落）
- 非 verbose 時のデフォルトログレベルを明示的に WARNING に設定（`cli/main.py`）

**影響ファイル**: `cli/main.py`, `cli/commands/system.py`
**テスト**: `tests/test_middleware.py` にログ出力先のテスト追加

#### Task 3: exit code 正常化 (#4)

**現状**: `execute_command()` は正しく `ctx.exit(3)` / `ctx.exit(4)` を呼んでいる。しかし `system.py` の `reconnect` と `check-connection` は `execute_command` を使わず独自実装しており、全て exit code 1。

**修正内容**:
- `system.py` の `reconnect` と `check-connection` を `execute_command` 経由に変更
- または、独自実装部分で `ConnectionError` → exit 3, `TimeoutError` → exit 4 を明示的にハンドリング
- `reconnect` は特殊な操作（disconnect → connect）なので `execute_command` 移行は不適切。代わりに `_handle_error(ctx, e, fmt)` ヘルパーを追加

**影響ファイル**: `cli/commands/system.py`, `cli/helpers.py`
**テスト**: `tests/integration/test_cli_system.py` で exit code 検証

```python
# helpers.py に追加
def handle_error(ctx, error: Exception, fmt: str = "text"):
    """共通エラーハンドリング（execute_command を使わないコマンド用）"""
    if isinstance(error, ConnectionError):
        click.echo(
            OutputFormatter.format_error(str(error), fmt, code="CONNECTION_ERROR"),
            err=True,
        )
        ctx.exit(3)
    elif isinstance(error, TimeoutError):
        click.echo(
            OutputFormatter.format_error(str(error), fmt, code="TIMEOUT_ERROR"),
            err=True,
        )
        ctx.exit(4)
    else:
        click.echo(
            OutputFormatter.format_error(str(error), fmt),
            err=True,
        )
        ctx.exit(1)
```

#### Task 4: `lr schema` の exit code 修正 (#8)

**現状**: `schema.py` でエラー時に `format_error()` を呼ぶが `return` するのみで `ctx.exit()` を呼んでいない。

**修正内容**:
- `schema_cmd` のエラーパスで `ctx.exit(1)` を追加

**影響ファイル**: `cli/schema.py`
**テスト**: `tests/integration/test_cli_schema.py` で exit code 検証

```python
# 修正案
if not schemas:
    click.echo(OutputFormatter.format_error(f"Unknown group: {path}", fmt), err=True)
    ctx.exit(1)
    return
```

#### Task 5: check-connection の出力構造化 (#14)

**現状**: `check-connection` がプレーンテキスト（"Lightroom connection: ok"）を返す。

**修正内容**:
- 出力を `OutputFormatter.format()` 経由に変更
- `{"status": "ok", "message": "..."}` または `{"status": "unavailable", "reason": "..."}` を返す

**影響ファイル**: `cli/commands/system.py`
**テスト**: `tests/integration/test_cli_system.py` で構造化出力検証

#### Task 6: Phase 1 テスト実行 + Codex レビュー

**テスト戦略**:
- 既存 450 テスト全パス確認
- 新規テスト: ~12 件（各 Task で 2-3 件）
- エッジケース: 空文字列、特殊文字、Unicode パラメータ名

---

### Phase 2: 入力パイプライン修正（#2, #5）

**テーマ**: `--json` と `--fields` を実際に動作させる

#### Task 7: `--json`/`--json-stdin` デコレータ適用 (#2)

**現状**: `json_input_options` デコレータが `cli/decorators.py` に存在するが、どのコマンドにも適用されていない。`execute_command` 内部に `json_str` チェックコードは存在する（L38-60）。

**修正内容**:
- `json_input_options` をコマンドに適用する方法を検討:
  - **案A**: 全 mutating コマンドに個別適用 → 多数のコマンドに手動追加が必要
  - **案B**: `execute_command` 内で `ctx.params.get("json_str")` を参照する現行方式を維持し、Click オプションの登録のみ追加 → **推奨**
- 具体的には、`execute_command` を呼ぶ全コマンドに `@json_input_options` を追加
- ただし、大量のコマンド（~55個）への個別追加は非現実的。代替策として:
  - `develop` グループの `invoke()` をオーバーライドして子コマンドに自動注入
  - または `execute_command` 呼び出し前に Click の `ctx.params` にデフォルト値を設定

**最終方針**: 全コマンドファイルの各コマンドに `@json_input_options` を追加する。`execute_command` 側のロジックは既に完成しているため、デコレータ適用のみで動作する。

**Codexレビュー指摘への対応**:
- `json_input_options` はClick の `**kwargs` を使うコマンド（`@click.pass_context` でctx経由）で動作する。`execute_command` は `ctx.params.get("json_str")` でアクセスするため、コールバック引数に `json_str` / `json_stdin` を追加する必要はない
- `json_stdin` は `parse_json_input` 内で stdin を読み取り、`json_str` と同じ経路で処理される
- **回帰テスト**: 全コマンドの `--help` が正常動作することを検証するパラメトリックテストを追加（55コマンド全網羅）

**影響ファイル**: `cli/commands/develop.py`, `cli/commands/catalog.py`, `cli/commands/system.py`, `cli/commands/preview.py`, `cli/commands/selection.py`, `cli/commands/ai_mask.py`
**テスト**: `tests/integration/test_cli_develop.py` に `--json` 入力テスト追加

**要確認事項**: `--json-stdin` のテストで stdin をモックする方法。Click の `CliRunner` は `input` パラメータで stdin を渡せる。

#### Task 8: `--fields` の動作修正 (#5)

**現状**: `lr --fields Exposure develop get-settings` → `{}`。

**根本原因の仮説**:
1. レスポンスのキー名がスキーマの `response_fields` と異なる（例: レスポンスが `{"Exposure2012": 0.5}` で `Exposure` ではフィルタに引っかからない）
2. `_filter_fields` はトップレベルのみフィルタするが、レスポンスが `{"result": {"Exposure": ...}}` のようにネストしている

**調査が必要**: 実際の `develop.getSettings` レスポンス構造を確認する。MockServer のレスポンスと実機レスポンスの差異を検証。

**修正方針**:
- レスポンス構造に応じて `_filter_fields` を修正
- もしキー名が `Exposure2012` 等の Lightroom 内部名である場合、エイリアスマッピングを追加
- `--fields` が空結果を返す場合、警告メッセージを出力する（「指定されたフィールドが見つかりません: Exposure」）

**影響ファイル**: `cli/output.py`, 場合により `cli/helpers.py`
**テスト**: `tests/test_output.py` に fields フィルタのテスト追加

#### Task 9: Phase 2 テスト実行 + Codex レビュー

---

### Phase 3: スキーマ充実化（#6, #7, #12, #13）

**テーマ**: `lr schema` の情報量を実用レベルにする

#### Task 10: response_fields の充実 (#6)

**現状**: `develop.getSettings` のみ `response_fields` が定義済み。他は全て空配列。

**修正内容**:
- 主要コマンドの response_fields を定義:
  - `system.ping` → `["status", "timestamp"]`
  - `system.status` → `["status", "uptime", "version", "connections"]`
  - `catalog.getSelectedPhotos` → `["photos", "count"]`
  - `catalog.getAllPhotos` → `["photos", "total", "limit", "offset"]`
  - `catalog.searchPhotos` → `["photos", "total", "query"]`
  - `catalog.getPhotoMetadata` → `["filename", "path", "rating", "flag", "keywords", "dimensions", "dateCreated"]`
  - `preview.generatePreview` → `["path", "size", "format"]`
  - `develop.getValue` → `["parameter", "value"]`
  - `develop.getRange` → `["parameter", "min", "max"]`

**注意**: response_fields は「保証されるフィールド」ではなく「主要なフィールド」。実機レスポンスとの差異がある場合はドキュメント内で注記。

**影響ファイル**: `lightroom_sdk/schema.py`
**テスト**: `tests/test_schema.py` で response_fields の非空チェック

#### Task 11: パラメータ description の充実 (#7)

**現状**: 多数のパラメータで `description=""` のまま。

**修正内容**:
- 全 `ParamSchema` の `description` を埋める
- 特に:
  - `param` → `"Develop parameter name (e.g., Exposure, Contrast, Highlights, Shadows, Whites, Blacks, Temperature, Tint, Vibrance, Saturation, Clarity, Dehaze, Texture)"`
  - `photoId` → `"Photo ID (obtain via 'lr catalog get-selected' or 'lr catalog list')"`
  - `settings` → `"JSON object mapping parameter names to values (e.g., {\"Exposure\": 0.5, \"Contrast\": 25})"`
  - `points` → `"Array of [x, y] coordinate pairs, each 0-255 (e.g., [[0,0],[128,140],[255,255]])"`
  - enum パラメータ → 各値の意味を記述

**影響ファイル**: `lightroom_sdk/schema.py`
**テスト**: `tests/test_schema.py` で description 非空チェック

#### Task 12: develop.ai.* のスキーマ改善 (#12)

**現状**: `develop.ai.<type>` という cli_path でスキーマ登録されているが、`lr schema develop.ai` で検索すると `develop.ai` グループとして認識されない（`get_schemas_by_group("develop.ai")` が `<type>` を含むパスを見つけられない可能性）。

**修正内容**:
- `cli_path` を `develop.ai.subject`, `develop.ai.sky` 等の具体的な値に変更（ただし単一スキーマで6種類のコマンドを表現しているため、設計判断が必要）
- **案A**: 6つの個別スキーマに分割 → スキーマ数が増えるが正確
- **案B**: `develop.ai.mask` として1つ残し、`selectionType` パラメータで区別 → `lr schema develop.ai.mask` で表示
- **推奨**: 案B。実装は1コマンドなので、スキーマも1つが自然

**影響ファイル**: `lightroom_sdk/schema.py`
**テスト**: `tests/test_schema.py`, `tests/integration/test_cli_schema.py`

#### Task 13: suggestions フィールドの発火確認 (#13)

**現状**: `ValidationError` に `suggestions` フィールドがあり、`_find_similar()` で類似パラメータを検索する仕組みは存在する。しかし「未知のパラメータ」エラー時しか発火しない。

**修正内容**:
- enum バリデーションエラー時にも suggestions を付与（有効な値の一覧を表示）
- 型変換エラー時にも suggestions を付与（期待される型の例を表示）
- `format_error` の JSON モードで suggestions が実際に出力されることをテストで確認

**影響ファイル**: `cli/validation.py`, `cli/output.py`
**テスト**: `tests/test_validation.py` で suggestions 出力テスト

#### Task 14: Phase 3 テスト実行 + Codex レビュー

---

### Phase 4: SKILLS.md 整合性修正（#9, #15, #16, #17）

**テーマ**: ドキュメントと実装の乖離を解消

#### Task 15: SKILLS.md コマンド表記の修正 (#9)

**現状の乖離**:
- `develop apply '{"Exposure": 1.0}'` → 実際は `--settings '{"Exposure": 1.0}'`
- `lr schema develop.setValue` → 実際は `lr schema develop.set`
- その他の表記不一致の網羅的チェック

**修正内容**:
- SKILLS.md の全コマンド例を実機テスト可能な形式に修正
- `lr schema <cli_path>` の表記を `cli_path` ベースに統一

**影響ファイル**: `SKILLS.md`
**テスト**: なし（ドキュメントのみ）。ただし、修正後に各コマンド例を `--dry-run` で検証可能であることを確認

#### Task 16: Develop パラメータ一覧の追加 (#15)

**修正内容**:
- SKILLS.md に「Develop Parameters Reference」セクション追加
- 主要パラメータの名前・範囲・説明を表形式で記載
- `lr develop range PARAM` コマンドで動的に確認できることも併記

**影響ファイル**: `SKILLS.md`

#### Task 17: PHOTO_ID 取得フローの明示 (#16) + catalog/selection 使い分けガイド (#17)

**修正内容**:
- SKILLS.md に「Getting Started for Agents」セクション追加:
  - Step 1: 接続確認 (`lr system check-connection`)
  - Step 2: 写真取得 (`lr -o json catalog get-selected` → `photoId` フィールド)
  - Step 3: 操作実行
- catalog vs selection の使い分けガイド:
  - **catalog**: photoId を指定して特定の写真を操作（明示的ターゲット）
  - **selection**: 現在の選択状態に対して操作（暗黙的ターゲット、ナビゲーション向き）
  - **推奨**: エージェントは catalog を優先（明示的で予測可能）

**影響ファイル**: `SKILLS.md`

#### Task 18: Phase 4 テスト実行 + 最終レビュー

---

### スコープ外（次回評価で検討）

- catalog/selection の責務重複 (#10) → Phase 4 のドキュメントで使い分けを明示するのみ
- develop reset-* の統合 (#11) → 破壊的変更のためバージョンアップ時に検討

---

## 全タスク一覧

| Task | Phase | 概要 | 影響ファイル | 新規テスト数 |
|------|-------|------|-------------|-------------|
| 1 | 1 | `_parse_pairs` トレースバック修正 | `develop.py` | 3 |
| 2 | 1 | 接続ログ stderr 分離 | `main.py` | 2 |
| 3 | 1 | exit code 正常化 | `system.py`, `helpers.py` | 4 |
| 4 | 1 | `lr schema` exit code 修正 | `schema.py` | 2 |
| 5 | 1 | check-connection 構造化出力 | `system.py` | 2 |
| 6 | 1 | Phase 1 テスト + Codex レビュー | — | — |
| 7 | 2 | `--json`/`--json-stdin` 適用 | `develop.py`, `catalog.py`, 他4ファイル | 5 + 全コマンド--help網羅テスト |
| 8 | 2 | `--fields` 動作修正 | `output.py`, `helpers.py` | 3 |
| 9 | 2 | Phase 2 テスト + Codex レビュー | — | — |
| 10 | 3 | response_fields 充実 | `lightroom_sdk/schema.py` | 2 |
| 11 | 3 | パラメータ description 充実 | `lightroom_sdk/schema.py` | 2 |
| 12 | 3 | develop.ai.* スキーマ改善 | `lightroom_sdk/schema.py` | 2 |
| 13 | 3 | suggestions 発火改善 | `validation.py`, `output.py` | 4 |
| 14 | 3 | Phase 3 テスト + Codex レビュー | — | — |
| 15 | 4 | SKILLS.md コマンド表記修正 | `SKILLS.md` | 0 |
| 16 | 4 | Develop パラメータ一覧追加 | `SKILLS.md` | 0 |
| 17 | 4 | PHOTO_ID フロー + catalog/selection ガイド | `SKILLS.md` | 0 |
| 18 | 4 | Phase 4 テスト + 最終レビュー | — | — |

**合計**: 18タスク / 4 Phase / 新規テスト ~31件

---

## テスト戦略

### 原則

1. **TDD (Red-Green-Commit)**: 各 Task でまずテストを書き、失敗を確認してから実装
2. **デグレ防止**: 各 Phase 終了時に全 450 テスト + 新規テストが全パス
3. **Codex レビューゲート**: 各 Phase 終了時にレビュー実施。Critical/Important 指摘は次 Phase に進む前に解決

### テストカテゴリ

| カテゴリ | テスト内容 | 場所 |
|---------|----------|------|
| Unit | `_parse_pairs` エラーハンドリング | `tests/test_develop.py` (新規) |
| Unit | `_filter_fields` のキー不一致 | `tests/test_output.py` |
| Unit | `ValidationError.suggestions` | `tests/test_validation.py` |
| Unit | response_fields / description 非空 | `tests/test_schema.py` |
| Integration | exit code 検証 | `tests/integration/test_cli_system.py` |
| Integration | `--json` 入力 | `tests/integration/test_cli_develop.py` |
| Integration | `--fields` フィルタ | `tests/integration/test_cli_develop.py` |
| Integration | ログ出力先 (stderr) | `tests/integration/test_cli_system.py` |

---

## 不確実な点・要確認事項

### 1. `--fields` の根本原因（Task 8）

`develop.getSettings` の実際のレスポンスキー名が不明。MockServer は簡易レスポンスを返しており、実機の Lightroom が返すキー名（`Exposure` vs `Exposure2012` 等）を確認する必要がある。

**確認方法**: `lr -o json develop get-settings` を実機で実行し、レスポンスキーを確認。

**もし `Exposure2012` 等の場合**:
- `--fields Exposure` → `Exposure2012` へのエイリアス解決が必要
- スキーマに `field_aliases` マッピングを追加する追加タスクが発生

### 2. `--json` の適用範囲（Task 7）

全 55 コマンドに `@json_input_options` を機械的に追加するか、mutating コマンドのみに限定するか。

**推奨**: 全コマンドに適用。理由: 読み取りコマンドでも `--json` でパラメータを渡したいケース（例: `lr catalog search --json '{"query": "sunset", "limit": 10}'`）がある。

### 3. `reconnect` コマンドの構造化（Task 3, 5）

`reconnect` は特殊な操作で `execute_command` に収まらない。`handle_error` ヘルパーで対応するが、成功時の出力も構造化すべきか。

**推奨**: 成功時も `OutputFormatter.format({"status": "reconnected"}, fmt)` を使用。

### 4. develop.ai スキーマの表現（Task 12）

現在 `develop.ai.<type>` という placeholder cli_path が使われている。6つの具体的コマンド（subject, sky, background, objects, people, landscape）を個別スキーマにするか、1つのスキーマで `selectionType` パラメータとして表現するか。

**推奨**: `develop.ai.mask` として1つのスキーマを登録。`batch` は既に別スキーマ。`lr schema develop.ai` でグループ表示した際に `mask` と `batch` が出る形。

### 5. catalog/selection の責務重複（#10）— 今回スコープ外

Phase 4 のドキュメントで使い分けを明示するのみ。API の統合・廃止は次のメジャーバージョンで検討。

---

## 依存関係図

```
Phase 1 (エラーハンドリング)
  ├── Task 1: _parse_pairs     ─┐
  ├── Task 2: logging stderr    │
  ├── Task 3: exit code         ├── Task 6: テスト + レビュー
  ├── Task 4: schema exit code  │
  └── Task 5: check-connection ─┘

Phase 2 (入力パイプライン) ← Phase 1 完了後
  ├── Task 7: --json 適用       ├── Task 9: テスト + レビュー
  └── Task 8: --fields 修正    ─┘

Phase 3 (スキーマ充実) ← Phase 2 完了後（cli/output.py 衝突のため順次）
  ├── Task 10: response_fields  ─┐
  ├── Task 11: descriptions      ├── Task 14: テスト + レビュー
  ├── Task 12: develop.ai        │
  └── Task 13: suggestions      ─┘

Phase 4 (ドキュメント) ← Phase 2, 3 完了後
  ├── Task 15: SKILLS.md 修正   ─┐
  ├── Task 16: パラメータ一覧    ├── Task 18: テスト + 最終レビュー
  └── Task 17: フローガイド     ─┘
```

**Phase 2 → Phase 3 は順次実行**（Task 8 と Task 13 が共に `cli/output.py` を変更するため並行不可。Codexレビュー指摘による修正）。

---

## 見積り

| Phase | タスク数 | 推定時間 | 変更行数 |
|-------|---------|---------|---------|
| Phase 1 | 6 | 1.5h | ~150行 |
| Phase 2 | 3 | 1.5h | ~200行 |
| Phase 3 | 5 | 1.0h | ~100行 |
| Phase 4 | 4 | 0.5h | ~80行 |
| **合計** | **18** | **4.5h** | **~530行** |

---

## Codex レビュー指摘と対応

| # | 指摘 | 対応 |
|---|------|------|
| 1 | Phase 2/3 並行不可（`output.py` 衝突） | Phase 2→3 順次実行に変更 |
| 2 | Task 7 の `--json` 適用が技術未完（引数整合性） | `ctx.params` 経由のためコールバック引数追加不要であることを確認・明記 |
| 3 | ログ混入の根本原因仮説が弱い | 実機検証でstderrに正しく分離されていることを確認。Task 2 を「確認+エラー出力統一」に修正 |
| 4 | Task 7 のテスト不足（55コマンド） | 全コマンド `--help` 網羅パラメトリックテストを追加 |
| 5 | Phase数表記不整合（5 vs 4） | 「4 Phase」に統一 |
