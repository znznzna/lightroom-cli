# Lightroom SDK Full Coverage Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Lightroom SDK API カバー率を11%→100%に引き上げ、全SDK機能をCLIから利用可能にする
**Architecture:** Lua Module追加（SelectionModule等） + CatalogModule拡張 + CLI commands追加 + bridge_commandデコレータによるボイラープレート削減
**Tech Stack:** Python 3.10+, Click, Rich, pytest, Lua (Lightroom SDK)
---

## 参照ドキュメント

- Gap分析: `docs/plans/2026-03-04-sdk-gap-analysis.md`

## 原則

- **DRY**: bridge_commandデコレータでCLIボイラープレートを削減
- **YAGNI**: 各Phaseで必要な機能のみ実装
- **TDD**: Red→Green→Commitサイクル
- **頻繁なコミット**: 各タスク完了時にコミット

---

## Phase A (P0): Critical — フラグ・条件検索・Gap C修正

### Task 1: CatalogModule.lua に pickStatus 読み取りを追加

**Files:**
- Modify: `lightroom-plugin/CatalogModule.lua`

**Step 1: 失敗するテストを書く**

Create: `tests/integration/test_cli_catalog_flag.py`

```python
import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.commands.catalog.get_bridge")
def test_catalog_get_info_includes_pick_status(mock_get_bridge, runner):
    """lr catalog get-info がpickStatusを含むメタデータを返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1",
        "success": True,
        "result": {
            "id": 12345,
            "filename": "IMG_001.jpg",
            "rating": 3,
            "pickStatus": 1,
            "colorLabel": "red",
        },
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "get-info", "12345"])
    assert result.exit_code == 0
    assert "pickStatus" in result.output
```

**Step 2: 失敗を確認**

Run: `python -m pytest tests/integration/test_cli_catalog_flag.py::test_catalog_get_info_includes_pick_status -v`
Expected: PASS (テスト自体はmockを使うので通るが、Lua側の修正がメイン)

**Step 3: 最小限の実装**

`lightroom-plugin/CatalogModule.lua` の `getPhotoMetadata` 関数内の metadata テーブルに追加:

```lua
-- 既存の colorLabel = photo:getRawMetadata("colorNameForLabel") の直後に追加
pickStatus = photo:getRawMetadata("pickStatus"),
```

`searchPhotos` 関数内の photoData 取得部分に追加:

```lua
-- 既存の photoData.isVirtualCopy 取得の直後に追加
photoData.pickStatus = photo:getRawMetadata("pickStatus")
```

`getAllPhotos` 関数内のpagedPhotos構築に追加:

```lua
-- 既存の rating = photo:getRawMetadata("rating") の直後に追加
pickStatus = photo:getRawMetadata("pickStatus"),
```

`getSelectedPhotos` 関数内のphotoData取得に追加:

```lua
-- 既存の photoData.isVirtualCopy 取得の直後に追加
photoData.pickStatus = photo:getRawMetadata("pickStatus")
```

**Step 4: 通過を確認**

Run: `python -m pytest tests/integration/test_cli_catalog_flag.py -v`
Expected: PASS

**Step 5: コミット**

```
git add lightroom-plugin/CatalogModule.lua tests/integration/test_cli_catalog_flag.py
git commit -m "feat: add pickStatus to catalog metadata responses (P0-1)"
```

---

### Task 2: CatalogModule.lua に setRating / addKeywords を実装 (Gap C修正)

**Files:**
- Modify: `lightroom-plugin/CatalogModule.lua`
- Modify: `lightroom-plugin/PluginInit.lua`

**Step 1: 失敗するテストを書く**

既存の `tests/integration/test_cli_catalog.py` にテスト追加:

```python
@patch("cli.commands.catalog.get_bridge")
def test_catalog_set_rating_sends_correct_command(mock_get_bridge, runner):
    """lr catalog set-rating がcatalog.setRatingコマンドを送信する（Luaバックエンド実装後に動作）"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "10",
        "success": True,
        "result": {"photoId": "123", "rating": 4, "message": "Rating set successfully"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "set-rating", "123", "4"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.setRating", {"photoId": "123", "rating": 4}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_add_keywords_sends_correct_command(mock_get_bridge, runner):
    """lr catalog add-keywords がcatalog.addKeywordsコマンドを送信する（Luaバックエンド実装後に動作）"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "11",
        "success": True,
        "result": {"photoId": "123", "addedKeywords": ["landscape", "sunset"], "count": 2},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "add-keywords", "123", "landscape", "sunset"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.addKeywords",
        {"photoId": "123", "keywords": ["landscape", "sunset"]},
        timeout=30.0,
    )
```

**Step 2: 失敗を確認**

Run: `python -m pytest tests/integration/test_cli_catalog.py::test_catalog_set_rating_sends_correct_command tests/integration/test_cli_catalog.py::test_catalog_add_keywords_sends_correct_command -v`
Expected: PASS (CLIコマンドは既存。Luaバックエンド実装がメイン)

**Step 3: 最小限の実装**

`lightroom-plugin/CatalogModule.lua` の `return CatalogModule` の直前に追加:

```lua
-- Set photo rating (Gap C fix)
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
    local writeSuccess, writeError = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Set Rating", function()
            local photo = catalog:getPhotoByLocalId(tonumber(photoId))
            if not photo then
                error("Photo not found: " .. tostring(photoId))
            end
            photo:setRawMetadata("rating", rating)
        end, { timeout = 10 })
    end)

    if writeSuccess then
        callback(ErrorUtils.createSuccess({
            photoId = photoId,
            rating = rating,
            message = "Rating set successfully"
        }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED",
            "Failed to set rating: " .. tostring(writeError)))
    end
end

-- Add keywords to photo (Gap C fix)
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
    local addedKeywords = {}

    local writeSuccess, writeError = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Add Keywords", function()
            local photo = catalog:getPhotoByLocalId(tonumber(photoId))
            if not photo then
                error("Photo not found: " .. tostring(photoId))
            end

            for _, kwName in ipairs(keywords) do
                local keyword = catalog:createKeyword(kwName, {}, false, nil, true)
                if keyword then
                    photo:addKeyword(keyword)
                    table.insert(addedKeywords, kwName)
                end
            end
        end, { timeout = 10 })
    end)

    if writeSuccess then
        callback(ErrorUtils.createSuccess({
            photoId = photoId,
            addedKeywords = addedKeywords,
            count = #addedKeywords,
            message = "Keywords added successfully"
        }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED",
            "Failed to add keywords: " .. tostring(writeError)))
    end
end
```

`lightroom-plugin/PluginInit.lua` の catalog コマンド登録セクション（`router:register("catalog.batchGetFormattedMetadata"` の直後）に追加:

```lua
router:register("catalog.setRating", CatalogModule.setRating, "sync")
router:register("catalog.addKeywords", CatalogModule.addKeywords, "sync")
```

**Step 4: 通過を確認**

Run: `python -m pytest tests/integration/test_cli_catalog.py -v`
Expected: PASS

**Step 5: コミット**

```
git add lightroom-plugin/CatalogModule.lua lightroom-plugin/PluginInit.lua tests/integration/test_cli_catalog.py
git commit -m "feat: implement setRating/addKeywords Lua handlers (Gap C fix, P0-4/P0-5)"
```

---

### Task 3: CatalogModule.lua に setFlag / getFlag を実装

**Files:**
- Modify: `lightroom-plugin/CatalogModule.lua`
- Modify: `lightroom-plugin/PluginInit.lua`
- Modify: `cli/commands/catalog.py`

**Step 1: 失敗するテストを書く**

`tests/integration/test_cli_catalog_flag.py` に追加:

```python
@patch("cli.commands.catalog.get_bridge")
def test_catalog_set_flag_pick(mock_get_bridge, runner):
    """lr catalog set-flag <id> pick がフラグを設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "2",
        "success": True,
        "result": {"photoId": "12345", "flag": 1, "message": "Flag set successfully"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "set-flag", "12345", "pick"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.setFlag", {"photoId": "12345", "flag": 1}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_set_flag_reject(mock_get_bridge, runner):
    """lr catalog set-flag <id> reject がRejectフラグを設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "3",
        "success": True,
        "result": {"photoId": "12345", "flag": -1, "message": "Flag set successfully"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "set-flag", "12345", "reject"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.setFlag", {"photoId": "12345", "flag": -1}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_set_flag_none(mock_get_bridge, runner):
    """lr catalog set-flag <id> none がフラグを解除する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "4",
        "success": True,
        "result": {"photoId": "12345", "flag": 0, "message": "Flag set successfully"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "set-flag", "12345", "none"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.setFlag", {"photoId": "12345", "flag": 0}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_get_flag(mock_get_bridge, runner):
    """lr catalog get-flag <id> がフラグ状態を取得する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "5",
        "success": True,
        "result": {"photoId": "12345", "pickStatus": 1, "label": "pick"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "get-flag", "12345"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.getFlag", {"photoId": "12345"}, timeout=30.0
    )
```

