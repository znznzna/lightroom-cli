# CLI Reference

## Global Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--output` | `-o` | `text` | Output format (`json` / `text` / `table`) |
| `--verbose` | `-v` | `false` | Enable debug logging |
| `--timeout` | `-t` | `30.0` | Default timeout in seconds |
| `--version` | | | Show version |

## lr system

| Command | Description |
|---------|-------------|
| `lr system ping` | Lightroomへの接続テスト |
| `lr system status` | ブリッジのステータス取得 |
| `lr system reconnect` | 再接続を実行 |
| `lr system check-connection` | 接続状態の詳細チェック |

## lr catalog

| Command | Description |
|---------|-------------|
| `lr catalog get-selected` | 選択中の写真を取得 |
| `lr catalog list [--limit N] [--offset N]` | カタログ内の写真を一覧表示 |
| `lr catalog search <query> [--limit N]` | キーワードで写真を検索 |
| `lr catalog get-info <photo_id>` | 写真の詳細メタデータを取得 |
| `lr catalog set-rating <photo_id> <rating>` | レーティングを設定 (0-5) |
| `lr catalog add-keywords <photo_id> <kw1> [kw2 ...]` | キーワードを追加 |

### 使用例

```bash
# 選択中の写真のIDを取得してJSON出力
lr -o json catalog get-selected

# 最新10枚を一覧
lr catalog list --limit 10

# "landscape" で検索
lr catalog search landscape --limit 20

# レーティング5を設定
lr catalog set-rating ABC123 5

# キーワード追加
lr catalog add-keywords ABC123 nature sunset
```

## lr develop

| Command | Description |
|---------|-------------|
| `lr develop get-settings` | 現在の現像設定をすべて取得 |
| `lr develop set <param> <value> [<param2> <value2> ...]` | 現像パラメータを設定 |
| `lr develop auto-tone` | AutoToneを適用 |
| `lr develop reset` | 現像設定をデフォルトにリセット |

### パラメータ一覧

`lr develop set` で使用可能なパラメータ（タブ補完対応）:

| Parameter | Range |
|-----------|-------|
| Exposure | -5.0 〜 5.0 |
| Contrast | -100 〜 100 |
| Highlights | -100 〜 100 |
| Shadows | -100 〜 100 |
| Whites | -100 〜 100 |
| Blacks | -100 〜 100 |
| Clarity | -100 〜 100 |
| Dehaze | -100 〜 100 |
| Vibrance | -100 〜 100 |
| Saturation | -100 〜 100 |
| Temperature | 2000 〜 50000 |
| Tint | -150 〜 150 |
| Sharpness | 0 〜 150 |
| LuminanceSmoothing | 0 〜 100 |
| ColorNoiseReduction | 0 〜 100 |
| PostCropVignetteAmount | -100 〜 100 |
| GrainAmount | 0 〜 100 |
| ShadowTint | -100 〜 100 |
| RedHue | -100 〜 100 |
| GreenHue | -100 〜 100 |
| BlueHue | -100 〜 100 |
| RedSaturation | -100 〜 100 |
| GreenSaturation | -100 〜 100 |
| BlueSaturation | -100 〜 100 |

### 使用例

```bash
# 単一パラメータ設定
lr develop set Exposure 1.5

# 複数パラメータを一括設定
lr develop set Exposure 1.5 Contrast 25 Clarity 30

# 設定をJSON出力で確認
lr -o json develop get-settings

# AutoTone
lr develop auto-tone

# リセット
lr develop reset
```

## lr preview

| Command | Description | Timeout |
|---------|-------------|---------|
| `lr preview generate-current` | 選択中の写真のプレビュー生成 | 120s |
| `lr preview generate [--size N] [--format jpeg\|png]` | 指定サイズ・形式でプレビュー生成 | 120s |
| `lr preview generate-batch` | バッチプレビュー生成 | 300s |

### 使用例

```bash
# 現在の写真のプレビュー
lr preview generate-current

# 2048pxのPNGプレビュー
lr preview generate --size 2048 --format png

# バッチ生成
lr preview generate-batch
```
