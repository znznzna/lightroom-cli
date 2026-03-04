# CLI Reference

全 107 コマンドのリファレンスです。

## Global Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--output` | `-o` | `text` | 出力形式 (`json` / `text` / `table`) |
| `--verbose` | `-v` | `false` | デバッグログを有効化 |
| `--timeout` | `-t` | `30.0` | デフォルトタイムアウト（秒） |
| `--version` | | | バージョン表示 |

---

## lr system (4 commands)

接続管理・ステータス確認。

| Command | Description |
|---------|-------------|
| `lr system ping` | Lightroom への接続テスト |
| `lr system status` | ブリッジのステータス取得 |
| `lr system reconnect` | 強制再接続 |
| `lr system check-connection` | 接続状態の詳細チェック |

---

## lr catalog (27 commands)

カタログ操作・写真検索・メタデータ管理。

### 写真取得・検索

| Command | Description |
|---------|-------------|
| `lr catalog get-selected` | 選択中の写真を取得 |
| `lr catalog list [--limit N] [--offset N]` | カタログ内の写真を一覧表示 |
| `lr catalog search <query> [--limit N]` | キーワードで写真を検索 |
| `lr catalog find <criteria_json>` | 構造化条件で写真を検索 |
| `lr catalog find-by-path <path>` | ファイルパスで写真を検索 |
| `lr catalog get-info <photo_id>` | 写真の詳細メタデータを取得 |
| `lr catalog select <photo_ids...>` | IDで写真を選択 |

### メタデータ設定

| Command | Description |
|---------|-------------|
| `lr catalog set-rating <photo_id> <0-5>` | レーティングを設定 |
| `lr catalog set-flag <photo_id> <pick\|reject\|none>` | フラグを設定 |
| `lr catalog set-title <photo_id> <title>` | タイトルを設定 |
| `lr catalog set-caption <photo_id> <caption>` | キャプションを設定 |
| `lr catalog set-color-label <photo_id> <color>` | カラーラベルを設定 |
| `lr catalog set-metadata <photo_id> <key> <value>` | 任意のメタデータを設定 |
| `lr catalog add-keywords <photo_id> <kw...>` | キーワードを追加 |
| `lr catalog remove-keyword <photo_id> <keyword>` | キーワードを削除 |
| `lr catalog get-flag <photo_id>` | フラグ状態を取得 |
| `lr catalog batch-metadata <photo_ids...>` | 複数写真のメタデータを一括取得 |

### カタログ構造

| Command | Description |
|---------|-------------|
| `lr catalog collections` | コレクション一覧 |
| `lr catalog create-collection <name>` | コレクション作成 |
| `lr catalog create-collection-set <name>` | コレクションセット作成 |
| `lr catalog create-smart-collection <name>` | スマートコレクション作成 |
| `lr catalog folders` | フォルダ一覧 |
| `lr catalog keywords` | キーワード一覧 |
| `lr catalog create-keyword <keyword>` | キーワード作成 |
| `lr catalog get-view-filter` | 現在のビューフィルタ取得 |
| `lr catalog set-view-filter <filter_json>` | ビューフィルタ設定 |

### 写真操作

| Command | Description |
|---------|-------------|
| `lr catalog rotate-left` | 選択写真を左回転 |
| `lr catalog rotate-right` | 選択写真を右回転 |
| `lr catalog create-virtual-copy` | 仮想コピーを作成 |
| `lr catalog remove-from-catalog` | カタログから写真を削除 |

---

## lr develop (55 commands)

現像設定・マスク・トーンカーブ・フィルタ・ローカル補正。

### 基本操作

| Command | Description |
|---------|-------------|
| `lr develop get-settings` | 全現像設定を取得 |
| `lr develop set <param> <value> [...]` | 現像パラメータを設定（複数可） |
| `lr develop get <param>` | 単一パラメータの値を取得 |
| `lr develop range <param>` | パラメータの min/max 範囲を取得 |
| `lr develop auto-tone` | AutoTone を適用 |
| `lr develop auto-wb` | Auto White Balance を適用 |
| `lr develop reset` | 現像設定をデフォルトにリセット |
| `lr develop reset-param <param>` | 特定パラメータをリセット |
| `lr develop apply <settings_json>` | JSON で現像設定を一括適用 |
| `lr develop process-version` | プロセスバージョンを取得 |
| `lr develop set-process-version <version>` | プロセスバージョンを設定 |