**Step 2: 失敗を確認**

Run: `python -m pytest tests/integration/test_cli_catalog_flag.py -v`
Expected: FAIL (set-flag, get-flag コマンドが未定義)

**Step 3: 最小限の実装**

**3a. Lua側** — `lightroom-plugin/CatalogModule.lua` の `return CatalogModule` 直前に追加:

```lua
-- Set photo flag (pick/reject/none)
function CatalogModule.setFlag(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local photoId = params.photoId
    local flag = params.flag  -- 1=pick, -1=reject, 0=none

    if not photoId then
        callback(ErrorUtils.createError("MISSING_PARAM", "photoId is required"))
        return
    end
    if flag ~= 1 and flag ~= -1 and flag ~= 0 then
        callback(ErrorUtils.createError("INVALID_PARAM_VALUE",
            "flag must be 1 (pick), -1 (reject), or 0 (none)"))
        return
    end

    local catalog = LrApplication.activeCatalog()
    local writeSuccess, writeError = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Set Flag", function()
            local photo = catalog:getPhotoByLocalId(tonumber(photoId))
            if not photo then
                error("Photo not found: " .. tostring(photoId))
            end
            photo:setRawMetadata("pickStatus", flag)
        end, { timeout = 10 })
    end)

    if writeSuccess then
        callback(ErrorUtils.createSuccess({
            photoId = photoId,
            flag = flag,
            message = "Flag set successfully"
        }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED",
            "Failed to set flag: " .. tostring(writeError)))
    end
end

-- Get photo flag status
function CatalogModule.getFlag(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local photoId = params.photoId

    if not photoId then
        callback(ErrorUtils.createError("MISSING_PARAM", "photoId is required"))
        return
    end

    local catalog = LrApplication.activeCatalog()
    catalog:withReadAccessDo(function()
        local photo = catalog:getPhotoByLocalId(tonumber(photoId))
        if not photo then
            callback(ErrorUtils.createError("PHOTO_NOT_FOUND",
                "Photo not found: " .. tostring(photoId)))
            return
        end

        local pickStatus = photo:getRawMetadata("pickStatus") or 0
        local label = "none"
        if pickStatus == 1 then label = "pick"
        elseif pickStatus == -1 then label = "reject"
        end

        callback(ErrorUtils.createSuccess({
            photoId = photoId,
            pickStatus = pickStatus,
            label = label
        }))
    end)
end
```

**3b. PluginInit.lua** — catalog登録セクションに追加:

```lua
router:register("catalog.setFlag", CatalogModule.setFlag, "sync")
router:register("catalog.getFlag", CatalogModule.getFlag, "sync")
```

**3c. CLI側** — `cli/commands/catalog.py` の末尾に追加:

```python
@catalog.command("set-flag")
@click.argument("photo_id")
@click.argument("flag", type=click.Choice(["pick", "reject", "none"]))
@click.pass_context
def set_flag(ctx, photo_id, flag):
    """Set photo flag (pick/reject/none)"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
    flag_map = {"pick": 1, "reject": -1, "none": 0}

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.setFlag",
                {"photoId": photo_id, "flag": flag_map[flag]},
                timeout=timeout,
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@catalog.command("get-flag")
@click.argument("photo_id")
@click.pass_context
def get_flag(ctx, photo_id):
    """Get photo flag status"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.getFlag", {"photoId": photo_id}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())
```

**Step 4: 通過を確認**

Run: `python -m pytest tests/integration/test_cli_catalog_flag.py -v`
Expected: PASS

**Step 5: コミット**

```
git add lightroom-plugin/CatalogModule.lua lightroom-plugin/PluginInit.lua cli/commands/catalog.py tests/integration/test_cli_catalog_flag.py
git commit -m "feat: implement setFlag/getFlag for photo pick status (P0-2)"
```

---

### Task 4: CatalogModule.lua の findPhotos を条件検索に対応 + CLI find コマンド

**Files:**
- Modify: `lightroom-plugin/CatalogModule.lua`
- Modify: `cli/commands/catalog.py`

**Step 1: 失敗するテストを書く**

`tests/integration/test_cli_catalog_flag.py` に追加:

```python
@patch("cli.commands.catalog.get_bridge")
def test_catalog_find_with_flag_option(mock_get_bridge, runner):
    """lr catalog find --flag pick がフラグ条件検索を実行する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "6",
        "success": True,
        "result": {
            "photos": [{"id": 1, "filename": "IMG_001.jpg", "pickStatus": 1}],
            "total": 1,
            "returned": 1,
        },
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "find", "--flag", "pick"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once()
    call_args = mock_bridge.send_command.call_args
    assert call_args[0][0] == "catalog.findPhotos"
    assert call_args[0][1]["searchDesc"]["flag"] == "pick"


@patch("cli.commands.catalog.get_bridge")
def test_catalog_find_with_rating_option(mock_get_bridge, runner):
    """lr catalog find --rating 5 がレーティング条件検索を実行する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "7",
        "success": True,
        "result": {"photos": [], "total": 0, "returned": 0},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "find", "--rating", "5"])
    assert result.exit_code == 0
    call_args = mock_bridge.send_command.call_args
    assert call_args[0][1]["searchDesc"]["rating"] == 5


@patch("cli.commands.catalog.get_bridge")
def test_catalog_find_with_multiple_options(mock_get_bridge, runner):
    """lr catalog find --flag pick --rating 5 --color-label red が複合条件検索を実行する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "8",
        "success": True,
        "result": {"photos": [], "total": 0, "returned": 0},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(
        cli, ["catalog", "find", "--flag", "pick", "--rating", "5", "--color-label", "red"]
    )
    assert result.exit_code == 0
    call_args = mock_bridge.send_command.call_args
    search_desc = call_args[0][1]["searchDesc"]
    assert search_desc["flag"] == "pick"
    assert search_desc["rating"] == 5
    assert search_desc["colorLabel"] == "red"
```

**Step 2: 失敗を確認**

Run: `python -m pytest tests/integration/test_cli_catalog_flag.py::test_catalog_find_with_flag_option -v`
Expected: FAIL (find コマンド未定義)

**Step 3: 最小限の実装**

**3a. CLI側** — `cli/commands/catalog.py` の末尾に追加:

```python
@catalog.command("find")
@click.option("--flag", type=click.Choice(["pick", "reject", "none"]), help="Flag condition")
@click.option("--rating", type=int, help="Rating (0-5)")
@click.option("--rating-op", default="==", help="Rating comparison operator (==, >=, <=, >, <)")
@click.option("--color-label", help="Color label (red/yellow/green/blue/purple/none)")
@click.option("--keyword", multiple=True, help="Keyword (can be specified multiple times)")
@click.option("--has-adjustments", is_flag=True, help="Has develop adjustments")
@click.option("--camera", help="Camera model name")
@click.option("--limit", default=50, type=int, help="Max results")
@click.option("--offset", default=0, type=int, help="Offset for pagination")
@click.pass_context
def find_photos(ctx, flag, rating, rating_op, color_label, keyword, has_adjustments, camera, limit, offset):
    """Find photos by structured criteria"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    search_desc = {}
    if flag:
        search_desc["flag"] = flag
    if rating is not None:
        search_desc["rating"] = rating
        search_desc["ratingOp"] = rating_op
    if color_label:
        search_desc["colorLabel"] = color_label
    if keyword:
        search_desc["keywords"] = list(keyword)
    if has_adjustments:
        search_desc["hasAdjustments"] = True
    if camera:
        search_desc["camera"] = camera

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.findPhotos",
                {"searchDesc": search_desc, "limit": limit, "offset": offset},
                timeout=timeout,
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())
```

**3b. Lua側** — `lightroom-plugin/CatalogModule.lua` の既存 `findPhotos` 関数を以下で完全置換:

