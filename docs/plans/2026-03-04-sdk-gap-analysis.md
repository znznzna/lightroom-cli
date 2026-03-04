# Lightroom SDK 機能カバレッジ Gap分析レポート & 拡張設計案

**作成日**: 2026-03-04
**ステータス**: Draft
**対象**: lightroom-cli プロジェクト

---

## 目次

1. [フラグ付き写真問題の原因分析](#1-フラグ付き写真問題の原因分析)
2. [3層 Gap分析](#2-3層-gap分析)
3. [Gap A: SDK APIにあるがLuaプラグインに未実装](#3-gap-a-sdk-apiにあるがluaプラグインに未実装)
4. [Gap B: Luaプラグインに登録済みだがCLIに未公開](#4-gap-b-luaプラグインに登録済みだがcliに未公開)
5. [Gap C: CLIに公開済みだがLuaバックエンドが無い](#5-gap-c-cliに公開済みだがluaバックエンドが無い)
6. [優先度付きロードマップ](#6-優先度付きロードマップ)
7. [CLIコマンド設計案](#7-cliコマンド設計案)
8. [実装方針](#8-実装方針)

---

## 1. フラグ付き写真問題の原因分析

### 結論: SDK制限ではなく、実装の欠如が原因

フラグ（Pick/Reject）機能は Lightroom SDK で**完全にサポート**されている。

#### SDK側の対応状況

| SDK API | 機能 | 対応状況 |
|---------|------|----------|
| `LrPhoto:getRawMetadata("pickStatus")` | フラグ状態読み取り (-1=reject, 0=none, 1=pick) | 利用可能 |
| `LrPhoto:setRawMetadata("pickStatus", value)` | フラグ状態書き込み | 利用可能 (SDK v4.0+) |
| `LrSelection.flagAsPick()` | 選択写真にPickフラグ設定 | 利用可能 |
| `LrSelection.flagAsReject()` | 選択写真にRejectフラグ設定 | 利用可能 |
| `LrSelection.removeFlag()` | フラグ解除 | 利用可能 |
| `LrSelection.getFlag()` | フラグ状態取得 | 利用可能 |
| `LrCatalog.findPhotos({criteria="pick", ...})` | フラグ条件での写真検索 | 利用可能 |

#### 現在の実装の問題

1. **CatalogModule.lua の `searchPhotos`**: `catalog:getTargetPhotos()` または `catalog:getAllPhotos()` を使用しており、`findPhotos` による条件検索を**実装していない**。フラグ条件でのフィルタリングが不可能。

2. **CatalogModule.lua の `getPhotoMetadata`**: `pickStatus` を `getRawMetadata` で読み取っておらず、レスポンスに含まれていない。`colorNameForLabel` は取得しているが `pickStatus` は欠落。

3. **CLIに `catalog.setFlag` / `catalog.getFlag` コマンドが存在しない**: フラグの読み書きを行うCLIコマンドもLuaハンドラも登録されていない。

4. **CLIの `catalog search` コマンド**: 単純なクエリ文字列のみ受け付け、`pick`/`reject`/`rating`/`colorLabel` などの構造化された検索条件をサポートしていない。

#### 解決策

| 修正箇所 | 作業内容 | 工数 |
|----------|----------|------|
| `CatalogModule.lua` `getPhotoMetadata` | `pickStatus` を `getRawMetadata("pickStatus")` で取得しレスポンスに追加 | 5分 |
| `CatalogModule.lua` `searchPhotos` / `getAllPhotos` | 各写真の `pickStatus` をレスポンスに追加 | 10分 |
| `CatalogModule.lua` 新規: `setFlag` | `LrPhoto:setRawMetadata("pickStatus", value)` を使用（withWriteAccessDo内） | 30分 |
| `CatalogModule.lua` 新規: `getFlag` | `LrPhoto:getRawMetadata("pickStatus")` を使用 | 15分 |
| `CatalogModule.lua` `findPhotos` | `searchDesc` による `pick` 条件検索を実装 | 1時間 |
| `PluginInit.lua` | `catalog.setFlag`, `catalog.getFlag` をルーターに登録 | 5分 |
| `cli/commands/catalog.py` | `set-flag`, `get-flag` CLIコマンド追加 | 30分 |
| `cli/commands/catalog.py` `search` | `--flag`, `--rating`, `--color-label` オプション追加 | 30分 |

---

## 2. 3層 Gap分析

### 全体統計

| 層 | 項目数 | カバー率 |
|----|--------|----------|
| SDK API メソッド（主要4モジュール） | ~150+ | - |
| Luaプラグイン登録コマンド | 73 | ~49% |
| CLI公開コマンド | 17 | ~11% |

### Gap分類

| Gap種別 | 説明 | 該当数 | 対応方針 |
|---------|------|--------|----------|
| **Gap A** | SDK APIにあるがLuaに未実装 | ~60+ | 新規Luaモジュール/関数作成 |
| **Gap B** | Luaに登録済みだがCLIに未公開 | 56 | CLIコマンド追加のみ |
| **Gap C** | CLIに公開済みだがLuaバックエンドが無い | 2 | Lua実装が必要 |

---

## 3. Gap A: SDK APIにあるがLuaプラグインに未実装

### 3.1 LrSelection（完全未実装）

現在のLuaプラグインは `LrSelection` モジュールを**一切使用していない**。

| SDK API | 機能 | 優先度 |
|---------|------|--------|
| `flagAsPick()` | Pickフラグ設定 | **P0** |
| `flagAsReject()` | Rejectフラグ設定 | **P0** |
| `removeFlag()` | フラグ解除 | **P0** |
| `getFlag()` | フラグ状態取得 | **P0** |
| `setRating(rating)` | レーティング設定 (LrSelection経由) | P1 |
| `getRating()` | レーティング取得 (LrSelection経由) | P1 |
| `increaseRating()` | レーティング+1 | P2 |
| `decreaseRating()` | レーティング-1 | P2 |
| `setColorLabel(label)` | カラーラベル設定 | **P1** |
| `getColorLabel()` | カラーラベル取得 | **P1** |
| `clearLabels()` | 全ラベルクリア | P2 |
| `toggleBlueLabel()` | 青ラベルトグル | P3 |
| `toggleGreenLabel()` | 緑ラベルトグル | P3 |
| `togglePurpleLabel()` | 紫ラベルトグル | P3 |
| `toggleRedLabel()` | 赤ラベルトグル | P3 |
| `toggleYellowLabel()` | 黄ラベルトグル | P3 |
| `selectAll()` | 全選択 | P2 |
| `selectNone()` | 選択解除 | P2 |
| `selectInverse()` | 選択反転 | P2 |
| `nextPhoto()` | 次の写真へ移動 | **P1** |
| `previousPhoto()` | 前の写真へ移動 | **P1** |
| `extendSelection(dir, amount)` | 選択範囲拡張 | P3 |
| `deselectActive()` | アクティブ選択解除 | P3 |
| `deselectOthers()` | 他の選択解除 | P3 |
| `removeFromCatalog()` | カタログから削除 (SDK 14.3+) | P2 |

### 3.2 LrPhoto メタデータ書き込み（部分未実装）

現在の `CatalogModule.lua` は `getRawMetadata` / `getFormattedMetadata` で読み取りは行っているが、`setRawMetadata` による書き込みは実装されていない。

| SDK API (`setRawMetadata` キー) | 機能 | 優先度 |
|------|------|--------|
| `pickStatus` | フラグ設定 | **P0** |
| `rating` | レーティング設定（LrPhoto経由） | **P1** |
| `label` | カラーラベル設定 | **P1** |
| `title` | タイトル設定 | **P1** |
| `caption` | キャプション設定 | **P1** |
| `copyName` | コピー名設定 | P2 |
| `creator` | 作成者設定 | P2 |
| `creatorJobTitle` | 作成者肩書き | P3 |
| `creatorAddress` / `creatorCity` / `creatorStateProvince` / `creatorPostalCode` / `creatorCountry` | 作成者住所系 | P3 |
| `creatorPhone` / `creatorEmail` / `creatorUrl` | 作成者連絡先 | P3 |
| `location` / `city` / `stateProvince` / `country` / `isoCountryCode` | 場所系 | P2 |
| `gps` / `gpsAltitude` | GPS座標 | P2 |
| `copyright` / `copyrightState` / `rightsUsageTerms` | 著作権系 | P2 |
| `colorNameForLabel` | カラーラベル（名前指定） | P1 |
| `altTextAccessibility` / `extDescrAccessibility` | アクセシビリティテキスト (v13.2+) | P3 |

### 3.3 LrPhoto メタデータ読み取り（部分未実装）

`getPhotoMetadata` で取得していないが SDK で利用可能なキー:

| `getRawMetadata` キー | 機能 | 優先度 |
|------|------|--------|
| `pickStatus` | フラグ状態 | **P0** |
| `fileSize` | ファイルサイズ（raw値） | P2 |
| `width` / `height` / `aspectRatio` | 画像寸法 | P2 |
| `isCropped` | クロップ有無 | P3 |
| `flash` | フラッシュ使用有無 | P3 |
| `exposureBias` | 露出補正 | P3 |
| `dateTimeDigitized` | デジタル化日時 | P3 |
| `lastEditTime` | 最終編集日時 | P2 |
| `uuid` | UUID | P2 |
| `countVirtualCopies` | 仮想コピー数 | P3 |
| `stackPositionInFolder` | スタック位置（一部取得済み） | P3 |
| `smartPreviewInfo` | スマートプレビュー情報 | P2 |
| `isVideo` | 動画判定 | P2 |
| `editCount` | 編集回数 | P3 |

### 3.4 LrPhoto その他メソッド（未実装）

| SDK メソッド | 機能 | 優先度 |
|------|------|--------|
| `applyDevelopPreset(preset, plugin)` | プリセット適用 | **P1** |
| `getDevelopSettings()` | 現像設定取得（LrPhoto経由） | P2 |
| `applyDevelopSettings(settings)` | 現像設定適用（LrPhoto経由） | P2 |
| `createDevelopSnapshot(name)` | スナップショット作成 | **P1** |
| `deleteDevelopSnapshot(snapshot)` | スナップショット削除 | P2 |
| `applyDevelopSnapshot(snapshot)` | スナップショット適用 | P2 |
| `getDevelopSnapshots()` | スナップショット一覧 | P2 |
| `buildSmartPreview()` | スマートプレビュー生成 | P2 |
| `deleteSmartPreview()` | スマートプレビュー削除 | P3 |
| `rotateLeft()` / `rotateRight()` | 回転 | P2 |
| `copySettings()` / `pasteSettings()` | 設定コピー&ペースト | **P1** |
| `addKeyword(keyword)` | キーワード追加（LrPhoto経由） | P1（Gap C参照） |
| `removeKeyword(keyword)` | キーワード削除 | P1 |
| `getContainedCollections()` | 所属コレクション取得（一部実装済み） | P3 |
| `addOrRemoveFromTargetCollection()` | ターゲットコレクション操作 | P2 |
| `openExportDialog()` | エクスポートダイアログ | P3 |
| `checkPhotoAvailability()` | 写真利用可能性チェック | P3 |
| `quickDevelop系` | クイック現像（ライブラリモジュール用） | P3 |

### 3.5 LrCatalog 高度な検索・コレクション管理（部分未実装）

| SDK メソッド | 機能 | 優先度 |
|------|------|--------|
| `findPhotos(searchDesc)` の完全実装 | 複合条件検索 | **P0** |
| `createCollection(name, parent)` | コレクション作成 | **P1** |
| `createSmartCollection(name, searchDesc)` | スマートコレクション作成 | P2 |
| `createCollectionSet(name, parent)` | コレクションセット作成 | P2 |
| `createKeyword(name, ...)` | キーワード作成 | P1 |
| `createVirtualCopies(photos)` | 仮想コピー作成 | P2 |
| `setActiveSources(sources)` | アクティブソース設定 | P2 |
| `getCurrentViewFilter()` | ビューフィルター取得 | P2 |
| `setViewFilter(filter)` | ビューフィルター設定 | P2 |
| `triggerImportUI()` | インポートUI起動 | P3 |
| `buildSmartPreviews(photos)` | バッチスマートプレビュー | P3 |
| `batchGetRawMetadata(photos, keys)` | バッチRawメタデータ取得 | P1 |
| `getLabelMapToColorName()` | カラーラベルマッピング | P2 |

### 3.6 LrDevelopController 未実装メソッド

Luaプラグインの `DevelopModule.lua` で LrDevelopController は広範に使用されているが、以下は未実装:

| SDK メソッド | 機能 | 優先度 |
|------|------|--------|
| `resetCrop()` | クロップリセット | P2 |
| `resetTransforms()` | 変形リセット | P2 |
| `resetSpotRemoval()` | スポット除去リセット | P2 |
| `resetRedeye()` | 赤目除去リセット | P3 |
| `resetHealing()` | ヒーリングリセット | P3 |
| `editInPhotoshop()` | Photoshopで編集 | P2 |
| `showClipping()` | クリッピング表示 | P3 |
| `setActiveColorGradingView()` | カラーグレーディングビュー | P3 |
| Spot/Remove関連 (countAllSpots, getAllSpots, etc.) | スポット操作 | P3 |
| Point Color関連 (addPointColorSwatch, etc.) | ポイントカラー操作 | P3 |
| Lens Blur関連 | レンズブラー操作 | P3 |
| GenAI関連 (deleteSelectedVariation, etc.) | GenAI操作 | P3 |

---

## 4. Gap B: Luaプラグインに登録済みだがCLIに未公開

Luaプラグイン（`PluginInit.lua` の `registerApiCommands`）には73コマンドが登録されているが、CLIには17コマンドしか公開されていない。**56コマンドがCLI未公開**。

### 4.1 Develop系 未公開コマンド（49コマンド）

#### 基本操作（CLIコマンド追加推奨）

| Luaコマンド | 提案CLIコマンド | 優先度 |
|------------|----------------|--------|
| `develop.applySettings` | `lr develop apply --settings '{...}'` | **P1** |
| `develop.getValue` | `lr develop get <param>` | **P1** |
| `develop.getRange` | `lr develop range <param>` | P2 |
| `develop.resetToDefault` | `lr develop reset-param <param>` | P2 |
| `develop.setAutoWhiteBalance` | `lr develop auto-wb` | **P1** |
| `develop.getProcessVersion` | `lr develop process-version` | P2 |
| `develop.setProcessVersion` | `lr develop set-process-version <version>` | P2 |

#### トーンカーブ操作

| Luaコマンド | 提案CLIコマンド | 優先度 |
|------------|----------------|--------|
| `develop.getCurvePoints` | `lr develop curve get [--channel <ch>]` | P2 |
| `develop.setCurvePoints` | `lr develop curve set --points '[[x,y],...]'` | P2 |
| `develop.setCurveLinear` | `lr develop curve linear` | P2 |
| `develop.setCurveSCurve` | `lr develop curve s-curve` | P2 |
| `develop.addCurvePoint` | `lr develop curve add-point <x> <y>` | P2 |
| `develop.removeCurvePoint` | `lr develop curve remove-point <index>` | P2 |

#### カラー操作

| Luaコマンド | 提案CLIコマンド | 優先度 |
|------------|----------------|--------|
| `develop.createGreenSwatch` | `lr develop color green-swatch` | P3 |
| `develop.createCyanSwatch` | `lr develop color cyan-swatch` | P3 |
| `develop.enhanceColors` | `lr develop color enhance` | P3 |

#### マスキング・ナビゲーション

| Luaコマンド | 提案CLIコマンド | 優先度 |
|------------|----------------|--------|
| `develop.goToMasking` | `lr develop mask go-to` | P2 |
| `develop.toggleOverlay` | `lr develop mask toggle-overlay` | P2 |
| `develop.selectTool` | `lr develop tool <tool_name>` | **P1** |

#### マスク管理

| Luaコマンド | 提案CLIコマンド | 優先度 |
|------------|----------------|--------|
| `develop.getAllMasks` | `lr develop mask list` | P2 |
| `develop.getSelectedMask` | `lr develop mask selected` | P2 |
| `develop.createNewMask` | `lr develop mask create` | P2 |
| `develop.selectMask` | `lr develop mask select <index>` | P2 |
| `develop.deleteMask` | `lr develop mask delete <index>` | P2 |
| `develop.getSelectedMaskTool` | `lr develop mask tool-info` | P3 |
| `develop.selectMaskTool` | `lr develop mask select-tool <index>` | P3 |
| `develop.deleteMaskTool` | `lr develop mask delete-tool <index>` | P3 |

#### マスク操作

| Luaコマンド | 提案CLIコマンド | 優先度 |
|------------|----------------|--------|
| `develop.addToCurrentMask` | `lr develop mask add <tool>` | P2 |
| `develop.intersectWithCurrentMask` | `lr develop mask intersect <tool>` | P2 |
| `develop.subtractFromCurrentMask` | `lr develop mask subtract <tool>` | P2 |
| `develop.invertMask` | `lr develop mask invert` | P2 |

#### リセット系

| Luaコマンド | 提案CLIコマンド | 優先度 |
|------------|----------------|--------|
| `develop.resetGradient` | `lr develop reset-gradient` | P3 |
| `develop.resetCircularGradient` | `lr develop reset-circular` | P3 |
| `develop.resetBrushing` | `lr develop reset-brush` | P3 |
| `develop.resetMasking` | `lr develop reset-masking` | P3 |

#### マスク作成ヘルパー

| Luaコマンド | 提案CLIコマンド | 優先度 |
|------------|----------------|--------|
| `develop.createGraduatedFilter` | `lr develop filter graduated [--settings '{}']` | P2 |
| `develop.createRadialFilter` | `lr develop filter radial [--settings '{}']` | P2 |
| `develop.createAdjustmentBrush` | `lr develop filter brush [--settings '{}']` | P2 |
| `develop.createAISelectionMask` | `lr develop mask ai-select [--settings '{}']` | P2 |
| `develop.createRangeMask` | `lr develop mask range [--type lum|color] [--settings '{}']` | P2 |
| `develop.createComplexMask` | `lr develop mask complex --steps '[...]'` | P3 |

#### ローカル調整

| Luaコマンド | 提案CLIコマンド | 優先度 |
|------------|----------------|--------|
| `develop.activateMaskingMode` | `lr develop mask activate` | P2 |
| `develop.getLocalValue` | `lr develop local get <param>` | P2 |
| `develop.setLocalValue` | `lr develop local set <param> <value>` | P2 |
| `develop.applyLocalSettings` | `lr develop local apply --settings '{...}'` | P2 |
| `develop.getAvailableLocalParameters` | `lr develop local params` | P2 |
| `develop.createMaskWithLocalAdjustments` | `lr develop local create-mask --tool <t> --settings '{}'` | P3 |

#### イントロスペクション・デバッグ

| Luaコマンド | 提案CLIコマンド | 優先度 |
|------------|----------------|--------|
| `develop.dumpLrDevelopController` | `lr develop debug dump` | P3 |
| `develop.discoverGradientParameters` | `lr develop debug gradient-params` | P3 |
| `develop.monitorParameterChanges` | `lr develop debug monitor` | P3 |
| `develop.probeAllDevelopParameters` | `lr develop debug probe` | P3 |

### 4.2 Catalog系 未公開コマンド（5コマンド）

| Luaコマンド | 提案CLIコマンド | 優先度 |
|------------|----------------|--------|
| `catalog.setSelectedPhotos` | `lr catalog select <photo_id> [photo_id2 ...]` | **P1** |
| `catalog.findPhotoByPath` | `lr catalog find-by-path <path>` | **P1** |
| `catalog.findPhotos` | `lr catalog find [--rating N] [--flag pick\|reject] ...` | **P1** |
| `catalog.getCollections` | `lr catalog collections` | **P1** |
| `catalog.getKeywords` | `lr catalog keywords` | **P1** |
| `catalog.getFolders` | `lr catalog folders [--recursive]` | **P1** |
| `catalog.batchGetFormattedMetadata` | `lr catalog batch-metadata <ids...> [--keys k1,k2]` | P2 |

### 4.3 Preview系 未公開コマンド（2コマンド）

| Luaコマンド | 提案CLIコマンド | 優先度 |
|------------|----------------|--------|
| `preview.getPreviewInfo` | `lr preview info <photo_id>` | P2 |
| `preview.getPreviewChunk` | (内部使用のみ、CLI公開不要) | - |

---

## 5. Gap C: CLIに公開済みだがLuaバックエンドが無い

以下のCLIコマンドは存在するが、対応するLuaハンドラが `PluginInit.lua` に登録されていない。

| CLIコマンド | Bridge Command | 状態 | 優先度 |
|------------|---------------|------|--------|
| `lr catalog set-rating` | `catalog.setRating` | Luaハンドラ未登録 | **P0** |
| `lr catalog add-keywords` | `catalog.addKeywords` | Luaハンドラ未登録 | **P0** |

### 原因分析

`PluginInit.lua` の `registerApiCommands()` を確認すると、`CatalogModule` の登録コマンドに `catalog.setRating` と `catalog.addKeywords` が**含まれていない**。これらはCLI側で定義されているが、Lua側にハンドラ関数自体が存在しない。

### 解決策

#### `catalog.setRating` の実装

```lua
-- CatalogModule.lua に追加
function CatalogModule.setRating(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local photoId = params.photoId
    local rating = params.rating

    if not photoId then
        callback(ErrorUtils.createError("MISSING_PARAM", "photoId is required"))
        return
    end
    if not rating or rating < 0 or rating > 5 then
        callback(ErrorUtils.createError("INVALID_PARAM_VALUE",
            "rating must be between 0 and 5"))
        return
    end

    local catalog = LrApplication.activeCatalog()
    catalog:withWriteAccessDo("Set Rating", function()
        local photo = catalog:getPhotoByLocalId(tonumber(photoId))
        if not photo then
            error("Photo not found: " .. tostring(photoId))
        end
        photo:setRawMetadata("rating", rating)
    end, { timeout = 10 })

    callback(ErrorUtils.createSuccess({
        photoId = photoId,
        rating = rating,
        message = "Rating set successfully"
    }))
end
```

#### `catalog.addKeywords` の実装

```lua
-- CatalogModule.lua に追加
function CatalogModule.addKeywords(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local photoId = params.photoId
    local keywords = params.keywords

    if not photoId then
        callback(ErrorUtils.createError("MISSING_PARAM", "photoId is required"))
        return
    end
    if not keywords or type(keywords) ~= "table" or #keywords == 0 then
        callback(ErrorUtils.createError("INVALID_PARAM_VALUE",
            "keywords must be a non-empty array"))
        return
    end

    local catalog = LrApplication.activeCatalog()
    catalog:withWriteAccessDo("Add Keywords", function()
        local photo = catalog:getPhotoByLocalId(tonumber(photoId))
        if not photo then
            error("Photo not found: " .. tostring(photoId))
        end

        local addedKeywords = {}
        for _, kwName in ipairs(keywords) do
            local keyword = catalog:createKeyword(kwName, {}, false, nil, true)
            if keyword then
                photo:addKeyword(keyword)
                table.insert(addedKeywords, kwName)
            end
        end

        callback(ErrorUtils.createSuccess({
            photoId = photoId,
            addedKeywords = addedKeywords,
            count = #addedKeywords,
            message = "Keywords added successfully"
        }))
    end, { timeout = 10 })
end
```

#### PluginInit.lua への登録追加

```lua
-- registerApiCommands() 内に追加
router:register("catalog.setRating", CatalogModule.setRating, "sync")
router:register("catalog.addKeywords", CatalogModule.addKeywords, "sync")
```

---

## 6. 優先度付きロードマップ

### P0 (Critical) — ユーザーが明示的に不足と述べた機能

| # | 機能 | Gap種別 | 作業内容 | 工数見積 |
|---|------|---------|----------|----------|
| P0-1 | フラグ読み取り（pickStatus） | A | `getPhotoMetadata`, `searchPhotos`, `getAllPhotos` のレスポンスに `pickStatus` 追加 | 0.5h |
| P0-2 | フラグ書き込み | A | `CatalogModule.setFlag` 新規実装 + CLI `set-flag` + ルーター登録 | 1h |
| P0-3 | フラグ条件検索 | A | `CatalogModule.findPhotos` を `LrCatalog:findPhotos` の `pick` 条件に対応 | 2h |
| P0-4 | `catalog.setRating` Lua実装 | C | `CatalogModule.setRating` 関数実装 + ルーター登録 | 0.5h |
| P0-5 | `catalog.addKeywords` Lua実装 | C | `CatalogModule.addKeywords` 関数実装 + ルーター登録 | 1h |

**P0 合計工数: 約5時間**

### P1 (High) — 日常ワークフローに不可欠

| # | 機能 | Gap種別 | 作業内容 | 工数見積 |
|---|------|---------|----------|----------|
| P1-1 | カラーラベル読み書き | A | Lua `setColorLabel`/`getColorLabel` + CLI | 1h |
| P1-2 | タイトル・キャプション設定 | A | Lua `setMetadata` (title, caption) + CLI | 1h |
| P1-3 | 写真ナビゲーション | A | Lua `nextPhoto`/`previousPhoto` (LrSelection) + CLI | 0.5h |
| P1-4 | プリセット適用 | A | Lua `applyDevelopPreset` + CLI | 1.5h |
| P1-5 | スナップショット作成 | A | Lua `createDevelopSnapshot` + CLI | 1h |
| P1-6 | 設定コピー&ペースト | A | Lua `copySettings`/`pasteSettings` + CLI | 1h |
| P1-7 | Catalog 未公開CLI（6コマンド） | B | CLI追加のみ (select, find-by-path, find, collections, keywords, folders) | 2h |
| P1-8 | Develop基本未公開CLI (getValue, applySettings, auto-wb, selectTool) | B | CLI追加のみ | 1.5h |
| P1-9 | コレクション作成 | A | Lua `createCollection` + CLI | 1h |
| P1-10 | キーワード削除 | A | Lua `removeKeyword` + CLI | 0.5h |
| P1-11 | バッチRawメタデータ取得 | A | Lua `batchGetRawMetadata` + CLI | 1h |
| P1-12 | キーワード作成 | A | Lua `createKeyword` + CLI | 0.5h |

**P1 合計工数: 約12.5時間**

### P2 (Medium) — 上級者向け・自動化に有用

| # | 機能 | Gap種別 | 作業内容 | 工数見積 |
|---|------|---------|----------|----------|
| P2-1 | 選択操作 (selectAll/None/Inverse) | A | Lua + CLI | 1h |
| P2-2 | レーティング増減 | A | Lua + CLI | 0.5h |
| P2-3 | 回転 (rotateLeft/Right) | A | Lua + CLI | 0.5h |
| P2-4 | 仮想コピー作成 | A | Lua + CLI | 1h |
| P2-5 | スナップショット管理 (delete/apply/list) | A | Lua + CLI | 1.5h |
| P2-6 | メタデータ読み取り強化 (width/height/uuid/lastEditTime等) | A | Lua修正 | 0.5h |
| P2-7 | ビューフィルター操作 | A | Lua + CLI | 1h |
| P2-8 | スマートプレビュー操作 | A | Lua + CLI | 1h |
| P2-9 | カラーラベルマッピング取得 | A | Lua + CLI | 0.5h |
| P2-10 | トーンカーブ CLI公開（6コマンド） | B | CLI追加のみ | 1.5h |
| P2-11 | マスキング CLI公開（~15コマンド） | B | CLI追加のみ | 3h |
| P2-12 | ローカル調整 CLI公開（~6コマンド） | B | CLI追加のみ | 1.5h |
| P2-13 | Preview info CLI公開 | B | CLI追加のみ | 0.5h |
| P2-14 | Develop リセット系（crop/transforms/spot等） | A | Lua + CLI | 1h |
| P2-15 | Photoshopで編集 | A | Lua + CLI | 0.5h |
| P2-16 | スマートコレクション・コレクションセット作成 | A | Lua + CLI | 1.5h |
| P2-17 | アクティブソース設定 | A | Lua + CLI | 0.5h |
| P2-18 | カタログから削除 (removeFromCatalog) | A | Lua + CLI | 0.5h |
| P2-19 | GPS座標・場所メタデータ書き込み | A | Lua + CLI | 1h |
| P2-20 | 著作権メタデータ書き込み | A | Lua + CLI | 0.5h |
| P2-21 | Develop: getRange CLI | B | CLI追加のみ | 0.5h |
| P2-22 | Develop: resetToDefault CLI | B | CLI追加のみ | 0.5h |
| P2-23 | Develop: processVersion CLI | B | CLI追加のみ | 0.5h |
| P2-24 | batch-metadata CLI | B | CLI追加のみ | 0.5h |

**P2 合計工数: 約20時間**

### P3 (Low) — ニッチ・将来対応

| # | 機能 | Gap種別 |
|---|------|---------|
| P3-1 | カラーラベル個別トグル (toggle*Label) | A |
| P3-2 | 選択拡張 (extendSelection) | A |
| P3-3 | 選択解除 (deselectActive/Others) | A |
| P3-4 | 作成者詳細メタデータ (住所・連絡先等) | A |
| P3-5 | アクセシビリティテキスト | A |
| P3-6 | Spot/Remove操作 | A |
| P3-7 | Point Color操作 | A |
| P3-8 | Lens Blur操作 | A |
| P3-9 | GenAI操作 | A |
| P3-10 | クリッピング表示 | A |
| P3-11 | カラーグレーディングビュー | A |
| P3-12 | エクスポートダイアログ | A |
| P3-13 | インポートUI起動 | A |
| P3-14 | Develop デバッグ系 CLI公開（4コマンド） | B |
| P3-15 | カラー操作 CLI公開（3コマンド） | B |
| P3-16 | マスクリセット系 CLI公開（4コマンド） | B |
| P3-17 | complexMask CLI公開 | B |
| P3-18 | createMaskWithLocalAdjustments CLI公開 | B |

**P3 合計工数: 約15時間（すべて実装する場合）**

---

## 7. CLIコマンド設計案

### 7.1 新規コマンドグループ追加

現在の4グループ (system, catalog, develop, preview) に加えて、以下のサブグループを提案:

```
lr
├── system          (既存)
├── catalog         (既存 + 拡張)
│   ├── get-selected, list, search, get-info, set-rating, add-keywords  (既存)
│   ├── select, find, find-by-path                                       (P1新規)
│   ├── collections, keywords, folders                                   (P1新規)
│   ├── set-flag, get-flag                                               (P0新規)
│   ├── set-color-label, set-title, set-caption                         (P1新規)
│   ├── remove-keyword, create-keyword, create-collection               (P1新規)
│   └── batch-metadata                                                   (P2新規)
├── develop         (既存 + 拡張)
│   ├── get-settings, set, auto-tone, reset                              (既存)
│   ├── get, apply, auto-wb, tool                                        (P1新規)
│   ├── preset, snapshot, copy-settings, paste-settings                  (P1新規)
│   ├── curve (サブグループ)                                              (P2新規)
│   ├── mask (サブグループ)                                               (P2新規)
│   ├── local (サブグループ)                                              (P2新規)
│   └── filter (サブグループ)                                             (P2新規)
├── preview         (既存 + 拡張)
│   ├── generate-current, generate, generate-batch                       (既存)
│   └── info                                                              (P2新規)
└── selection       (P1新規グループ)
    ├── next, previous                                                    (P1新規)
    ├── flag, unflag, reject                                              (P0新規)
    ├── select-all, select-none, select-inverse                          (P2新規)
    └── color-label                                                       (P1新規)
```

### 7.2 P0 コマンド詳細設計

#### `lr catalog set-flag`

```
Usage: lr catalog set-flag <photo_id> <flag>

Arguments:
  photo_id    写真のID
  flag        pick | reject | none

Options:
  -o, --output    出力形式 (text/json/table)

Example:
  lr catalog set-flag 12345 pick
  lr catalog set-flag 12345 reject
  lr catalog set-flag 12345 none
```

#### `lr catalog get-flag`

```
Usage: lr catalog get-flag <photo_id>

Arguments:
  photo_id    写真のID

Example:
  lr catalog get-flag 12345
  # Output: pick (1) / reject (-1) / none (0)
```

#### `lr catalog find` (拡張検索)

```
Usage: lr catalog find [OPTIONS]

Options:
  --flag TEXT          フラグ条件 (pick/reject/none)
  --rating INTEGER     レーティング条件 (0-5)
  --rating-op TEXT     レーティング比較演算子 (==, >=, <=, >, <)  [default: ==]
  --color-label TEXT   カラーラベル (red/yellow/green/blue/purple/none)
  --keyword TEXT       キーワード (複数指定可: --keyword a --keyword b)
  --folder TEXT        フォルダパス
  --collection TEXT    コレクション名
  --file-format TEXT   ファイル形式 (RAW/JPEG/TIFF/PNG/DNG/Video)
  --has-gps            GPS情報あり
  --has-adjustments    現像調整あり
  --camera TEXT        カメラ名
  --date-from TEXT     撮影日範囲（開始）
  --date-to TEXT       撮影日範囲（終了）
  --limit INTEGER      最大取得数 [default: 50]
  --offset INTEGER     オフセット [default: 0]
  -o, --output         出力形式

Example:
  lr catalog find --flag pick --rating 5
  lr catalog find --color-label red --has-adjustments
  lr catalog find --camera "Sony" --date-from "2026-01-01"
  lr -o json catalog find --flag pick --limit 100
```

### 7.3 P1 コマンド詳細設計

#### `lr selection` グループ

```
Usage: lr selection <command>

Commands:
  next            次の写真に移動
  previous        前の写真に移動
  flag            選択写真にPickフラグ設定
  reject          選択写真にRejectフラグ設定
  unflag          選択写真のフラグ解除
  color-label     選択写真のカラーラベル設定

Example:
  lr selection next
  lr selection flag
  lr selection reject
  lr selection color-label red
```

#### `lr catalog select`

```
Usage: lr catalog select <photo_id> [photo_id2 ...]

Arguments:
  photo_id    選択する写真のID（複数指定可）

Example:
  lr catalog select 12345
  lr catalog select 12345 67890 11111
```

#### `lr catalog set-title` / `set-caption`

```
Usage: lr catalog set-title <photo_id> <title>
Usage: lr catalog set-caption <photo_id> <caption>

Example:
  lr catalog set-title 12345 "Sunset at Beach"
  lr catalog set-caption 12345 "A beautiful sunset captured at Malibu Beach"
```

#### `lr develop preset`

```
Usage: lr develop preset <preset_name>

Arguments:
  preset_name    適用するプリセット名

Example:
  lr develop preset "Adobe Color"
  lr develop preset "Camera Vivid"
```

#### `lr develop snapshot`

```
Usage: lr develop snapshot <name>

Arguments:
  name    スナップショット名

Example:
  lr develop snapshot "Before color grading"
```

#### `lr develop auto-wb`

```
Usage: lr develop auto-wb

Example:
  lr develop auto-wb
```

#### `lr develop get`

```
Usage: lr develop get <parameter>

Arguments:
  parameter    取得するパラメータ名

Example:
  lr develop get Exposure
  lr develop get Temperature
```

#### `lr develop tool`

```
Usage: lr develop tool <tool_name>

Arguments:
  tool_name    ツール名 (loupe/crop/dust/redeye/gradient/circularGradient/localized/upright)

Example:
  lr develop tool crop
  lr develop tool loupe
```

---

## 8. 実装方針

### 8.1 フェーズ分け

#### Phase A: P0 修正（1日）
1. `CatalogModule.lua` に `pickStatus` 読み取り追加
2. `CatalogModule.lua` に `setRating`, `addKeywords` 実装
3. `CatalogModule.lua` に `setFlag`, `getFlag` 実装
4. `CatalogModule.lua` の `findPhotos` を `LrCatalog:findPhotos` の条件検索に対応
5. `PluginInit.lua` にルーター登録追加
6. CLI側: `set-flag`, `get-flag`, `find` コマンド追加
7. テスト作成・実行

#### Phase B: P1 CLI公開（2-3日）
1. 既存Luaコマンドの CLI公開（Gap B解消、コード追加のみ）
   - Catalog: select, find-by-path, collections, keywords, folders
   - Develop: get, apply, auto-wb, tool
2. `selection` コマンドグループ新設（LrSelection Luaモジュール新規作成）
3. LrPhoto メタデータ書き込み（title, caption, colorLabel）
4. プリセット・スナップショット・設定コピー機能
5. テスト作成・実行

#### Phase C: P2 拡張（1-2週間）
1. トーンカーブ、マスキング、ローカル調整の CLI公開
2. 選択操作、回転、仮想コピー
3. ビューフィルター、スマートプレビュー
4. 高度なメタデータ操作
5. テスト作成・実行

### 8.2 新規Luaモジュール

#### `SelectionModule.lua`（新規作成）

`LrSelection` のラッパーモジュール。以下の関数を提供:

- `flagAsPick(params, callback)` — 選択写真をPickに設定
- `flagAsReject(params, callback)` — 選択写真をRejectに設定
- `removeFlag(params, callback)` — フラグ解除
- `getFlag(params, callback)` — フラグ状態取得
- `setRating(params, callback)` — レーティング設定
- `getRating(params, callback)` — レーティング取得
- `setColorLabel(params, callback)` — カラーラベル設定
- `getColorLabel(params, callback)` — カラーラベル取得
- `nextPhoto(params, callback)` — 次の写真
- `previousPhoto(params, callback)` — 前の写真
- `selectAll(params, callback)` — 全選択
- `selectNone(params, callback)` — 全解除
- `selectInverse(params, callback)` — 選択反転

### 8.3 CLIコマンドのボイラープレート削減

現在の各CLIコマンドには大量のボイラープレートがある（bridge取得、async実行、エラーハンドリング、出力フォーマット）。P1以降の大量コマンド追加に備えて、ヘルパーデコレータを導入:

```python
# cli/helpers.py
import asyncio
import functools
import click
from cli.output import OutputFormatter


def bridge_command(bridge_cmd: str, timeout: float = 30.0):
    """CLIコマンドのボイラープレートを削減するデコレータ"""
    def decorator(func):
        @functools.wraps(func)
        @click.pass_context
        def wrapper(ctx, **kwargs):
            from lightroom_sdk.resilient_bridge import ResilientSocketBridge
            _timeout = ctx.obj.get("timeout", timeout) if ctx.obj else timeout
            fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

            # コマンド固有のパラメータ変換
            params = func(**kwargs)

            loop = asyncio.new_event_loop()
            try:
                async def _run():
                    bridge = ResilientSocketBridge()
                    try:
                        result = await bridge.send_command(
                            bridge_cmd, params or {}, timeout=_timeout
                        )
                        click.echo(OutputFormatter.format(
                            result.get("result", result), fmt
                        ))
                    except Exception as e:
                        click.echo(OutputFormatter.format_error(str(e)))
                    finally:
                        await bridge.disconnect()

                loop.run_until_complete(_run())
            finally:
                loop.close()
        return wrapper
    return decorator
```

使用例:

```python
@catalog.command("set-flag")
@click.argument("photo_id")
@click.argument("flag", type=click.Choice(["pick", "reject", "none"]))
@bridge_command("catalog.setFlag")
def set_flag(photo_id, flag):
    """Set photo flag (pick/reject/none)"""
    flag_map = {"pick": 1, "reject": -1, "none": 0}
    return {"photoId": photo_id, "flag": flag_map[flag]}
```

### 8.4 テスト戦略

各 Phase で TDD (Red-Green-Commit) ワークフローを維持:

1. **MockServer拡張**: 新規コマンドに対するモック応答を `MockLightroomServer` に追加
2. **単体テスト**: 各Lua関数のロジック（パラメータバリデーション、エラーケース）
3. **CLI統合テスト**: Click の `CliRunner` で新規コマンドをテスト
4. **エッジケース**: 存在しないphotoId、範囲外のrating、空のkeywords配列等

---

## 付録: 完全コマンドマッピング表

### 現在の状態（73 Luaコマンド vs 17 CLIコマンド）

| # | Lua Bridge Command | CLI Command | Gap |
|---|-------------------|-------------|-----|
| 1 | system.ping | `lr system ping` | - |
| 2 | system.status | `lr system status` | - |
| 3 | develop.getSettings | `lr develop get-settings` | - |
| 4 | develop.applySettings | - | **B** |
| 5 | develop.batchApplySettings | `lr develop set` (batch) | - |
| 6 | develop.getValue | - | **B** |
| 7 | develop.setValue | `lr develop set` (single) | - |
| 8 | develop.getRange | - | **B** |
| 9 | develop.resetToDefault | - | **B** |
| 10 | develop.setAutoTone | `lr develop auto-tone` | - |
| 11 | develop.setAutoWhiteBalance | - | **B** |
| 12 | develop.getProcessVersion | - | **B** |
| 13 | develop.setProcessVersion | - | **B** |
| 14 | develop.resetAllDevelopAdjustments | `lr develop reset` | - |
| 15 | develop.getCurvePoints | - | **B** |
| 16 | develop.setCurvePoints | - | **B** |
| 17 | develop.setCurveLinear | - | **B** |
| 18 | develop.setCurveSCurve | - | **B** |
| 19 | develop.addCurvePoint | - | **B** |
| 20 | develop.removeCurvePoint | - | **B** |
| 21 | develop.createGreenSwatch | - | **B** |
| 22 | develop.createCyanSwatch | - | **B** |
| 23 | develop.enhanceColors | - | **B** |
| 24 | develop.goToMasking | - | **B** |
| 25 | develop.toggleOverlay | - | **B** |
| 26 | develop.selectTool | - | **B** |
| 27 | develop.getAllMasks | - | **B** |
| 28 | develop.getSelectedMask | - | **B** |
| 29 | develop.createNewMask | - | **B** |
| 30 | develop.selectMask | - | **B** |
| 31 | develop.deleteMask | - | **B** |
| 32 | develop.getSelectedMaskTool | - | **B** |
| 33 | develop.selectMaskTool | - | **B** |
| 34 | develop.deleteMaskTool | - | **B** |
| 35 | develop.addToCurrentMask | - | **B** |
| 36 | develop.intersectWithCurrentMask | - | **B** |
| 37 | develop.subtractFromCurrentMask | - | **B** |
| 38 | develop.invertMask | - | **B** |
| 39 | develop.resetGradient | - | **B** |
| 40 | develop.resetCircularGradient | - | **B** |
| 41 | develop.resetBrushing | - | **B** |
| 42 | develop.resetMasking | - | **B** |
| 43 | develop.createGraduatedFilter | - | **B** |
| 44 | develop.createRadialFilter | - | **B** |
| 45 | develop.createAdjustmentBrush | - | **B** |
| 46 | develop.createAISelectionMask | - | **B** |
| 47 | develop.createRangeMask | - | **B** |
| 48 | develop.createComplexMask | - | **B** |
| 49 | develop.activateMaskingMode | - | **B** |
| 50 | develop.getLocalValue | - | **B** |
| 51 | develop.setLocalValue | - | **B** |
| 52 | develop.applyLocalSettings | - | **B** |
| 53 | develop.getAvailableLocalParameters | - | **B** |
| 54 | develop.createMaskWithLocalAdjustments | - | **B** |
| 55 | develop.dumpLrDevelopController | - | **B** |
| 56 | develop.discoverGradientParameters | - | **B** |
| 57 | develop.monitorParameterChanges | - | **B** |
| 58 | develop.probeAllDevelopParameters | - | **B** |
| 59 | catalog.searchPhotos | `lr catalog search` | - |
| 60 | catalog.getPhotoMetadata | `lr catalog get-info` | - |
| 61 | catalog.getSelectedPhotos | `lr catalog get-selected` | - |
| 62 | catalog.setSelectedPhotos | - | **B** |
| 63 | catalog.getAllPhotos | `lr catalog list` | - |
| 64 | catalog.findPhotoByPath | - | **B** |
| 65 | catalog.findPhotos | - | **B** |
| 66 | catalog.getCollections | - | **B** |
| 67 | catalog.getKeywords | - | **B** |
| 68 | catalog.getFolders | - | **B** |
| 69 | catalog.batchGetFormattedMetadata | - | **B** |
| 70 | preview.generatePreview | `lr preview generate` / `generate-current` | - |
| 71 | preview.generateBatchPreviews | `lr preview generate-batch` | - |
| 72 | preview.getPreviewInfo | - | **B** |
| 73 | preview.getPreviewChunk | (内部用) | - |
| - | catalog.setRating | `lr catalog set-rating` | **C** |
| - | catalog.addKeywords | `lr catalog add-keywords` | **C** |

### Gap集計

| Gap | 件数 | 対応方針 |
|-----|------|----------|
| カバー済み（Gap無し） | 17 | 対応不要 |
| **Gap A** (SDK→Lua未実装) | ~60+ | 新規Lua実装 + CLI |
| **Gap B** (Lua→CLI未公開) | 56 | CLI追加のみ |
| **Gap C** (CLI→Lua未実装) | 2 | Lua実装 + ルーター登録 |
| 内部用（CLI公開不要） | 1 | 対応不要 |

---

## 不確実な点・要確認事項

1. **LrCatalog:findPhotos の searchDesc 仕様**: SDK公式ドキュメントの `searchDesc` パラメータの正確な構文は、SDKバージョンによって異なる可能性がある。実機テストが必須。

2. **LrSelection のモジュール制約**: `LrSelection` は Library モジュールでのみ動作する可能性がある。Develop モジュールで呼び出した場合の動作を確認する必要がある。

3. **withWriteAccessDo のタイムアウト**: 大量のキーワード追加やフラグ操作でタイムアウトが発生する可能性。バッチ操作では適切なタイムアウト値を設定する必要がある。

4. **プリセット名の取得方法**: `applyDevelopPreset` にはプリセットオブジェクトが必要。利用可能なプリセット一覧を取得する方法（`LrApplication.developPresetFolders()` 等）の実装が必要。

5. **SDK バージョン互換性**: `pickStatus` の書き込み (v4.0+)、`removeFromCatalog` (v14.3+)、`altTextAccessibility` (v13.2+) など、SDKバージョン依存の機能がある。最小対応バージョンの決定が必要。