### プリセット・スナップショット・コピー

| Command | Description |
|---------|-------------|
| `lr develop preset <name>` | プリセットを適用 |
| `lr develop snapshot <name>` | スナップショットを作成 |
| `lr develop copy-settings` | 現像設定をコピー |
| `lr develop paste-settings` | 現像設定をペースト |
| `lr develop tool <tool_name>` | ツールを選択 |
| `lr develop edit-in-photoshop` | Photoshop で開く |

### トーンカーブ (lr develop curve)

| Command | Description |
|---------|-------------|
| `lr develop curve get [--channel RGB\|Red\|Green\|Blue]` | カーブポイントを取得 |
| `lr develop curve set <points_json> [--channel ...]` | カーブポイントを設定 |
| `lr develop curve add-point <x> <y> [--channel ...]` | ポイントを追加 |
| `lr develop curve remove-point <x> <y> [--channel ...]` | ポイントを削除 |
| `lr develop curve s-curve [--channel ...]` | S カーブプリセット |
| `lr develop curve linear [--channel ...]` | リニアにリセット |

### マスキング (lr develop mask)

| Command | Description |
|---------|-------------|
| `lr develop mask list` | 全マスク一覧 |
| `lr develop mask selected` | 選択中のマスクを取得 |
| `lr develop mask create` | 新規マスク作成 |
| `lr develop mask select <mask_id>` | マスクを選択 |
| `lr develop mask delete <mask_id>` | マスクを削除 |
| `lr develop mask invert <mask_id>` | マスクを反転 |
| `lr develop mask add <tool>` | ツールを追加 (brush/gradient/radial/range/ai) |
| `lr develop mask intersect <tool>` | ツールでインターセクト |
| `lr develop mask subtract <tool>` | ツールでサブトラクト |
| `lr develop mask tool-info` | 選択中のツール情報 |
| `lr develop mask select-tool <tool_id>` | ツールを選択 |
| `lr develop mask delete-tool <tool_id>` | ツールを削除 |
| `lr develop mask go-to` | マスキングビューに移動 |
| `lr develop mask toggle-overlay` | オーバーレイ表示切替 |
| `lr develop mask activate` | マスキングモード有効化 |
| `lr develop mask complex <workflow_json>` | 複合マスクを作成 |

### ローカル補正 (lr develop local)

| Command | Description |
|---------|-------------|
| `lr develop local set <param> <value>` | ローカル補正パラメータを設定 |
| `lr develop local get <param>` | ローカル補正パラメータを取得 |
| `lr develop local params` | 利用可能なローカルパラメータ一覧 |
| `lr develop local apply <settings_json>` | JSON でローカル補正を一括適用 |
| `lr develop local create-mask <settings_json>` | マスク付きローカル補正を作成 |

### フィルタ (lr develop filter)

| Command | Description |
|---------|-------------|
| `lr develop filter graduated` | 段階フィルタを作成 |
| `lr develop filter radial` | 円形フィルタを作成 |
| `lr develop filter brush` | ブラシフィルタを作成 |
| `lr develop filter ai-select` | AI 選択マスクを作成 |
| `lr develop filter range` | レンジマスクを作成 |

### カラー操作 (lr develop color)

| Command | Description |
|---------|-------------|
| `lr develop color enhance` | カラーエンハンス |
| `lr develop color cyan-swatch` | シアンカラースウォッチ |
| `lr develop color green-swatch` | グリーンカラースウォッチ |

### デバッグ (lr develop debug)

| Command | Description |
|---------|-------------|
| `lr develop debug dump` | LrDevelopController 情報ダンプ |
| `lr develop debug probe` | 全パラメータをプローブ |
| `lr develop debug monitor` | パラメータ変更モニタ |
| `lr develop debug gradient-params` | グラデーションパラメータを調査 |

### リセット系

| Command | Description |
|---------|-------------|
| `lr develop reset-brush` | ブラシをリセット |
| `lr develop reset-circular` | 円形フィルタをリセット |
| `lr develop reset-crop` | クロップをリセット |
| `lr develop reset-gradient` | グラデーションをリセット |
| `lr develop reset-healing` | ヒーリングをリセット |
| `lr develop reset-masking` | マスキングをリセット |
| `lr develop reset-redeye` | 赤目除去をリセット |
| `lr develop reset-spot` | スポット除去をリセット |
| `lr develop reset-transforms` | トランスフォームをリセット |