```lua
-- Advanced photo search with criteria
function CatalogModule.findPhotos(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local searchDesc = params.searchDesc or {}
    local limit = params.limit or 100
    local offset = params.offset or 0

    logger:debug("Finding photos with search criteria")

    local catalog = LrApplication.activeCatalog()

    catalog:withReadAccessDo(function()
        local allPhotos = catalog:getAllPhotos()

        if not allPhotos or #allPhotos == 0 then
            callback({
                result = {
                    photos = {},
                    total = 0,
                    returned = 0
                }
            })
            return
        end

        -- Apply filters
        local filtered = {}
        for _, photo in ipairs(allPhotos) do
            local match = true

            -- Flag filter
            if searchDesc.flag then
                local pickStatus = photo:getRawMetadata("pickStatus") or 0
                if searchDesc.flag == "pick" and pickStatus ~= 1 then match = false end
                if searchDesc.flag == "reject" and pickStatus ~= -1 then match = false end
                if searchDesc.flag == "none" and pickStatus ~= 0 then match = false end
            end

            -- Rating filter
            if match and searchDesc.rating then
                local rating = photo:getRawMetadata("rating") or 0
                local op = searchDesc.ratingOp or "=="
                if op == "==" and rating ~= searchDesc.rating then match = false end
                if op == ">=" and rating < searchDesc.rating then match = false end
                if op == "<=" and rating > searchDesc.rating then match = false end
                if op == ">" and rating <= searchDesc.rating then match = false end
                if op == "<" and rating >= searchDesc.rating then match = false end
            end

            -- Color label filter
            if match and searchDesc.colorLabel then
                local label = photo:getRawMetadata("colorNameForLabel") or ""
                if searchDesc.colorLabel == "none" then
                    if label ~= "" and label ~= "none" then match = false end
                else
                    if label ~= searchDesc.colorLabel then match = false end
                end
            end

            -- Camera filter
            if match and searchDesc.camera then
                local camera = photo:getFormattedMetadata("cameraModel") or ""
                if not string.find(string.lower(camera), string.lower(searchDesc.camera)) then
                    match = false
                end
            end

            if match then
                table.insert(filtered, photo)
            end
        end

        -- Apply pagination
        local total = #filtered
        local startIndex = offset + 1
        local endIndex = math.min(offset + limit, total)
        local resultPhotos = {}

        for i = startIndex, endIndex do
            local photo = filtered[i]
            table.insert(resultPhotos, {
                id = photo.localIdentifier,
                filename = photo:getFormattedMetadata("fileName"),
                path = photo:getRawMetadata("path"),
                captureTime = photo:getFormattedMetadata("dateTimeOriginal"),
                fileFormat = photo:getRawMetadata("fileFormat"),
                rating = photo:getRawMetadata("rating"),
                pickStatus = photo:getRawMetadata("pickStatus"),
                colorLabel = photo:getRawMetadata("colorNameForLabel")
            })
        end

        callback({
            result = {
                photos = resultPhotos,
                total = total,
                returned = #resultPhotos,
                offset = offset,
                limit = limit
            }
        })
    end)
end
```

**Step 4: 通過を確認**

Run: `python -m pytest tests/integration/test_cli_catalog_flag.py -v`
Expected: PASS

**Step 5: コミット**

```
git add lightroom-plugin/CatalogModule.lua cli/commands/catalog.py tests/integration/test_cli_catalog_flag.py
git commit -m "feat: implement structured photo search with flag/rating/color filters (P0-3)"
```

---

### Task 5: Phase A 全テスト通過確認

**Files:**
- (変更なし)

**Step 1: 全テスト実行**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

**Step 2: コミット（必要な場合のみ）**

修正が必要な場合は修正してコミット。

---

## Phase B (P1): High — 日常ワークフロー必須機能

### Task 6: bridge_command デコレータ導入

**Files:**
- Create: `cli/helpers.py`

**Step 1: 失敗するテストを書く**

Create: `tests/test_bridge_command.py`

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from click.testing import CliRunner
import click

# bridge_command のインポートテスト
def test_bridge_command_import():
    """bridge_command デコレータがインポートできる"""
    from cli.helpers import bridge_command
    assert callable(bridge_command)


def test_bridge_command_creates_click_command():
    """bridge_command が正しいClickコマンドを生成する"""
    from cli.helpers import bridge_command

    @click.group()
    @click.pass_context
    def test_group(ctx):
        ctx.ensure_object(dict)
        ctx.obj["output"] = "text"
        ctx.obj["timeout"] = 30.0

    @test_group.command("test-cmd")
    @click.argument("name")
    @bridge_command("test.command")
    def test_cmd(name):
        return {"name": name}

    runner = CliRunner()
    with patch("cli.helpers.get_bridge") as mock_get_bridge:
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {
            "id": "1", "success": True, "result": {"ok": True}
        }
        mock_get_bridge.return_value = mock_bridge

        result = runner.invoke(test_group, ["test-cmd", "hello"])
        assert result.exit_code == 0
        mock_bridge.send_command.assert_called_once_with(
            "test.command", {"name": "hello"}, timeout=30.0
        )
```

**Step 2: 失敗を確認**

Run: `python -m pytest tests/test_bridge_command.py -v`
Expected: FAIL (cli.helpers モジュール未作成)

**Step 3: 最小限の実装**

Create: `cli/helpers.py`

```python
import asyncio
import functools
import click
from cli.output import OutputFormatter


def get_bridge():
    """ResilientSocketBridgeインスタンスを取得（遅延import）"""
    from lightroom_sdk.resilient_bridge import ResilientSocketBridge
    return ResilientSocketBridge()


def run_async(coro):
    """CLIからasync関数を実行するヘルパー"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def bridge_command(bridge_cmd: str, timeout: float = 30.0):
    """CLIコマンドのボイラープレートを削減するデコレータ。

    デコレートされた関数はパラメータのdictを返す。
    デコレータがbridge通信・出力フォーマット・エラーハンドリングを担当する。

    Usage:
        @some_group.command("cmd-name")
        @click.argument("photo_id")
        @bridge_command("catalog.someCommand")
        def cmd_name(photo_id):
            return {"photoId": photo_id}
    """
    def decorator(func):
        @functools.wraps(func)
        @click.pass_context
        def wrapper(ctx, **kwargs):
            _timeout = ctx.obj.get("timeout", timeout) if ctx.obj else timeout
            fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

            params = func(**kwargs)
            if params is None:
                params = {}

            loop = asyncio.new_event_loop()
            try:
                async def _run():
                    bridge = get_bridge()
                    try:
                        result = await bridge.send_command(
                            bridge_cmd, params, timeout=_timeout
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

**Step 4: 通過を確認**

Run: `python -m pytest tests/test_bridge_command.py -v`
Expected: PASS

**Step 5: コミット**

```
git add cli/helpers.py tests/test_bridge_command.py
git commit -m "feat: add bridge_command decorator for CLI boilerplate reduction (P1)"
```

---

### Task 7: SelectionModule.lua 新規作成 + PluginInit登録

**Files:**
- Create: `lightroom-plugin/SelectionModule.lua`
- Modify: `lightroom-plugin/PluginInit.lua`

**Step 1: 失敗するテストを書く**

Create: `tests/integration/test_cli_selection.py`

```python
import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.commands.selection.get_bridge")
def test_selection_flag(mock_get_bridge, runner):
    """lr selection flag が選択写真にPickフラグを設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"message": "Flag set to pick"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["selection", "flag"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "selection.flagAsPick", {}, timeout=30.0
    )


@patch("cli.commands.selection.get_bridge")
def test_selection_reject(mock_get_bridge, runner):
    """lr selection reject が選択写真にRejectフラグを設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "2", "success": True,
        "result": {"message": "Flag set to reject"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["selection", "reject"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "selection.flagAsReject", {}, timeout=30.0
    )


@patch("cli.commands.selection.get_bridge")
def test_selection_unflag(mock_get_bridge, runner):
    """lr selection unflag がフラグを解除する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "3", "success": True,
        "result": {"message": "Flag removed"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["selection", "unflag"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "selection.removeFlag", {}, timeout=30.0
    )


@patch("cli.commands.selection.get_bridge")
def test_selection_next(mock_get_bridge, runner):
    """lr selection next が次の写真へ移動する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "4", "success": True,
        "result": {"message": "Moved to next photo"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["selection", "next"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "selection.nextPhoto", {}, timeout=30.0
    )


@patch("cli.commands.selection.get_bridge")
def test_selection_previous(mock_get_bridge, runner):
    """lr selection previous が前の写真へ移動する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "5", "success": True,
        "result": {"message": "Moved to previous photo"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["selection", "previous"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "selection.previousPhoto", {}, timeout=30.0
    )


@patch("cli.commands.selection.get_bridge")
def test_selection_color_label(mock_get_bridge, runner):
    """lr selection color-label red がカラーラベルを設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "6", "success": True,
        "result": {"message": "Color label set to red"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["selection", "color-label", "red"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "selection.setColorLabel", {"label": "red"}, timeout=30.0
    )
```

**Step 2: 失敗を確認**

Run: `python -m pytest tests/integration/test_cli_selection.py -v`
Expected: FAIL (selectionモジュール未作成)

**Step 3: 最小限の実装**

**3a. Lua側** — Create: `lightroom-plugin/SelectionModule.lua`

```lua
-- SelectionModule.lua
-- LrSelection API wrapper

local LrSelection = nil
local LrTasks = import 'LrTasks'

local function getErrorUtils()
    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.ErrorUtils then
        return _G.LightroomPythonBridge.ErrorUtils
    end
    return {
        safeCall = function(func, ...) return LrTasks.pcall(func, ...) end,
        createError = function(code, message) return { error = { code = code or "ERROR", message = message or "An error occurred" } } end,
        createSuccess = function(result) return { result = result or {} } end,
    }
end

local ErrorUtils = getErrorUtils()

local function ensureLrSelection()
    if not LrSelection then
        LrSelection = import 'LrSelection'
    end
end

local function getLogger()
    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.logger then
        return _G.LightroomPythonBridge.logger
    end
    local LrLogger = import 'LrLogger'
    local logger = LrLogger('SelectionModule')
    logger:enable("logfile")
    return logger
end

local SelectionModule = {}

function SelectionModule.flagAsPick(params, callback)
    ensureLrSelection()
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.flagAsPick()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Flag set to pick" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to flag as pick: " .. tostring(err)))
    end
end

function SelectionModule.flagAsReject(params, callback)
    ensureLrSelection()
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.flagAsReject()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Flag set to reject" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to flag as reject: " .. tostring(err)))
    end
end

function SelectionModule.removeFlag(params, callback)
    ensureLrSelection()
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.removeFlag()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Flag removed" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to remove flag: " .. tostring(err)))
    end
end

function SelectionModule.getFlag(params, callback)
    ensureLrSelection()
    local success, result = ErrorUtils.safeCall(function()
        return LrSelection.getFlag()
    end)
    if success then
        local label = "none"
        if result == 1 then label = "pick"
        elseif result == -1 then label = "reject" end
        callback(ErrorUtils.createSuccess({ pickStatus = result, label = label }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to get flag: " .. tostring(result)))
    end
end

function SelectionModule.setRating(params, callback)
    ensureLrSelection()
    local rating = params.rating
    if not rating or rating < 0 or rating > 5 then
        callback(ErrorUtils.createError("INVALID_PARAM_VALUE", "rating must be between 0 and 5"))
        return
    end
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.setRating(rating)
    end)
    if success then
        callback(ErrorUtils.createSuccess({ rating = rating, message = "Rating set" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to set rating: " .. tostring(err)))
    end
end

function SelectionModule.getRating(params, callback)
    ensureLrSelection()
    local success, result = ErrorUtils.safeCall(function()
        return LrSelection.getRating()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ rating = result }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to get rating: " .. tostring(result)))
    end
end

function SelectionModule.setColorLabel(params, callback)
    ensureLrSelection()
    local label = params.label
    if not label then
        callback(ErrorUtils.createError("MISSING_PARAM", "label is required"))
        return
    end
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.setColorLabel(label)
    end)
    if success then
        callback(ErrorUtils.createSuccess({ label = label, message = "Color label set to " .. label }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to set color label: " .. tostring(err)))
    end
end

function SelectionModule.getColorLabel(params, callback)
    ensureLrSelection()
    local success, result = ErrorUtils.safeCall(function()
        return LrSelection.getColorLabel()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ label = result }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to get color label: " .. tostring(result)))
    end
end

function SelectionModule.nextPhoto(params, callback)
    ensureLrSelection()
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.nextPhoto()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Moved to next photo" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to move to next photo: " .. tostring(err)))
    end
end

function SelectionModule.previousPhoto(params, callback)
    ensureLrSelection()
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.previousPhoto()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Moved to previous photo" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to move to previous photo: " .. tostring(err)))
    end
end

function SelectionModule.selectAll(params, callback)
    ensureLrSelection()
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.selectAll()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "All photos selected" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to select all: " .. tostring(err)))
    end
end

function SelectionModule.selectNone(params, callback)
    ensureLrSelection()
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.selectNone()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Selection cleared" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to clear selection: " .. tostring(err)))
    end
end

function SelectionModule.selectInverse(params, callback)
    ensureLrSelection()
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.selectInverse()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Selection inverted" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to invert selection: " .. tostring(err)))
    end
end

function SelectionModule.increaseRating(params, callback)
    ensureLrSelection()
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.increaseRating()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Rating increased" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to increase rating: " .. tostring(err)))
    end
end

function SelectionModule.decreaseRating(params, callback)
    ensureLrSelection()
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.decreaseRating()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Rating decreased" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to decrease rating: " .. tostring(err)))
    end
end

return SelectionModule
```

**3b. PluginInit.lua** — `loadPhase4Modules()` に SelectionModule ロード追加:

```lua
-- Load SelectionModule (loadPhase4Modules内、PreviewModule の後に追加)
success, SelectionModule = LrTasks.pcall(require, 'SelectionModule')
if success then
    _G.LightroomPythonBridge.SelectionModule = SelectionModule
    Logger:info("SelectionModule loaded successfully")
else
    Logger:error("Failed to load SelectionModule: " .. tostring(SelectionModule))
end
```

`registerApiCommands()` に SelectionModule 登録追加:

```lua
-- Selection module commands
local SelectionModule = _G.LightroomPythonBridge.SelectionModule
if SelectionModule then
    Logger:info("Registering selection commands...")
    router:register("selection.flagAsPick", SelectionModule.flagAsPick, "sync")
    router:register("selection.flagAsReject", SelectionModule.flagAsReject, "sync")
    router:register("selection.removeFlag", SelectionModule.removeFlag, "sync")
    router:register("selection.getFlag", SelectionModule.getFlag, "sync")
    router:register("selection.setRating", SelectionModule.setRating, "sync")
    router:register("selection.getRating", SelectionModule.getRating, "sync")
    router:register("selection.setColorLabel", SelectionModule.setColorLabel, "sync")
    router:register("selection.getColorLabel", SelectionModule.getColorLabel, "sync")
    router:register("selection.nextPhoto", SelectionModule.nextPhoto, "sync")
    router:register("selection.previousPhoto", SelectionModule.previousPhoto, "sync")
    router:register("selection.selectAll", SelectionModule.selectAll, "sync")
    router:register("selection.selectNone", SelectionModule.selectNone, "sync")
    router:register("selection.selectInverse", SelectionModule.selectInverse, "sync")
    router:register("selection.increaseRating", SelectionModule.increaseRating, "sync")
    router:register("selection.decreaseRating", SelectionModule.decreaseRating, "sync")
end
```

**3c. CLI側** — Create: `cli/commands/selection.py`

```python
import asyncio
import click
from cli.output import OutputFormatter


def get_bridge():
    """ResilientSocketBridgeインスタンスを取得（遅延import）"""
    from lightroom_sdk.resilient_bridge import ResilientSocketBridge
    return ResilientSocketBridge()


def run_async(coro):
    """CLIからasync関数を実行するヘルパー"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@click.group()
def selection():
    """Selection commands (flag, unflag, reject, next, previous, color-label)"""
    pass


@selection.command("flag")
@click.pass_context
def flag_as_pick(ctx):
    """Flag selected photo(s) as Pick"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("selection.flagAsPick", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@selection.command("reject")
@click.pass_context
def flag_as_reject(ctx):
    """Flag selected photo(s) as Reject"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("selection.flagAsReject", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@selection.command("unflag")
@click.pass_context
def remove_flag(ctx):
    """Remove flag from selected photo(s)"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("selection.removeFlag", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@selection.command("next")
@click.pass_context
def next_photo(ctx):
    """Move to next photo"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("selection.nextPhoto", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@selection.command("previous")
@click.pass_context
def previous_photo(ctx):
    """Move to previous photo"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("selection.previousPhoto", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@selection.command("color-label")
@click.argument("label", type=click.Choice(["red", "yellow", "green", "blue", "purple", "none"]))
@click.pass_context
def set_color_label(ctx, label):
    """Set color label for selected photo(s)"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "selection.setColorLabel", {"label": label}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())
```

**3d. main.py** — selectionグループ登録:

`cli/main.py` に追加:

```python
from cli.commands.selection import selection
cli.add_command(selection)
```

**Step 4: 通過を確認**

Run: `python -m pytest tests/integration/test_cli_selection.py -v`
Expected: PASS

**Step 5: コミット**

```
git add lightroom-plugin/SelectionModule.lua cli/commands/selection.py cli/main.py lightroom-plugin/PluginInit.lua tests/integration/test_cli_selection.py
git commit -m "feat: add SelectionModule with flag/navigation/color-label commands (P1)"
```

---

### Task 8: Catalog 未公開CLI公開 (Gap B: select, find-by-path, collections, keywords, folders)

**Files:**
- Modify: `cli/commands/catalog.py`

**Step 1: 失敗するテストを書く**

Create: `tests/integration/test_cli_catalog_extended.py`

```python
import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.commands.catalog.get_bridge")
def test_catalog_select(mock_get_bridge, runner):
    """lr catalog select がphotoIdでの写真選択を実行する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"selected": 2},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "select", "123", "456"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.setSelectedPhotos", {"photoIds": ["123", "456"]}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_find_by_path(mock_get_bridge, runner):
    """lr catalog find-by-path がパスで写真を検索する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "2", "success": True,
        "result": {"id": 123, "filename": "IMG_001.jpg"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "find-by-path", "/photos/IMG_001.jpg"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.findPhotoByPath", {"path": "/photos/IMG_001.jpg"}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_collections(mock_get_bridge, runner):
    """lr catalog collections がコレクション一覧を返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "3", "success": True,
        "result": {"collections": [], "count": 0},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "collections"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.getCollections", {}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_keywords(mock_get_bridge, runner):
    """lr catalog keywords がキーワード一覧を返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "4", "success": True,
        "result": {"keywords": [], "count": 0},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "keywords"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.getKeywords", {}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_folders(mock_get_bridge, runner):
    """lr catalog folders がフォルダ一覧を返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "5", "success": True,
        "result": {"folders": [], "count": 0},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "folders"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.getFolders", {"includeSubfolders": False}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_folders_recursive(mock_get_bridge, runner):
    """lr catalog folders --recursive がサブフォルダ付きで返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "6", "success": True,
        "result": {"folders": [], "count": 0, "includeSubfolders": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "folders", "--recursive"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.getFolders", {"includeSubfolders": True}, timeout=30.0
    )
```

**Step 2: 失敗を確認**

Run: `python -m pytest tests/integration/test_cli_catalog_extended.py -v`
Expected: FAIL (select, find-by-path, collections, keywords, folders コマンド未定義)

**Step 3: 最小限の実装**

`cli/commands/catalog.py` の末尾に追加:

```python
@catalog.command("select")
@click.argument("photo_ids", nargs=-1, required=True)
@click.pass_context
def select_photos(ctx, photo_ids):
    """Select photos by ID"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.setSelectedPhotos", {"photoIds": list(photo_ids)}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@catalog.command("find-by-path")
@click.argument("path")
@click.pass_context
def find_by_path(ctx, path):
    """Find photo by file path"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.findPhotoByPath", {"path": path}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@catalog.command("collections")
@click.pass_context
def collections(ctx):
    """List collections in catalog"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.getCollections", {}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@catalog.command("keywords")
@click.pass_context
def keywords(ctx):
    """List keywords in catalog"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.getKeywords", {}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@catalog.command("folders")
@click.option("--recursive", is_flag=True, help="Include subfolders")
@click.pass_context
def folders(ctx, recursive):
    """List folders in catalog"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.getFolders", {"includeSubfolders": recursive}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())
```

**Step 4: 通過を確認**

Run: `python -m pytest tests/integration/test_cli_catalog_extended.py -v`
Expected: PASS

**Step 5: コミット**

```
git add cli/commands/catalog.py tests/integration/test_cli_catalog_extended.py
git commit -m "feat: expose catalog Gap B commands as CLI (select, find-by-path, collections, keywords, folders)"
```

---

### Task 9: Develop 未公開CLI公開 (Gap B: get, apply, auto-wb, tool)

**Files:**
- Modify: `cli/commands/develop.py`

**Step 1: 失敗するテストを書く**

`tests/integration/test_cli_develop.py` に追加:

```python
@patch("cli.commands.develop.get_bridge")
def test_develop_get_value(mock_get_bridge, runner):
    """lr develop get Exposure が単一パラメータ値を取得する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "5", "success": True,
        "result": {"parameter": "Exposure", "value": 0.5},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "get", "Exposure"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.getValue", {"parameter": "Exposure"}, timeout=30.0
    )


@patch("cli.commands.develop.get_bridge")
def test_develop_apply(mock_get_bridge, runner):
    """lr develop apply がJSON設定を適用する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "6", "success": True,
        "result": {"applied": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "apply", "--settings", '{"Exposure": 1.0}'])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.applySettings", {"settings": {"Exposure": 1.0}}, timeout=30.0
    )


@patch("cli.commands.develop.get_bridge")
def test_develop_auto_wb(mock_get_bridge, runner):
    """lr develop auto-wb がオートホワイトバランスを適用する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "7", "success": True,
        "result": {"applied": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "auto-wb"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.setAutoWhiteBalance", {}, timeout=30.0
    )


@patch("cli.commands.develop.get_bridge")
def test_develop_tool(mock_get_bridge, runner):
    """lr develop tool crop がツールを選択する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "8", "success": True,
        "result": {"tool": "crop"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "tool", "crop"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.selectTool", {"tool": "crop"}, timeout=30.0
    )
```

**Step 2: 失敗を確認**

Run: `python -m pytest tests/integration/test_cli_develop.py::test_develop_get_value -v`
Expected: FAIL

**Step 3: 最小限の実装**

`cli/commands/develop.py` の末尾に追加:

```python
@develop.command("get")
@click.argument("parameter")
@click.pass_context
def get_value(ctx, parameter):
    """Get a single develop parameter value"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "develop.getValue", {"parameter": parameter}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@develop.command("apply")
@click.option("--settings", required=True, help="JSON string of settings to apply")
@click.pass_context
def apply_settings(ctx, settings):
    """Apply develop settings from JSON"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    import json
    try:
        parsed = json.loads(settings)
    except json.JSONDecodeError as e:
        click.echo(OutputFormatter.format_error(f"Invalid JSON: {e}"))
        return

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "develop.applySettings", {"settings": parsed}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@develop.command("auto-wb")
@click.pass_context
def auto_wb(ctx):
    """Apply auto white balance"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "develop.setAutoWhiteBalance", {}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@develop.command("tool")
@click.argument("tool_name")
@click.pass_context
def select_tool(ctx, tool_name):
    """Select a develop tool (loupe/crop/dust/redeye/gradient/circularGradient/localized/upright)"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "develop.selectTool", {"tool": tool_name}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())
```

**Step 4: 通過を確認**

Run: `python -m pytest tests/integration/test_cli_develop.py -v`
Expected: PASS

**Step 5: コミット**

```
git add cli/commands/develop.py tests/integration/test_cli_develop.py
git commit -m "feat: expose develop Gap B commands as CLI (get, apply, auto-wb, tool)"
```

---

### Task 10: メタデータ書き込み CLI (set-title, set-caption, set-color-label) + Lua実装

**Files:**
- Modify: `lightroom-plugin/CatalogModule.lua`
- Modify: `lightroom-plugin/PluginInit.lua`
- Modify: `cli/commands/catalog.py`

**Step 1: 失敗するテストを書く**

`tests/integration/test_cli_catalog_extended.py` に追加:

```python
@patch("cli.commands.catalog.get_bridge")
def test_catalog_set_title(mock_get_bridge, runner):
    """lr catalog set-title がタイトルを設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "10", "success": True,
        "result": {"photoId": "123", "title": "Sunset"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "set-title", "123", "Sunset"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.setTitle", {"photoId": "123", "title": "Sunset"}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_set_caption(mock_get_bridge, runner):
    """lr catalog set-caption がキャプションを設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "11", "success": True,
        "result": {"photoId": "123", "caption": "A beautiful sunset"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "set-caption", "123", "A beautiful sunset"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.setCaption", {"photoId": "123", "caption": "A beautiful sunset"}, timeout=30.0
    )


@patch("cli.commands.catalog.get_bridge")
def test_catalog_set_color_label(mock_get_bridge, runner):
    """lr catalog set-color-label がカラーラベルを設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "12", "success": True,
        "result": {"photoId": "123", "colorLabel": "red"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "set-color-label", "123", "red"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.setColorLabel", {"photoId": "123", "label": "red"}, timeout=30.0
    )
```

**Step 2: 失敗を確認**

Run: `python -m pytest tests/integration/test_cli_catalog_extended.py::test_catalog_set_title -v`
Expected: FAIL

**Step 3: 最小限の実装**

**3a. Lua側** — `lightroom-plugin/CatalogModule.lua` に追加:

```lua
-- Set photo title
function CatalogModule.setTitle(params, callback)
    ensureLrModules()
    local photoId = params.photoId
    local title = params.title

    if not photoId then
        callback(ErrorUtils.createError("MISSING_PARAM", "photoId is required"))
        return
    end
    if not title then
        callback(ErrorUtils.createError("MISSING_PARAM", "title is required"))
        return
    end

    local catalog = LrApplication.activeCatalog()
    local writeSuccess, writeError = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Set Title", function()
            local photo = catalog:getPhotoByLocalId(tonumber(photoId))
            if not photo then error("Photo not found: " .. tostring(photoId)) end
            photo:setRawMetadata("title", title)
        end, { timeout = 10 })
    end)

    if writeSuccess then
        callback(ErrorUtils.createSuccess({ photoId = photoId, title = title, message = "Title set successfully" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to set title: " .. tostring(writeError)))
    end
end

-- Set photo caption
function CatalogModule.setCaption(params, callback)
    ensureLrModules()
    local photoId = params.photoId
    local caption = params.caption

    if not photoId then
        callback(ErrorUtils.createError("MISSING_PARAM", "photoId is required"))
        return
    end
    if not caption then
        callback(ErrorUtils.createError("MISSING_PARAM", "caption is required"))
        return
    end

    local catalog = LrApplication.activeCatalog()
    local writeSuccess, writeError = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Set Caption", function()
            local photo = catalog:getPhotoByLocalId(tonumber(photoId))
            if not photo then error("Photo not found: " .. tostring(photoId)) end
            photo:setRawMetadata("caption", caption)
        end, { timeout = 10 })
    end)

    if writeSuccess then
        callback(ErrorUtils.createSuccess({ photoId = photoId, caption = caption, message = "Caption set successfully" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to set caption: " .. tostring(writeError)))
    end
end

-- Set photo color label (via LrPhoto)
function CatalogModule.setColorLabel(params, callback)
    ensureLrModules()
    local photoId = params.photoId
    local label = params.label

    if not photoId then
        callback(ErrorUtils.createError("MISSING_PARAM", "photoId is required"))
        return
    end
    if not label then
        callback(ErrorUtils.createError("MISSING_PARAM", "label is required"))
        return
    end

    local catalog = LrApplication.activeCatalog()
    local writeSuccess, writeError = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Set Color Label", function()
            local photo = catalog:getPhotoByLocalId(tonumber(photoId))
            if not photo then error("Photo not found: " .. tostring(photoId)) end
            photo:setRawMetadata("colorNameForLabel", label)
        end, { timeout = 10 })
    end)

    if writeSuccess then
        callback(ErrorUtils.createSuccess({ photoId = photoId, colorLabel = label, message = "Color label set successfully" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to set color label: " .. tostring(writeError)))
    end
end
```

**3b. PluginInit.lua** — catalog登録セクションに追加:

```lua
router:register("catalog.setTitle", CatalogModule.setTitle, "sync")
router:register("catalog.setCaption", CatalogModule.setCaption, "sync")
router:register("catalog.setColorLabel", CatalogModule.setColorLabel, "sync")
```

**3c. CLI側** — `cli/commands/catalog.py` に追加:

```python
@catalog.command("set-title")
@click.argument("photo_id")
@click.argument("title")
@click.pass_context
def set_title(ctx, photo_id, title):
    """Set photo title"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.setTitle", {"photoId": photo_id, "title": title}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@catalog.command("set-caption")
@click.argument("photo_id")
@click.argument("caption")
@click.pass_context
def set_caption(ctx, photo_id, caption):
    """Set photo caption"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.setCaption", {"photoId": photo_id, "caption": caption}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@catalog.command("set-color-label")
@click.argument("photo_id")
@click.argument("label", type=click.Choice(["red", "yellow", "green", "blue", "purple", "none"]))
@click.pass_context
def set_color_label(ctx, photo_id, label):
    """Set photo color label"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.setColorLabel", {"photoId": photo_id, "label": label}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())
```

**Step 4: 通過を確認**

Run: `python -m pytest tests/integration/test_cli_catalog_extended.py -v`
Expected: PASS

**Step 5: コミット**

```
git add lightroom-plugin/CatalogModule.lua lightroom-plugin/PluginInit.lua cli/commands/catalog.py tests/integration/test_cli_catalog_extended.py
git commit -m "feat: add metadata write commands (set-title, set-caption, set-color-label) (P1)"
```

---

### Task 11: プリセット適用・スナップショット・設定コピー (Gap A Lua + CLI)

**Files:**
- Modify: `lightroom-plugin/CatalogModule.lua`
- Modify: `lightroom-plugin/PluginInit.lua`
- Modify: `cli/commands/develop.py`

**Step 1: 失敗するテストを書く**

`tests/integration/test_cli_develop.py` に追加:

```python
@patch("cli.commands.develop.get_bridge")
def test_develop_preset(mock_get_bridge, runner):
    """lr develop preset がプリセット適用コマンドを送信する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "9", "success": True,
        "result": {"preset": "Adobe Color", "applied": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "preset", "Adobe Color"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.applyDevelopPreset", {"presetName": "Adobe Color"}, timeout=30.0
    )


@patch("cli.commands.develop.get_bridge")
def test_develop_snapshot(mock_get_bridge, runner):
    """lr develop snapshot がスナップショット作成コマンドを送信する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "10", "success": True,
        "result": {"name": "Before grading", "created": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "snapshot", "Before grading"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.createDevelopSnapshot", {"name": "Before grading"}, timeout=30.0
    )


@patch("cli.commands.develop.get_bridge")
def test_develop_copy_settings(mock_get_bridge, runner):
    """lr develop copy-settings が設定コピーコマンドを送信する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "11", "success": True,
        "result": {"copied": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "copy-settings"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.copySettings", {}, timeout=30.0
    )


@patch("cli.commands.develop.get_bridge")
def test_develop_paste_settings(mock_get_bridge, runner):
    """lr develop paste-settings が設定ペーストコマンドを送信する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "12", "success": True,
        "result": {"pasted": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "paste-settings"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "catalog.pasteSettings", {}, timeout=30.0
    )
```

**Step 2: 失敗を確認**

Run: `python -m pytest tests/integration/test_cli_develop.py::test_develop_preset -v`
Expected: FAIL

**Step 3: 最小限の実装**

**3a. Lua側** — `lightroom-plugin/CatalogModule.lua` に追加:

```lua
-- Apply develop preset to current photo
function CatalogModule.applyDevelopPreset(params, callback)
    ensureLrModules()
    local presetName = params.presetName
    if not presetName then
        callback(ErrorUtils.createError("MISSING_PARAM", "presetName is required"))
        return
    end

    local LrDevelopController = import 'LrDevelopController'
    -- Find preset by name
    local presetFolders = LrApplication.developPresetFolders()
    local targetPreset = nil

    for _, folder in ipairs(presetFolders) do
        for _, preset in ipairs(folder:getDevelopPresets()) do
            if preset:getName() == presetName then
                targetPreset = preset
                break
            end
        end
        if targetPreset then break end
    end

    if not targetPreset then
        callback(ErrorUtils.createError("PHOTO_NOT_FOUND", "Preset not found: " .. presetName))
        return
    end

    local catalog = LrApplication.activeCatalog()
    local photo = catalog:getTargetPhoto()
    if not photo then
        callback(ErrorUtils.createError("PHOTO_NOT_FOUND", "No photo selected"))
        return
    end

    local writeSuccess, writeError = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Apply Preset", function()
            photo:applyDevelopPreset(targetPreset)
        end, { timeout = 10 })
    end)

    if writeSuccess then
        callback(ErrorUtils.createSuccess({ preset = presetName, applied = true, message = "Preset applied" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to apply preset: " .. tostring(writeError)))
    end
end

-- Create develop snapshot for current photo
function CatalogModule.createDevelopSnapshot(params, callback)
    ensureLrModules()
    local name = params.name
    if not name then
        callback(ErrorUtils.createError("MISSING_PARAM", "name is required"))
        return
    end

    local catalog = LrApplication.activeCatalog()
    local photo = catalog:getTargetPhoto()
    if not photo then
        callback(ErrorUtils.createError("PHOTO_NOT_FOUND", "No photo selected"))
        return
    end

    local writeSuccess, writeError = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Create Snapshot", function()
            photo:createDevelopSnapshot(name)
        end, { timeout = 10 })
    end)

    if writeSuccess then
        callback(ErrorUtils.createSuccess({ name = name, created = true, message = "Snapshot created" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to create snapshot: " .. tostring(writeError)))
    end
end

-- Copy develop settings from current photo
function CatalogModule.copySettings(params, callback)
    ensureLrModules()
    local catalog = LrApplication.activeCatalog()
    local photo = catalog:getTargetPhoto()
    if not photo then
        callback(ErrorUtils.createError("PHOTO_NOT_FOUND", "No photo selected"))
        return
    end

    local success, err = ErrorUtils.safeCall(function()
        photo:copySettings()
    end)

    if success then
        callback(ErrorUtils.createSuccess({ copied = true, message = "Settings copied" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to copy settings: " .. tostring(err)))
    end
end

-- Paste develop settings to current photo
function CatalogModule.pasteSettings(params, callback)
    ensureLrModules()
    local catalog = LrApplication.activeCatalog()
    local photo = catalog:getTargetPhoto()
    if not photo then
        callback(ErrorUtils.createError("PHOTO_NOT_FOUND", "No photo selected"))
        return
    end

    local writeSuccess, writeError = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Paste Settings", function()
            photo:pasteSettings()
        end, { timeout = 10 })
    end)

    if writeSuccess then
        callback(ErrorUtils.createSuccess({ pasted = true, message = "Settings pasted" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to paste settings: " .. tostring(writeError)))
    end
end
```

**3b. PluginInit.lua** に追加:

```lua
router:register("catalog.applyDevelopPreset", CatalogModule.applyDevelopPreset, "sync")
router:register("catalog.createDevelopSnapshot", CatalogModule.createDevelopSnapshot, "sync")
router:register("catalog.copySettings", CatalogModule.copySettings, "sync")
router:register("catalog.pasteSettings", CatalogModule.pasteSettings, "sync")
```

**3c. CLI側** — `cli/commands/develop.py` に追加:

```python
@develop.command("preset")
@click.argument("preset_name")
@click.pass_context
def apply_preset(ctx, preset_name):
    """Apply a develop preset by name"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.applyDevelopPreset", {"presetName": preset_name}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@develop.command("snapshot")
@click.argument("name")
@click.pass_context
def create_snapshot(ctx, name):
    """Create a develop snapshot"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.createDevelopSnapshot", {"name": name}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@develop.command("copy-settings")
@click.pass_context
def copy_settings(ctx):
    """Copy develop settings from current photo"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.copySettings", {}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())


@develop.command("paste-settings")
@click.pass_context
def paste_settings(ctx):
    """Paste develop settings to current photo"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "catalog.pasteSettings", {}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())
```

**Step 4: 通過を確認**

Run: `python -m pytest tests/integration/test_cli_develop.py -v`
Expected: PASS

**Step 5: コミット**

```
git add lightroom-plugin/CatalogModule.lua lightroom-plugin/PluginInit.lua cli/commands/develop.py tests/integration/test_cli_develop.py
git commit -m "feat: add preset/snapshot/copy-paste settings commands (P1)"
```

---

### Task 12: Phase B 全テスト通過確認

**Files:**
- (変更なし)

**Step 1: 全テスト実行**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

**Step 2: コミット（必要な場合のみ）**

---

## Phase C (P2): Medium — 上級者向け

### Task 13: トーンカーブ CLI公開 (Gap B: 6コマンド一括)

**Files:**
- Modify: `cli/commands/develop.py`

**Step 1: 失敗するテストを書く**

Create: `tests/integration/test_cli_develop_curve.py`

```python
import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.commands.develop.get_bridge")
def test_develop_curve_get(mock_get_bridge, runner):
    """lr develop curve get がカーブポイントを取得する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"points": [[0, 0], [128, 128], [255, 255]]},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "curve", "get"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once()
```

同パターンで以下も追加:
- `test_develop_curve_set`: `lr develop curve set --points '[[0,0],[128,140],[255,255]]'` -> `develop.setCurvePoints`
- `test_develop_curve_linear`: `lr develop curve linear` -> `develop.setCurveLinear`
- `test_develop_curve_s_curve`: `lr develop curve s-curve` -> `develop.setCurveSCurve`
- `test_develop_curve_add_point`: `lr develop curve add-point 128 140` -> `develop.addCurvePoint`
- `test_develop_curve_remove_point`: `lr develop curve remove-point 1` -> `develop.removeCurvePoint`

**Step 2: 失敗を確認**

Run: `python -m pytest tests/integration/test_cli_develop_curve.py -v`
Expected: FAIL

**Step 3: 最小限の実装**

`cli/commands/develop.py` に `curve` サブグループを追加:

```python
@develop.group()
def curve():
    """Tone curve commands"""
    pass


@curve.command("get")
@click.option("--channel", default="RGB", help="Channel (RGB/Red/Green/Blue)")
@click.pass_context
def curve_get(ctx, channel):
    """Get tone curve points"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "develop.getCurvePoints", {"channel": channel}, timeout=timeout
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())
```

同パターンで `curve set`, `curve linear`, `curve s-curve`, `curve add-point`, `curve remove-point` を追加。各コマンドは対応するbridge commandを呼ぶのみ。

**Step 4: 通過を確認**

Run: `python -m pytest tests/integration/test_cli_develop_curve.py -v`
Expected: PASS

**Step 5: コミット**

```
git add cli/commands/develop.py tests/integration/test_cli_develop_curve.py
git commit -m "feat: expose tone curve CLI commands (6 commands, Gap B, P2)"
```

---

### Task 14: マスキング CLI公開 (Gap B: ~15コマンド一括)

**Files:**
- Modify: `cli/commands/develop.py`

**Step 1: 失敗するテストを書く**

Create: `tests/integration/test_cli_develop_mask.py`

パターンテスト1件を完全に記述:

```python
import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.commands.develop.get_bridge")
def test_develop_mask_list(mock_get_bridge, runner):
    """lr develop mask list が全マスク一覧を返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"masks": []},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "mask", "list"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.getAllMasks", {}, timeout=30.0
    )
```

同パターンで以下も追加:
- `mask selected` -> `develop.getSelectedMask`
- `mask create` -> `develop.createNewMask`
- `mask select <index>` -> `develop.selectMask`
- `mask delete <index>` -> `develop.deleteMask`
- `mask tool-info` -> `develop.getSelectedMaskTool`
- `mask select-tool <index>` -> `develop.selectMaskTool`
- `mask delete-tool <index>` -> `develop.deleteMaskTool`
- `mask add <tool>` -> `develop.addToCurrentMask`
- `mask intersect <tool>` -> `develop.intersectWithCurrentMask`
- `mask subtract <tool>` -> `develop.subtractFromCurrentMask`
- `mask invert` -> `develop.invertMask`
- `mask go-to` -> `develop.goToMasking`
- `mask toggle-overlay` -> `develop.toggleOverlay`
- `mask activate` -> `develop.activateMaskingMode`

**Step 2: 失敗を確認**

Run: `python -m pytest tests/integration/test_cli_develop_mask.py -v`
Expected: FAIL

**Step 3: 最小限の実装**

`cli/commands/develop.py` に `mask` サブグループを追加:

```python
@develop.group()
def mask():
    """Masking commands"""
    pass
```

各コマンドは同一パターン（引数なしまたはindex/tool引数 + bridge command呼び出し）。上記テストリスト15コマンド分を一括実装。

**Step 4: 通過を確認**

Run: `python -m pytest tests/integration/test_cli_develop_mask.py -v`
Expected: PASS

**Step 5: コミット**

```
git add cli/commands/develop.py tests/integration/test_cli_develop_mask.py
git commit -m "feat: expose masking CLI commands (~15 commands, Gap B, P2)"
```

---

### Task 15: ローカル調整 CLI公開 (Gap B: ~6コマンド一括)

**Files:**
- Modify: `cli/commands/develop.py`

**Step 1: 失敗するテストを書く**

Create: `tests/integration/test_cli_develop_local.py`

パターンテスト:

```python
import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.commands.develop.get_bridge")
def test_develop_local_get(mock_get_bridge, runner):
    """lr develop local get <param> がローカル調整値を取得する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"parameter": "Exposure", "value": 0.5},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "local", "get", "Exposure"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.getLocalValue", {"parameter": "Exposure"}, timeout=30.0
    )
```

同パターンで以下も追加:
- `local set <param> <value>` -> `develop.setLocalValue`
- `local apply --settings '{...}'` -> `develop.applyLocalSettings`
- `local params` -> `develop.getAvailableLocalParameters`

**Step 2-5: 上記Task 13-14と同パターン**

コミット:
```
git commit -m "feat: expose local adjustment CLI commands (~6 commands, Gap B, P2)"
```

---

### Task 16: フィルター作成 CLI公開 (Gap B: graduated, radial, brush, ai-select, range)

**Files:**
- Modify: `cli/commands/develop.py`

同パターンで `filter` サブグループを追加:
- `filter graduated` -> `develop.createGraduatedFilter`
- `filter radial` -> `develop.createRadialFilter`
- `filter brush` -> `develop.createAdjustmentBrush`
- `filter ai-select` -> `develop.createAISelectionMask`
- `filter range` -> `develop.createRangeMask`

コミット:
```
git commit -m "feat: expose filter creation CLI commands (5 commands, Gap B, P2)"
```

---

### Task 17: 選択操作 CLI (P2 Gap A: selectAll/None/Inverse)

**Files:**
- Modify: `cli/commands/selection.py`

`tests/integration/test_cli_selection.py` に追加:

```python
@patch("cli.commands.selection.get_bridge")
def test_selection_select_all(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "7", "success": True, "result": {"message": "All selected"}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["selection", "select-all"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("selection.selectAll", {}, timeout=30.0)
```

同パターンで `select-none`, `select-inverse` も追加。

CLI側:

```python
@selection.command("select-all")
@click.pass_context
def select_all(ctx):
    """Select all photos"""
    # 標準パターン: bridge.send_command("selection.selectAll", {})

@selection.command("select-none")
# ...

@selection.command("select-inverse")
# ...
```

コミット:
```
git commit -m "feat: add selection select-all/none/inverse commands (P2)"
```

---

### Task 18: Develop追加 Gap B CLI一括公開 (getRange, resetToDefault, processVersion, resetParam)

**Files:**
- Modify: `cli/commands/develop.py`

追加コマンド:
- `lr develop range <param>` -> `develop.getRange`
- `lr develop reset-param <param>` -> `develop.resetToDefault`
- `lr develop process-version` -> `develop.getProcessVersion`
- `lr develop set-process-version <version>` -> `develop.setProcessVersion`

コミット:
```
git commit -m "feat: expose develop range/reset-param/process-version CLI (Gap B, P2)"
```

---

### Task 19: Preview info CLI公開 (Gap B)

**Files:**
- Modify: `cli/commands/preview.py`

追加:
- `lr preview info <photo_id>` -> `preview.getPreviewInfo`

コミット:
```
git commit -m "feat: expose preview info CLI (Gap B, P2)"
```

---

### Task 20: レーティング増減・回転・仮想コピー (Gap A Lua + CLI)

**Files:**
- Modify: `lightroom-plugin/CatalogModule.lua` (rotateLeft/Right, createVirtualCopy)
- Modify: `lightroom-plugin/PluginInit.lua`
- Modify: `cli/commands/selection.py` (increase-rating, decrease-rating)
- Modify: `cli/commands/catalog.py` (rotate-left, rotate-right, create-virtual-copy)

Lua実装パターン:

```lua
function CatalogModule.rotateLeft(params, callback)
    ensureLrModules()
    local catalog = LrApplication.activeCatalog()
    local photo = catalog:getTargetPhoto()
    if not photo then
        callback(ErrorUtils.createError("PHOTO_NOT_FOUND", "No photo selected"))
        return
    end
    local success, err = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Rotate Left", function()
            photo:rotateLeft()
        end, { timeout = 10 })
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Rotated left" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", tostring(err)))
    end
end
```

同パターンで rotateRight, createVirtualCopy を追加。

Selection CLI に increase-rating, decrease-rating を追加（SelectionModule にLua実装済み）。

コミット:
```
git commit -m "feat: add rating adjust/rotate/virtual-copy commands (P2)"
```

---

### Task 21: batch-metadata CLI公開 (Gap B)

**Files:**
- Modify: `cli/commands/catalog.py`

```python
@catalog.command("batch-metadata")
@click.argument("photo_ids", nargs=-1, required=True)
@click.option("--keys", default="fileName,dateTimeOriginal,rating", help="Comma-separated metadata keys")
@click.pass_context
def batch_metadata(ctx, photo_ids, keys):
    """Get formatted metadata for multiple photos"""
    # bridge.send_command("catalog.batchGetFormattedMetadata", {"photoIds": list(photo_ids), "keys": keys.split(",")})
```

コミット:
```
git commit -m "feat: expose batch-metadata CLI (Gap B, P2)"
```

---

### Task 22: Phase C 全テスト通過確認

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

---

## Phase D (P3): Low — ニッチ機能

### Task 23: カラーラベルトグル CLI (Gap A: 5コマンド一括)

**Files:**
- Modify: `lightroom-plugin/SelectionModule.lua` (toggleBlueLabel等 5関数追加)
- Modify: `lightroom-plugin/PluginInit.lua`
- Modify: `cli/commands/selection.py`

Lua パターン:

```lua
function SelectionModule.toggleRedLabel(params, callback)
    ensureLrSelection()
    local success, err = ErrorUtils.safeCall(function()
        LrSelection.toggleRedLabel()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Red label toggled" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", tostring(err)))
    end
end
```

同パターンで toggleYellow/Green/Blue/Purple も追加。

CLI側: `selection toggle-label <color>` として1コマンドにまとめてもよい。

コミット:
```
git commit -m "feat: add color label toggle commands (P3)"
```

---

### Task 24: 選択拡張・選択解除 (Gap A)

**Files:**
- Modify: `lightroom-plugin/SelectionModule.lua`
- Modify: `lightroom-plugin/PluginInit.lua`
- Modify: `cli/commands/selection.py`

追加関数:
- `extendSelection(params, callback)` (params.direction, params.amount)
- `deselectActive(params, callback)`
- `deselectOthers(params, callback)`

コミット:
```
git commit -m "feat: add selection extend/deselect commands (P3)"
```

---

### Task 25: Develop デバッグ系 CLI公開 (Gap B: 4コマンド)

**Files:**
- Modify: `cli/commands/develop.py`

`debug` サブグループ追加:
- `lr develop debug dump` -> `develop.dumpLrDevelopController`
- `lr develop debug gradient-params` -> `develop.discoverGradientParameters`
- `lr develop debug monitor` -> `develop.monitorParameterChanges`
- `lr develop debug probe` -> `develop.probeAllDevelopParameters`

コミット:
```
git commit -m "feat: expose develop debug/introspection CLI (4 commands, Gap B, P3)"
```

---

### Task 26: カラー操作 + マスクリセット系 CLI公開 (Gap B: 7コマンド)

**Files:**
- Modify: `cli/commands/develop.py`

カラー操作:
- `lr develop color green-swatch` -> `develop.createGreenSwatch`
- `lr develop color cyan-swatch` -> `develop.createCyanSwatch`
- `lr develop color enhance` -> `develop.enhanceColors`

マスクリセット系:
- `lr develop reset-gradient` -> `develop.resetGradient`
- `lr develop reset-circular` -> `develop.resetCircularGradient`
- `lr develop reset-brush` -> `develop.resetBrushing`
- `lr develop reset-masking` -> `develop.resetMasking`

コミット:
```
git commit -m "feat: expose color operations and mask reset CLI (7 commands, Gap B, P3)"
```

---

### Task 27: complexMask + createMaskWithLocalAdjustments CLI公開 (Gap B)

**Files:**
- Modify: `cli/commands/develop.py`

追加:
- `lr develop mask complex --steps '[...]'` -> `develop.createComplexMask`
- `lr develop local create-mask --tool <t> --settings '{}'` -> `develop.createMaskWithLocalAdjustments`

コミット:
```
git commit -m "feat: expose complex mask and local mask creation CLI (Gap B, P3)"
```

---

### Task 28: LrDevelopController 未実装メソッド対応 (Gap A)

**Files:**
- Modify: `lightroom-plugin/DevelopModule.lua`
- Modify: `lightroom-plugin/PluginInit.lua`
- Modify: `cli/commands/develop.py`

Lua追加: resetCrop, resetTransforms, resetSpotRemoval, resetRedeye, resetHealing, editInPhotoshop
CLI追加: 対応するコマンド群

コミット:
```
git commit -m "feat: add LrDevelopController reset/edit methods (P3)"
```

---

### Task 29: メタデータ強化 (Gap A: 場所・著作権・作成者等)

**Files:**
- Modify: `lightroom-plugin/CatalogModule.lua`
- Modify: `lightroom-plugin/PluginInit.lua`
- Modify: `cli/commands/catalog.py`

汎用メタデータ書き込み関数:

```lua
function CatalogModule.setMetadata(params, callback)
    ensureLrModules()
    local photoId = params.photoId
    local key = params.key
    local value = params.value
    -- バリデーション後、photo:setRawMetadata(key, value)
end
```

CLI: `lr catalog set-metadata <photo_id> <key> <value>`

コミット:
```
git commit -m "feat: add generic metadata write command for location/copyright/creator (P3)"
```

---

### Task 30: エクスポート・インポート・高度カタログ操作 (Gap A)

**Files:**
- Modify: `lightroom-plugin/CatalogModule.lua`
- Modify: `lightroom-plugin/PluginInit.lua`
- Modify: `cli/commands/catalog.py`

追加:
- createCollection, createSmartCollection, createCollectionSet
- createKeyword, removeKeyword
- setViewFilter, getCurrentViewFilter
- removeFromCatalog

コミット:
```
git commit -m "feat: add advanced catalog operations (collections, keywords, view filters) (P3)"
```

---

### Task 31: Phase D 全テスト通過確認 + カバレッジ確認

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

最終確認: 全Lua登録コマンド + 全Gap A実装がCLIから利用可能であること。

コミット:
```
git commit -m "test: verify full SDK coverage - all phases complete"
```

---

## 実装サマリー

| Phase | タスク数 | 主な成果物 |
|-------|---------|-----------|
| A (P0) | 5 | pickStatus読取り, setFlag/getFlag, setRating/addKeywords Lua実装, findPhotos条件検索 |
| B (P1) | 7 | bridge_commandデコレータ, SelectionModule, Catalog/Develop Gap B CLI公開, メタデータ書き込み, プリセット/スナップショット |
| C (P2) | 10 | トーンカーブ/マスキング/ローカル調整/フィルターCLI, 選択操作, レーティング増減, 回転, 仮想コピー, batch-metadata |
| D (P3) | 9 | カラーラベルトグル, 選択拡張, デバッグCLI, カラー操作, リセット系, 高度メタデータ, エクスポート/インポート |
| **合計** | **31** | **SDK カバー率 100%** |