---

## lr preview (4 commands)

プレビュー生成・情報取得。

| Command | Description | Timeout |
|---------|-------------|---------|
| `lr preview generate-current` | 選択写真のプレビュー生成 | 120s |
| `lr preview generate [--size N] [--format jpeg\|png]` | サイズ・形式指定でプレビュー生成 | 120s |
| `lr preview generate-batch` | バッチプレビュー生成 | 300s |
| `lr preview info` | プレビュー情報を取得 | 30s |

---

## lr selection (17 commands)

選択写真の操作・フラグ・レーティング・カラーラベル。

### フラグ操作

| Command | Description |
|---------|-------------|
| `lr selection flag` | Pick フラグを設定 |
| `lr selection reject` | Reject フラグを設定 |
| `lr selection unflag` | フラグを解除 |
| `lr selection get-flag` | フラグ状態を取得 |

### レーティング

| Command | Description |
|---------|-------------|
| `lr selection set-rating <0-5>` | レーティングを設定 |
| `lr selection get-rating` | レーティングを取得 |
| `lr selection increase-rating` | レーティングを +1 |
| `lr selection decrease-rating` | レーティングを -1 |

### カラーラベル

| Command | Description |
|---------|-------------|
| `lr selection color-label <color>` | カラーラベルを設定 (red/yellow/green/blue/purple/none) |
| `lr selection get-color-label` | カラーラベルを取得 |
| `lr selection toggle-label <color>` | カラーラベルをトグル (red/yellow/green/blue/purple) |

### 選択操作

| Command | Description |
|---------|-------------|
| `lr selection next` | 次の写真に移動 |
| `lr selection previous` | 前の写真に移動 |
| `lr selection select-all` | 全写真を選択 |
| `lr selection select-none` | 全選択解除 |
| `lr selection select-inverse` | 選択を反転 |
| `lr selection extend [--direction left\|right] [--amount N]` | 選択範囲を拡張 |
| `lr selection deselect-active` | アクティブ写真の選択解除 |
| `lr selection deselect-others` | アクティブ以外の選択解除 |

---

## Develop Parameters

`lr develop set` で使用可能な主要パラメータ（タブ補完対応）:

| Parameter | Range | Description |
|-----------|-------|-------------|
| `Exposure` | -5.0 〜 5.0 | 露出 |
| `Contrast` | -100 〜 100 | コントラスト |
| `Highlights` | -100 〜 100 | ハイライト |
| `Shadows` | -100 〜 100 | シャドウ |
| `Whites` | -100 〜 100 | 白レベル |
| `Blacks` | -100 〜 100 | 黒レベル |
| `Clarity` | -100 〜 100 | 明瞭度 |
| `Dehaze` | -100 〜 100 | かすみ除去 |
| `Vibrance` | -100 〜 100 | 自然な彩度 |
| `Saturation` | -100 〜 100 | 彩度 |
| `Temperature` | 2000 〜 50000 | 色温度 |
| `Tint` | -150 〜 150 | 色かぶり |
| `Sharpness` | 0 〜 150 | シャープネス |
| `LuminanceSmoothing` | 0 〜 100 | ノイズ軽減（輝度） |
| `ColorNoiseReduction` | 0 〜 100 | ノイズ軽減（カラー） |
| `PostCropVignetteAmount` | -100 〜 100 | 切り抜き後の周辺光量 |
| `GrainAmount` | 0 〜 100 | 粒子の量 |
| `ShadowTint` | -100 〜 100 | シャドウの色かぶり |
| `RedHue` | -100 〜 100 | 赤色相 |
| `GreenHue` | -100 〜 100 | 緑色相 |
| `BlueHue` | -100 〜 100 | 青色相 |
| `RedSaturation` | -100 〜 100 | 赤彩度 |
| `GreenSaturation` | -100 〜 100 | 緑彩度 |
| `BlueSaturation` | -100 〜 100 | 青彩度 |

パラメータの全リストと範囲は `lr develop range <param>` で確認できます。
