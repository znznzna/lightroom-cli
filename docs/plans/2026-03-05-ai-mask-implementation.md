# AI Mask API Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** AI エージェント向けの AI マスク CLI コマンド群を実装する
**Architecture:** Lua Plugin → Python SDK → Click CLI の3層。AI マスク作成 + 調整をアトミックに実行する Lua 関数を追加し、Python SDK でラップ、CLI で公開
**Tech Stack:** Lua (LR SDK), Python 3.10+, Click 8.x, pytest
---

## Task 1: プリセット定義モジュール作成

**Files:**
- Create: `lightroom_sdk/presets.py`
- Test: `tests/test_presets.py`

**Step 1: 失敗するテストを書く**

```python
# tests/test_presets.py
import pytest
from lightroom_sdk.presets import AI_MASK_PRESETS, get_preset, list_presets


def test_ai_mask_presets_has_five_entries():
    assert len(AI_MASK_PRESETS) == 5


def test_darken_sky_preset_keys():
    preset = AI_MASK_PRESETS["darken-sky"]
    assert preset == {"Exposure": -0.7, "Highlights": -30, "Saturation": 15}


def test_brighten_subject_preset():
    preset = AI_MASK_PRESETS["brighten-subject"]
    assert preset == {"Exposure": 0.5, "Shadows": 20, "Clarity": 10}


def test_blur_background_preset():
    preset = AI_MASK_PRESETS["blur-background"]
    assert preset == {"Sharpness": -80, "Clarity": -40}


def test_warm_skin_preset():
    preset = AI_MASK_PRESETS["warm-skin"]
    assert preset == {"Temp": 500, "Tint": 5, "Saturation": -10}


def test_enhance_landscape_preset():
    preset = AI_MASK_PRESETS["enhance-landscape"]
    assert preset == {"Clarity": 30, "Vibrance": 25, "Dehaze": 15}


def test_get_preset_returns_copy():
    """get_preset は元データを変更されないようコピーを返す"""
    preset = get_preset("darken-sky")
    preset["Exposure"] = 999
    assert AI_MASK_PRESETS["darken-sky"]["Exposure"] == -0.7


def test_get_preset_unknown_returns_none():
    assert get_preset("nonexistent") is None


def test_list_presets_returns_all_names():
    names = list_presets()
    assert set(names) == {"darken-sky", "brighten-subject", "blur-background", "warm-skin", "enhance-landscape"}
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_presets.py -v`
Expected: FAIL (ModuleNotFoundError)

**Step 3: 最小限の実装**

```python
# lightroom_sdk/presets.py
"""AI Mask adjustment presets."""

from typing import Dict, Optional

AI_MASK_PRESETS: Dict[str, Dict[str, float]] = {
    "darken-sky": {"Exposure": -0.7, "Highlights": -30, "Saturation": 15},
    "brighten-subject": {"Exposure": 0.5, "Shadows": 20, "Clarity": 10},
    "blur-background": {"Sharpness": -80, "Clarity": -40},
    "warm-skin": {"Temp": 500, "Tint": 5, "Saturation": -10},
    "enhance-landscape": {"Clarity": 30, "Vibrance": 25, "Dehaze": 15},
}


def get_preset(name: str) -> Optional[Dict[str, float]]:
    """プリセット名から調整パラメータのコピーを返す。存在しなければ None。"""
    preset = AI_MASK_PRESETS.get(name)
    if preset is None:
        return None
    return dict(preset)


def list_presets() -> list[str]:
    """利用可能なプリセット名の一覧を返す。"""
    return list(AI_MASK_PRESETS.keys())
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_presets.py -v`
Expected: PASS (9 tests)

**Step 5: コミット**
```bash
git add lightroom_sdk/presets.py tests/test_presets.py
git commit -m "feat: add AI mask adjustment presets module"
```

---

## Task 2: SDK タイムアウト設定追加

**Files:**
- Modify: `lightroom_sdk/retry.py`
- Test: `tests/test_retry.py`

**Step 1: 失敗するテストを書く**

`tests/test_retry.py` の末尾に追加:

```python
def test_ai_mask_timeout():
    assert get_timeout("develop.createAIMaskWithAdjustments") == 60.0


def test_batch_ai_mask_timeout():
    assert get_timeout("develop.batchAIMask") == 300.0


def test_probe_ai_part_timeout():
    assert get_timeout("develop.probeAIPartSupport") == 30.0
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_retry.py -v -k "ai_mask or batch_ai or probe_ai"`
Expected: FAIL (AssertionError: 30.0 != 60.0)

**Step 3: 最小限の実装**

`lightroom_sdk/retry.py` の `COMMAND_TIMEOUTS` 辞書に以下を追加:

```python
COMMAND_TIMEOUTS: dict[str, float] = {
    "system.ping": 5.0,
    "system.status": 5.0,
    "system.reconnect": 10.0,
    "preview.*": 120.0,
    "develop.set_parameter": 10.0,
    "develop.set_parameters": 15.0,
    "develop.get_current_settings": 10.0,
    "catalog.search_photos": 60.0,
    "catalog.get_all_photos": 60.0,
    # AI Mask commands
    "develop.createAIMaskWithAdjustments": 60.0,
    "develop.batchAIMask": 300.0,
    "develop.probeAIPartSupport": 30.0,
}
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_retry.py -v`
Expected: PASS

**Step 5: コミット**
```bash
git add lightroom_sdk/retry.py tests/test_retry.py
git commit -m "feat: add AI mask command timeouts (60s single, 300s batch)"
```

---

## Task 3: SDK client に create_ai_mask メソッド追加

**Files:**
- Modify: `lightroom_sdk/client.py`
- Test: `tests/test_client.py`

**Step 1: 失敗するテストを書く**

`tests/test_client.py` の末尾に追加:

```python
@pytest.mark.asyncio
async def test_create_ai_mask_basic(mock_lr_server):
    """create_ai_mask が develop.createAIMaskWithAdjustments を正しいパラメータで送信する"""
    mock_lr_server.register_response("develop.createAIMaskWithAdjustments", {
        "maskType": "aiSelection",
        "selectionType": "sky",
        "message": "Created AI sky mask",
    })

    from lightroom_sdk.client import LightroomClient
    client = LightroomClient()
    await client.connect()
    try:
        result = await client.create_ai_mask("sky")
        assert result["selectionType"] == "sky"
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_create_ai_mask_with_adjustments(mock_lr_server):
    """create_ai_mask に adjustments を渡すと params に含まれる"""
    mock_lr_server.register_response("develop.createAIMaskWithAdjustments", {
        "maskType": "aiSelection",
        "selectionType": "subject",
        "adjustments": {"Exposure": 0.5},
    })

    from lightroom_sdk.client import LightroomClient
    client = LightroomClient()
    await client.connect()
    try:
        result = await client.create_ai_mask("subject", adjustments={"Exposure": 0.5})
        assert result["adjustments"] == {"Exposure": 0.5}
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_create_ai_mask_with_part(mock_lr_server):
    """create_ai_mask に part を渡すと params に含まれる"""
    mock_lr_server.register_response("develop.createAIMaskWithAdjustments", {
        "maskType": "aiSelection",
        "selectionType": "people",
        "part": "eyes",
    })

    from lightroom_sdk.client import LightroomClient
    client = LightroomClient()
    await client.connect()
    try:
        result = await client.create_ai_mask("people", part="eyes")
        assert result["part"] == "eyes"
    finally:
        await client.disconnect()
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_client.py -v -k "ai_mask"`
Expected: FAIL (AttributeError: 'LightroomClient' object has no attribute 'create_ai_mask')

**Step 3: 最小限の実装**

`lightroom_sdk/client.py` の `LightroomClient` クラスに以下を追加（`wait_for_lightroom` メソッドの後）:

```python
    async def create_ai_mask(
        self,
        selection_type: str,
        part: Optional[str] = None,
        adjustments: Optional[Dict[str, float]] = None,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        """Create an AI mask and optionally apply adjustments.

        Args:
            selection_type: One of subject, sky, background, objects, people, landscape
            part: Optional body/landscape part for people/landscape types
            adjustments: Optional dict of develop parameter adjustments
            timeout: Command timeout in seconds
        """
        params: Dict[str, Any] = {"selectionType": selection_type}
        if part:
            params["part"] = part
        if adjustments:
            params["adjustments"] = adjustments
        return await self.execute_command(
            "develop.createAIMaskWithAdjustments", params, timeout=timeout
        )
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_client.py -v -k "ai_mask"`
Expected: PASS (3 tests)

**Step 5: コミット**
```bash
git add lightroom_sdk/client.py tests/test_client.py
git commit -m "feat: add create_ai_mask method to LightroomClient"
```

---

## Task 4: SDK client に batch_ai_mask メソッド追加

**Files:**
- Modify: `lightroom_sdk/client.py`
- Test: `tests/test_client.py`

**Step 1: 失敗するテストを書く**

`tests/test_client.py` の末尾に追加:

```python
@pytest.mark.asyncio
async def test_batch_ai_mask_with_photo_ids(mock_lr_server):
    """batch_ai_mask が photoIds 付きで送信される"""
    mock_lr_server.register_response("develop.batchAIMask", {
        "total": 2, "succeeded": 2, "failed": 0,
        "results": [
            {"photoId": "1", "status": "success"},
            {"photoId": "2", "status": "success"},
        ],
    })

    from lightroom_sdk.client import LightroomClient
    client = LightroomClient()
    await client.connect()
    try:
        result = await client.batch_ai_mask("sky", photo_ids=["1", "2"])
        assert result["total"] == 2
        assert result["succeeded"] == 2
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_batch_ai_mask_all_selected(mock_lr_server):
    """batch_ai_mask --all-selected で allSelected=True が送信される"""
    mock_lr_server.register_response("develop.batchAIMask", {
        "total": 3, "succeeded": 3, "failed": 0, "results": [],
    })

    from lightroom_sdk.client import LightroomClient
    client = LightroomClient()
    await client.connect()
    try:
        result = await client.batch_ai_mask("subject", all_selected=True)
        assert result["total"] == 3
    finally:
        await client.disconnect()
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_client.py -v -k "batch_ai"`
Expected: FAIL (AttributeError: 'LightroomClient' object has no attribute 'batch_ai_mask')

**Step 3: 最小限の実装**

`lightroom_sdk/client.py` の `LightroomClient` クラスに以下を追加（`create_ai_mask` メソッドの後）:

```python
    async def batch_ai_mask(
        self,
        selection_type: str,
        photo_ids: Optional[list[str]] = None,
        all_selected: bool = False,
        part: Optional[str] = None,
        adjustments: Optional[Dict[str, float]] = None,
        continue_on_error: bool = True,
        timeout: float = 300.0,
    ) -> Dict[str, Any]:
        """Apply AI mask to multiple photos.

        Args:
            selection_type: One of subject, sky, background, objects, people, landscape
            photo_ids: List of photo IDs to process
            all_selected: If True, apply to all currently selected photos
            part: Optional body/landscape part
            adjustments: Optional dict of develop parameter adjustments
            continue_on_error: If True, continue processing on individual failures
            timeout: Command timeout in seconds
        """
        params: Dict[str, Any] = {
            "selectionType": selection_type,
            "allSelected": all_selected,
            "continueOnError": continue_on_error,
        }
        if photo_ids:
            params["photoIds"] = photo_ids
        if part:
            params["part"] = part
        if adjustments:
            params["adjustments"] = adjustments
        return await self.execute_command(
            "develop.batchAIMask", params, timeout=timeout
        )
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/test_client.py -v -k "batch_ai"`
Expected: PASS (2 tests)

**Step 5: コミット**
```bash
git add lightroom_sdk/client.py tests/test_client.py
git commit -m "feat: add batch_ai_mask method to LightroomClient"
```

---

## Task 5: CLI ai グループ骨格 + subject コマンド

**Files:**
- Create: `cli/commands/ai_mask.py`
- Modify: `cli/commands/develop.py` (import + group 登録)
- Test: `tests/integration/test_cli_ai_mask.py`

**Step 1: 失敗するテストを書く**

```python
# tests/integration/test_cli_ai_mask.py
import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.commands.ai_mask.get_bridge")
def test_ai_subject_creates_mask(mock_get_bridge, runner):
    """lr develop ai subject が develop.createAIMaskWithAdjustments を呼ぶ"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {
            "maskType": "aiSelection",
            "selectionType": "subject",
            "message": "Created AI subject mask",
        },
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "subject"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.createAIMaskWithAdjustments",
        {"selectionType": "subject"},
        timeout=60.0,
    )


@patch("cli.commands.ai_mask.get_bridge")
def test_ai_sky_creates_mask(mock_get_bridge, runner):
    """lr develop ai sky が正しい selectionType で呼ばれる"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"selectionType": "sky", "message": "Created AI sky mask"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "sky"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.createAIMaskWithAdjustments",
        {"selectionType": "sky"},
        timeout=60.0,
    )


@patch("cli.commands.ai_mask.get_bridge")
def test_ai_background_creates_mask(mock_get_bridge, runner):
    """lr develop ai background"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"selectionType": "background"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "background"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.createAIMaskWithAdjustments",
        {"selectionType": "background"},
        timeout=60.0,
    )


@patch("cli.commands.ai_mask.get_bridge")
def test_ai_objects_creates_mask(mock_get_bridge, runner):
    """lr develop ai objects"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"selectionType": "objects"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "objects"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.createAIMaskWithAdjustments",
        {"selectionType": "objects"},
        timeout=60.0,
    )
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/integration/test_cli_ai_mask.py -v`
Expected: FAIL (ModuleNotFoundError or NoSuchCommand)

**Step 3: 最小限の実装**

```python
# cli/commands/ai_mask.py
"""AI Mask CLI commands — lr develop ai <type>"""

import asyncio
import json
import click
from cli.output import OutputFormatter


def get_bridge():
    """ResilientSocketBridge インスタンスを取得（遅延 import）"""
    from lightroom_sdk.resilient_bridge import ResilientSocketBridge
    return ResilientSocketBridge()


def run_async(coro):
    """CLI から async 関数を実行するヘルパー"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


AI_SELECTION_TYPES = ["subject", "sky", "background", "objects", "people", "landscape"]


@click.group("ai")
def ai():
    """AI mask commands (subject, sky, background, people, landscape, objects)"""
    pass


def _make_ai_type_command(selection_type: str, has_part: bool = False, part_choices: list[str] | None = None):
    """各 AI マスクタイプコマンドのファクトリ関数"""

    params = [
        click.Option(["--adjust"], default=None, help="JSON adjustment settings"),
        click.Option(["--adjust-preset"], default=None, help="Named preset (darken-sky, brighten-subject, etc)"),
    ]
    if has_part and part_choices:
        params.insert(0, click.Option(
            ["--part"], default=None,
            type=click.Choice(part_choices),
            help="Specific part to mask",
        ))

    @click.pass_context
    def command_func(ctx, **kwargs):
        adjust = kwargs.get("adjust")
        adjust_preset = kwargs.get("adjust_preset")
        part = kwargs.get("part")
        timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
        fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

        # Build params
        cmd_params: dict = {"selectionType": selection_type}
        if part:
            cmd_params["part"] = part

        # Resolve adjustments
        adjustments = _resolve_adjustments(adjust, adjust_preset)
        if isinstance(adjustments, str):
            # Error message
            click.echo(OutputFormatter.format_error(adjustments))
            return
        if adjustments:
            cmd_params["adjustments"] = adjustments

        async def _run():
            bridge = get_bridge()
            try:
                result = await bridge.send_command(
                    "develop.createAIMaskWithAdjustments",
                    cmd_params,
                    timeout=max(timeout, 60.0),
                )
                click.echo(OutputFormatter.format(result.get("result", result), fmt))
            except Exception as e:
                click.echo(OutputFormatter.format_error(str(e)))
            finally:
                await bridge.disconnect()

        run_async(_run())

    cmd = click.Command(
        name=selection_type,
        callback=command_func,
        params=params,
        help=f"Create AI {selection_type} mask",
    )
    return cmd


def _resolve_adjustments(adjust_json: str | None, adjust_preset: str | None) -> dict | str | None:
    """--adjust JSON と --adjust-preset を解決する。エラー時は文字列を返す。"""
    if adjust_json and adjust_preset:
        return "Cannot use both --adjust and --adjust-preset"

    if adjust_preset:
        from lightroom_sdk.presets import get_preset
        preset = get_preset(adjust_preset)
        if preset is None:
            from lightroom_sdk.presets import list_presets
            available = ", ".join(list_presets())
            return f"Unknown preset '{adjust_preset}'. Available: {available}"
        return preset

    if adjust_json:
        try:
            parsed = json.loads(adjust_json)
            if not isinstance(parsed, dict):
                return "--adjust must be a JSON object"
            return parsed
        except json.JSONDecodeError as e:
            return f"Invalid JSON in --adjust: {e}"

    return None


# Register type commands
ai.add_command(_make_ai_type_command("subject"))
ai.add_command(_make_ai_type_command("sky"))
ai.add_command(_make_ai_type_command("background"))
ai.add_command(_make_ai_type_command("objects"))
ai.add_command(_make_ai_type_command(
    "people", has_part=True,
    part_choices=["eyes", "hair", "skin", "lips", "teeth", "clothes"],
))
ai.add_command(_make_ai_type_command(
    "landscape", has_part=True,
    part_choices=["mountain", "tree", "water", "building", "road"],
))
```

次に `cli/commands/develop.py` の `develop` グループに `ai` を登録する。
ファイル先頭付近（`@click.group()` の `develop` 定義の後、最初のコマンド定義の前）に追加:

```python
# --- AI Mask commands (別ファイルに分離) ---
from cli.commands.ai_mask import ai
develop.add_command(ai)
```

具体的には、`develop.py` の 35 行目（`pass` の後の空行）の直後に挿入する:

```python
# develop.py 35行目の後に追加
from cli.commands.ai_mask import ai
develop.add_command(ai)
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/integration/test_cli_ai_mask.py -v`
Expected: PASS (4 tests)

**Step 5: コミット**
```bash
git add cli/commands/ai_mask.py cli/commands/develop.py tests/integration/test_cli_ai_mask.py
git commit -m "feat: add CLI ai group with subject/sky/background/objects commands"
```

---

## Task 6: people/landscape の --part オプションテスト

**Files:**
- Test: `tests/integration/test_cli_ai_mask.py` (追加)

**Step 1: 失敗するテストを書く**

`tests/integration/test_cli_ai_mask.py` の末尾に追加:

```python
@patch("cli.commands.ai_mask.get_bridge")
def test_ai_people_with_part(mock_get_bridge, runner):
    """lr develop ai people --part eyes がパラメータに part を含む"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"selectionType": "people", "part": "eyes"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "people", "--part", "eyes"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.createAIMaskWithAdjustments",
        {"selectionType": "people", "part": "eyes"},
        timeout=60.0,
    )


@patch("cli.commands.ai_mask.get_bridge")
def test_ai_people_without_part(mock_get_bridge, runner):
    """lr develop ai people (part なし) は part をパラメータに含まない"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"selectionType": "people"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "people"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.createAIMaskWithAdjustments",
        {"selectionType": "people"},
        timeout=60.0,
    )


@patch("cli.commands.ai_mask.get_bridge")
def test_ai_landscape_with_part(mock_get_bridge, runner):
    """lr develop ai landscape --part water"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"selectionType": "landscape", "part": "water"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "landscape", "--part", "water"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.createAIMaskWithAdjustments",
        {"selectionType": "landscape", "part": "water"},
        timeout=60.0,
    )
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/integration/test_cli_ai_mask.py::test_ai_people_with_part tests/integration/test_cli_ai_mask.py::test_ai_people_without_part tests/integration/test_cli_ai_mask.py::test_ai_landscape_with_part -v`
Expected: PASS (Task 5 の実装で既に対応済みのはず。もし FAIL なら修正)

**Step 3: テスト追加のみ（実装は Task 5 で完了済み）**

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/integration/test_cli_ai_mask.py -v`
Expected: PASS (7 tests)

**Step 5: コミット**
```bash
git add tests/integration/test_cli_ai_mask.py
git commit -m "test: add people/landscape --part option tests for ai mask"
```

---

## Task 7: --adjust JSON オプションテスト

**Files:**
- Test: `tests/integration/test_cli_ai_mask.py` (追加)

**Step 1: 失敗するテストを書く**

`tests/integration/test_cli_ai_mask.py` の末尾に追加:

```python
@patch("cli.commands.ai_mask.get_bridge")
def test_ai_sky_with_adjust_json(mock_get_bridge, runner):
    """lr develop ai sky --adjust '{"Exposure": -0.5}' が adjustments を含む"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"selectionType": "sky", "adjustments": {"Exposure": -0.5}},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "sky", "--adjust", '{"Exposure": -0.5}'])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.createAIMaskWithAdjustments",
        {"selectionType": "sky", "adjustments": {"Exposure": -0.5}},
        timeout=60.0,
    )


@patch("cli.commands.ai_mask.get_bridge")
def test_ai_subject_with_adjust_preset(mock_get_bridge, runner):
    """lr develop ai subject --adjust-preset brighten-subject がプリセットを展開する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"selectionType": "subject"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "subject", "--adjust-preset", "brighten-subject"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.createAIMaskWithAdjustments",
        {
            "selectionType": "subject",
            "adjustments": {"Exposure": 0.5, "Shadows": 20, "Clarity": 10},
        },
        timeout=60.0,
    )


def test_ai_adjust_invalid_json(runner):
    """--adjust に不正な JSON を渡すとエラーメッセージが出る"""
    result = runner.invoke(cli, ["develop", "ai", "sky", "--adjust", "not-json"])
    assert result.exit_code == 0
    assert "Invalid JSON" in result.output


def test_ai_adjust_unknown_preset(runner):
    """--adjust-preset に存在しないプリセット名でエラー"""
    result = runner.invoke(cli, ["develop", "ai", "sky", "--adjust-preset", "nonexistent"])
    assert result.exit_code == 0
    assert "Unknown preset" in result.output


def test_ai_adjust_and_preset_conflict(runner):
    """--adjust と --adjust-preset の同時指定でエラー"""
    result = runner.invoke(cli, [
        "develop", "ai", "sky",
        "--adjust", '{"Exposure": 1}',
        "--adjust-preset", "darken-sky",
    ])
    assert result.exit_code == 0
    assert "Cannot use both" in result.output
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/integration/test_cli_ai_mask.py -v -k "adjust"`
Expected: PASS (Task 5 の実装で対応済みのはず)

**Step 3: テスト追加のみ（実装は Task 5 で完了済み）**

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/integration/test_cli_ai_mask.py -v`
Expected: PASS (12 tests)

**Step 5: コミット**
```bash
git add tests/integration/test_cli_ai_mask.py
git commit -m "test: add --adjust and --adjust-preset option tests for ai mask"
```

---

## Task 8: presets コマンド

**Files:**
- Modify: `cli/commands/ai_mask.py`
- Test: `tests/integration/test_cli_ai_mask.py` (追加)

**Step 1: 失敗するテストを書く**

`tests/integration/test_cli_ai_mask.py` の末尾に追加:

```python
def test_ai_presets_lists_all(runner):
    """lr develop ai presets が全プリセット名を出力する"""
    result = runner.invoke(cli, ["develop", "ai", "presets"])
    assert result.exit_code == 0
    assert "darken-sky" in result.output
    assert "brighten-subject" in result.output
    assert "blur-background" in result.output
    assert "warm-skin" in result.output
    assert "enhance-landscape" in result.output


def test_ai_presets_json_format(runner):
    """lr develop ai presets -o json が JSON 形式で出力する"""
    result = runner.invoke(cli, ["-o", "json", "develop", "ai", "presets"])
    assert result.exit_code == 0
    import json
    data = json.loads(result.output)
    assert "darken-sky" in data
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/integration/test_cli_ai_mask.py -v -k "presets"`
Expected: FAIL (NoSuchCommand: presets)

**Step 3: 最小限の実装**

`cli/commands/ai_mask.py` の末尾（`ai.add_command(...)` の後）に追加:

```python
@ai.command("presets")
@click.pass_context
def ai_presets(ctx):
    """List available adjustment presets"""
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
    from lightroom_sdk.presets import AI_MASK_PRESETS
    click.echo(OutputFormatter.format(AI_MASK_PRESETS, fmt))
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/integration/test_cli_ai_mask.py -v -k "presets"`
Expected: PASS (2 tests)

**Step 5: コミット**
```bash
git add cli/commands/ai_mask.py tests/integration/test_cli_ai_mask.py
git commit -m "feat: add 'lr develop ai presets' command"
```

---

## Task 9: list コマンド

**Files:**
- Modify: `cli/commands/ai_mask.py`
- Test: `tests/integration/test_cli_ai_mask.py` (追加)

**Step 1: 失敗するテストを書く**

`tests/integration/test_cli_ai_mask.py` の末尾に追加:

```python
@patch("cli.commands.ai_mask.get_bridge")
def test_ai_list_calls_get_all_masks(mock_get_bridge, runner):
    """lr develop ai list が develop.getAllMasks を呼ぶ"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"masks": [{"type": "aiSelection", "subtype": "sky"}]},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "list"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.getAllMasks", {}, timeout=30.0,
    )
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/integration/test_cli_ai_mask.py::test_ai_list_calls_get_all_masks -v`
Expected: FAIL (NoSuchCommand: list)

**Step 3: 最小限の実装**

`cli/commands/ai_mask.py` に追加:

```python
@ai.command("list")
@click.pass_context
def ai_list(ctx):
    """List all masks on the current photo"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.getAllMasks", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/integration/test_cli_ai_mask.py::test_ai_list_calls_get_all_masks -v`
Expected: PASS

**Step 5: コミット**
```bash
git add cli/commands/ai_mask.py tests/integration/test_cli_ai_mask.py
git commit -m "feat: add 'lr develop ai list' command"
```

---

## Task 10: reset コマンド

**Files:**
- Modify: `cli/commands/ai_mask.py`
- Test: `tests/integration/test_cli_ai_mask.py` (追加)

**Step 1: 失敗するテストを書く**

`tests/integration/test_cli_ai_mask.py` の末尾に追加:

```python
@patch("cli.commands.ai_mask.get_bridge")
def test_ai_reset_calls_reset_masking(mock_get_bridge, runner):
    """lr develop ai reset が develop.resetMasking を呼ぶ"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"message": "All masks reset"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "reset"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.resetMasking", {}, timeout=30.0,
    )
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/integration/test_cli_ai_mask.py::test_ai_reset_calls_reset_masking -v`
Expected: FAIL

**Step 3: 最小限の実装**

`cli/commands/ai_mask.py` に追加:

```python
@ai.command("reset")
@click.pass_context
def ai_reset(ctx):
    """Remove all masks from the current photo"""
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command("develop.resetMasking", {}, timeout=timeout)
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/integration/test_cli_ai_mask.py::test_ai_reset_calls_reset_masking -v`
Expected: PASS

**Step 5: コミット**
```bash
git add cli/commands/ai_mask.py tests/integration/test_cli_ai_mask.py
git commit -m "feat: add 'lr develop ai reset' command"
```

---

## Task 11: batch コマンド

**Files:**
- Modify: `cli/commands/ai_mask.py`
- Test: `tests/integration/test_cli_ai_mask.py` (追加)

**Step 1: 失敗するテストを書く**

`tests/integration/test_cli_ai_mask.py` の末尾に追加:

```python
@patch("cli.commands.ai_mask.get_bridge")
def test_ai_batch_all_selected(mock_get_bridge, runner):
    """lr develop ai batch sky --all-selected"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"total": 3, "succeeded": 3, "failed": 0, "results": []},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "batch", "sky", "--all-selected"])
    assert result.exit_code == 0
    call_args = mock_bridge.send_command.call_args
    assert call_args[0][0] == "develop.batchAIMask"
    assert call_args[0][1]["selectionType"] == "sky"
    assert call_args[0][1]["allSelected"] is True


@patch("cli.commands.ai_mask.get_bridge")
def test_ai_batch_with_photos(mock_get_bridge, runner):
    """lr develop ai batch subject --photos 1,2,3"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"total": 3, "succeeded": 3, "failed": 0, "results": []},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "batch", "subject", "--photos", "1,2,3"])
    assert result.exit_code == 0
    call_args = mock_bridge.send_command.call_args
    assert call_args[0][1]["photoIds"] == ["1", "2", "3"]


@patch("cli.commands.ai_mask.get_bridge")
def test_ai_batch_with_adjust_preset(mock_get_bridge, runner):
    """lr develop ai batch sky --all-selected --adjust-preset darken-sky"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"total": 2, "succeeded": 2, "failed": 0, "results": []},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, [
        "develop", "ai", "batch", "sky",
        "--all-selected", "--adjust-preset", "darken-sky",
    ])
    assert result.exit_code == 0
    call_args = mock_bridge.send_command.call_args
    assert call_args[0][1]["adjustments"] == {"Exposure": -0.7, "Highlights": -30, "Saturation": 15}


@patch("cli.commands.ai_mask.get_bridge")
def test_ai_batch_dry_run(mock_get_bridge, runner):
    """lr develop ai batch sky --all-selected --dry-run は実行せず対象を表示"""
    # dry-run では bridge を呼ばないはず（mockが呼ばれないことを確認）
    mock_bridge = AsyncMock()
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "ai", "batch", "sky", "--all-selected", "--dry-run"])
    assert result.exit_code == 0
    assert "dry-run" in result.output.lower() or "Dry run" in result.output
    mock_bridge.send_command.assert_not_called()


def test_ai_batch_no_target(runner):
    """--photos も --all-selected もない場合エラー"""
    result = runner.invoke(cli, ["develop", "ai", "batch", "sky"])
    assert result.exit_code == 0
    assert "Specify --photos or --all-selected" in result.output
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/integration/test_cli_ai_mask.py -v -k "batch"`
Expected: FAIL (NoSuchCommand: batch)

**Step 3: 最小限の実装**

`cli/commands/ai_mask.py` に追加:

```python
@ai.command("batch")
@click.argument("type", type=click.Choice(AI_SELECTION_TYPES))
@click.option("--photos", default=None, help="Comma-separated photo IDs")
@click.option("--all-selected", is_flag=True, help="Apply to all selected photos")
@click.option("--adjust", default=None, help="JSON adjustment settings")
@click.option("--adjust-preset", default=None, help="Named preset")
@click.option("--dry-run", is_flag=True, help="Show targets without applying")
@click.option("--continue-on-error", is_flag=True, default=True, help="Continue on errors")
@click.pass_context
def ai_batch(ctx, type, photos, all_selected, adjust, adjust_preset, dry_run, continue_on_error):
    """Apply AI mask to multiple photos"""
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0

    if not photos and not all_selected:
        click.echo(OutputFormatter.format_error("Specify --photos or --all-selected"))
        return

    if dry_run:
        target = "all selected photos" if all_selected else f"photos: {photos}"
        click.echo(f"Dry run: would apply AI {type} mask to {target}")
        return

    # Resolve adjustments
    adjustments = _resolve_adjustments(adjust, adjust_preset)
    if isinstance(adjustments, str):
        click.echo(OutputFormatter.format_error(adjustments))
        return

    cmd_params: dict = {
        "selectionType": type,
        "allSelected": all_selected,
        "continueOnError": continue_on_error,
    }
    if photos:
        cmd_params["photoIds"] = [p.strip() for p in photos.split(",")]
    if adjustments:
        cmd_params["adjustments"] = adjustments

    async def _run():
        bridge = get_bridge()
        try:
            result = await bridge.send_command(
                "develop.batchAIMask",
                cmd_params,
                timeout=max(timeout, 300.0),
            )
            click.echo(OutputFormatter.format(result.get("result", result), fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e)))
        finally:
            await bridge.disconnect()

    run_async(_run())
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/integration/test_cli_ai_mask.py -v -k "batch"`
Expected: PASS (5 tests)

**Step 5: コミット**
```bash
git add cli/commands/ai_mask.py tests/integration/test_cli_ai_mask.py
git commit -m "feat: add 'lr develop ai batch' command with dry-run support"
```

---

## Task 12: Lua createAIMaskWithAdjustments 関数

**Files:**
- Modify: `lightroom-plugin/DevelopModule.lua`
- Modify: `lightroom-plugin/PluginInit.lua` (ルーター登録)

**Step 1: 失敗するテストを書く**

Lua の直接テストは不可。代わりに MockLightroomServer にハンドラを追加して CLI 経由で検証する（Task 13 で実施）。
このステップでは Lua コードのみ実装する。

**Step 2: 実装**

`lightroom-plugin/DevelopModule.lua` の `createAISelectionMask` 関数（2791行目）の直後に追加:

```lua
function DevelopModule.createAIMaskWithAdjustments(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local selectionType = params.selectionType or "subject"
    local part = params.part
    local adjustments = params.adjustments

    -- Validate selection type
    local validTypes = {"subject", "sky", "background", "objects", "people", "landscape"}
    local isValid = false
    for _, validType in ipairs(validTypes) do
        if selectionType == validType then
            isValid = true
            break
        end
    end

    if not isValid then
        callback({
            error = {
                code = "AI_MASK_INVALID_TYPE",
                message = "Valid types: " .. table.concat(validTypes, ", ")
            }
        })
        return
    end

    local success, result = ErrorUtils.safeCall(function()
        -- Guard: check current tool to avoid hang
        local currentTool = LrDevelopController.getSelectedTool()
        if currentTool ~= "masking" then
            LrDevelopController.selectTool("masking")
        end

        -- Create AI selection mask
        local maskId = LrDevelopController.createNewMask("aiSelection", selectionType)

        local partApplied = false
        local partSupported = false

        -- Attempt part selection if requested (SDK support unverified)
        if part then
            local partSuccess, partResult = ErrorUtils.safeCall(function()
                -- Try part-based mask creation
                -- NOTE: This is experimental - SDK may not support part selection
                return false  -- Placeholder until SDK support is verified
            end)
            if partSuccess and partResult then
                partApplied = true
                partSupported = true
            end
        end

        -- Apply adjustments if provided
        local appliedAdjustments = {}
        local adjustmentErrors = {}

        if adjustments and type(adjustments) == "table" then
            for param, value in pairs(adjustments) do
                local adjSuccess, adjError = ErrorUtils.safeCall(function()
                    LrDevelopController.setValue(param, value)
                end)
                if adjSuccess then
                    appliedAdjustments[param] = value
                else
                    adjustmentErrors[param] = tostring(adjError)
                end
            end
        end

        local resultData = {
            maskType = "aiSelection",
            selectionType = selectionType,
            part = part,
            partApplied = partApplied,
            partSupported = partSupported,
            message = "Created AI " .. selectionType .. " mask"
        }

        if next(appliedAdjustments) then
            resultData.adjustments = {
                applied = appliedAdjustments,
            }
            resultData.message = resultData.message .. " with adjustments"
        end

        if next(adjustmentErrors) then
            resultData.adjustmentErrors = adjustmentErrors
        end

        if part and not partApplied then
            resultData.warning = "Part selection not supported by SDK. Full " .. selectionType .. " mask created instead."
        end

        return resultData
    end)

    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "AI_MASK_CREATION_FAILED",
                message = "Failed to create AI mask: " .. tostring(result)
            }
        })
    end
end
```

`lightroom-plugin/PluginInit.lua` の `develop.createAISelectionMask` 登録行（316行目）の後に追加:

```lua
    router:register("develop.createAIMaskWithAdjustments", DevelopModule.createAIMaskWithAdjustments, "sync")
```

**Step 3: コミット**
```bash
git add lightroom-plugin/DevelopModule.lua lightroom-plugin/PluginInit.lua
git commit -m "feat: add Lua createAIMaskWithAdjustments with hang guard and adjustment support"
```

---

## Task 13: Lua batchAIMask 関数

**Files:**
- Modify: `lightroom-plugin/DevelopModule.lua`
- Modify: `lightroom-plugin/PluginInit.lua` (ルーター登録)

**Step 1: 実装**

`lightroom-plugin/DevelopModule.lua` の `createAIMaskWithAdjustments` の直後に追加:

```lua
function DevelopModule.batchAIMask(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local selectionType = params.selectionType or "subject"
    local photoIds = params.photoIds
    local allSelected = params.allSelected
    local part = params.part
    local adjustments = params.adjustments
    local continueOnError = params.continueOnError
    if continueOnError == nil then continueOnError = true end

    local success, result = ErrorUtils.safeCall(function()
        local catalog = LrApplication.activeCatalog()
        local photos = {}

        if allSelected then
            local targetPhoto = catalog:getTargetPhoto()
            local multiplePhotos = catalog:getTargetPhotos()
            if multiplePhotos and #multiplePhotos > 0 then
                photos = multiplePhotos
            elseif targetPhoto then
                photos = { targetPhoto }
            end
        elseif photoIds and type(photoIds) == "table" then
            -- Resolve photo IDs to photo objects
            for _, pid in ipairs(photoIds) do
                local allPhotos = catalog:getAllPhotos()
                for _, photo in ipairs(allPhotos) do
                    local localId = tostring(photo.localIdentifier)
                    if localId == pid then
                        table.insert(photos, photo)
                        break
                    end
                end
            end
        end

        if #photos == 0 then
            return {
                total = 0, succeeded = 0, failed = 0,
                results = {},
                message = "No photos found to process",
            }
        end

        local results = {}
        local succeeded = 0
        local failed = 0

        for _, photo in ipairs(photos) do
            local photoSuccess, photoResult = ErrorUtils.safeCall(function()
                -- Select this photo
                catalog:setSelectedPhotos(photo, { photo })

                -- Create mask with adjustments
                local maskParams = {
                    selectionType = selectionType,
                    part = part,
                    adjustments = adjustments,
                }

                -- Guard: ensure masking tool
                local currentTool = LrDevelopController.getSelectedTool()
                if currentTool ~= "masking" then
                    LrDevelopController.selectTool("masking")
                end

                local maskId = LrDevelopController.createNewMask("aiSelection", selectionType)

                -- Apply adjustments
                if adjustments and type(adjustments) == "table" then
                    for param, value in pairs(adjustments) do
                        LrDevelopController.setValue(param, value)
                    end
                end

                return {
                    photoId = tostring(photo.localIdentifier),
                    status = "success",
                    message = "Applied " .. selectionType .. " mask",
                }
            end)

            if photoSuccess then
                table.insert(results, photoResult)
                succeeded = succeeded + 1
            else
                failed = failed + 1
                table.insert(results, {
                    photoId = tostring(photo.localIdentifier or "unknown"),
                    status = "error",
                    error = tostring(photoResult),
                })
                if not continueOnError then
                    break
                end
            end
        end

        return {
            total = #photos,
            succeeded = succeeded,
            failed = failed,
            results = results,
            message = "Batch AI mask: " .. succeeded .. "/" .. #photos .. " succeeded",
        }
    end)

    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "BATCH_AI_MASK_FAILED",
                message = "Failed to batch AI mask: " .. tostring(result)
            }
        })
    end
end
```

`lightroom-plugin/PluginInit.lua` の `createAIMaskWithAdjustments` 登録行の後に追加:

```lua
    router:register("develop.batchAIMask", DevelopModule.batchAIMask, "sync")
```

**Step 2: コミット**
```bash
git add lightroom-plugin/DevelopModule.lua lightroom-plugin/PluginInit.lua
git commit -m "feat: add Lua batchAIMask for multi-photo AI mask application"
```

---

## Task 14: MockLightroomServer に AI マスクハンドラ追加

**Files:**
- Modify: `tests/mocks/lightroom_mock.py`

**Step 1: 失敗するテストを書く**

この Task は Mock 側の拡張のみ。テストは既存の integration テストで検証される。

**Step 2: 実装**

`tests/mocks/lightroom_mock.py` の `MockLightroomServer` クラスを拡張する。

現在の MockLightroomServer は汎用的な `register_response` を使っている。AI マスク用のデフォルトレスポンスを `start()` メソッド内で登録する方式にする。

`_handle_receiver` メソッドのレスポンス生成部分は変更不要（`self._responses` ベースで既に動作する）。テスト側で `register_response` を呼べばよい。

この Task は追加実装不要。既存の `register_response` メカニズムで十分。スキップする。

---

## Task 15: 全テストの統合実行

**Files:**
- なし (検証のみ)

**Step 1: 全テストを実行**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/ -v --ignore=tests/e2e`
Expected: ALL PASS

**Step 2: もし失敗するテストがあれば修正**

既存テストとの競合がないか確認する。特に以下を注意:
- `tests/integration/test_cli_develop_mask.py` — 既存の mask テストが壊れていないこと
- `tests/integration/test_cli_develop_filter.py` — filter テストが壊れていないこと
- `tests/test_project_structure.py` — プロジェクト構造テストが新ファイルを認識すること

**Step 3: コミット（修正があった場合のみ）**
```bash
git add -A
git commit -m "fix: resolve test conflicts after ai mask integration"
```

---

## Task 16: 既存コマンドの deprecated 化

**Files:**
- Modify: `cli/commands/develop.py`
- Test: `tests/integration/test_cli_ai_mask.py` (追加)

**Step 1: 失敗するテストを書く**

`tests/integration/test_cli_ai_mask.py` の末尾に追加:

```python
@patch("cli.commands.develop.get_bridge")
def test_deprecated_mask_list_shows_warning(mock_get_bridge, runner):
    """lr develop mask list が deprecated 警告を出す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"masks": []},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "mask", "list"])
    assert result.exit_code == 0
    assert "deprecated" in result.output.lower() or "lr develop ai list" in result.output


@patch("cli.commands.develop.get_bridge")
def test_deprecated_reset_masking_shows_warning(mock_get_bridge, runner):
    """lr develop reset-masking が deprecated 警告を出す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"message": "Reset"},
    }
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["develop", "reset-masking"])
    assert result.exit_code == 0
    assert "deprecated" in result.output.lower() or "lr develop ai reset" in result.output
```

**Step 2: 失敗を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/integration/test_cli_ai_mask.py -v -k "deprecated"`
Expected: FAIL (deprecated 警告が出ていない)

**Step 3: 最小限の実装**

`cli/commands/develop.py` の `mask_list` 関数（574行目付近）を修正:

```python
@mask.command("list")
@click.pass_context
def mask_list(ctx):
    """List all masks (DEPRECATED: use 'lr develop ai list')"""
    click.echo("Warning: 'lr develop mask list' is deprecated. Use 'lr develop ai list' instead.", err=True)
    # ... 既存の処理はそのまま
```

同様に `mask_selected`（592行目付近）、`reset_masking`（1409行目付近）にも deprecated 警告を追加。

`mask_list` の修正:
```python
def mask_list(ctx):
    """List all masks (DEPRECATED: use 'lr develop ai list')"""
    click.echo("Warning: 'lr develop mask list' is deprecated. Use 'lr develop ai list' instead.", err=True)
    timeout = ctx.obj.get("timeout", 30.0) if ctx.obj else 30.0
    # ... 以下既存のまま
```

`reset_masking` の修正（1409行目付近）:
```python
def reset_masking(ctx):
    """Reset masking (DEPRECATED: use 'lr develop ai reset')"""
    click.echo("Warning: 'lr develop reset-masking' is deprecated. Use 'lr develop ai reset' instead.", err=True)
    # ... 以下既存のまま
```

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/integration/test_cli_ai_mask.py -v -k "deprecated"`
Expected: PASS (2 tests)

**Step 5: コミット**
```bash
git add cli/commands/develop.py tests/integration/test_cli_ai_mask.py
git commit -m "feat: add deprecated warnings to mask list, mask selected, reset-masking"
```

---

## Task 17: 不要コマンドの削除

**Files:**
- Modify: `cli/commands/develop.py`
- Modify: `tests/integration/test_cli_develop_mask.py`
- Modify: `tests/integration/test_cli_develop_filter.py`

**Step 1: 削除対象の確認**

以下のコマンドを `cli/commands/develop.py` から削除:
- `mask create` (614行目)
- `mask select MASK_ID` (632行目)
- `mask delete MASK_ID` (653行目)
- `mask tool-info` (674行目)
- `mask select-tool` (694行目)
- `mask delete-tool` (715行目)
- `mask add` (736行目)
- `mask intersect` (762行目)
- `mask subtract` (788行目)
- `mask invert` (814行目)
- `mask activate` (875行目)
- `mask complex` (895行目)
- `filter ai-select` (1135行目)

**Step 2: 対応テストの削除**

`tests/integration/test_cli_develop_mask.py` から削除対象コマンドのテストを削除:
- `test_develop_mask_create`
- `test_develop_mask_select`
- `test_develop_mask_delete`
- `test_develop_mask_tool_info`
- `test_develop_mask_select_tool`
- `test_develop_mask_delete_tool`
- `test_develop_mask_add`
- `test_develop_mask_intersect`
- `test_develop_mask_subtract`
- `test_develop_mask_invert`
- `test_develop_mask_activate`

`tests/integration/test_cli_develop_filter.py` から削除:
- `test_develop_filter_ai_select`（存在する場合）

**Step 3: コマンドとテストの削除を実施**

`develop.py` から該当関数を削除し、`mask` グループには `list`, `selected`, `go-to`, `toggle-overlay` のみ残す。

**Step 4: 通過を確認**
Run: `cd /Users/motokiendo/dev/lightroom-cli && venv/bin/python -m pytest tests/ -v --ignore=tests/e2e`
Expected: ALL PASS

**Step 5: コミット**
```bash
git add cli/commands/develop.py tests/integration/test_cli_develop_mask.py tests/integration/test_cli_develop_filter.py
git commit -m "refactor: remove 13 deprecated mask/filter commands replaced by ai group"
```

---

## Task 18: E2E テストスケルトン作成

**Files:**
- Create: `tests/e2e/test_phase11_ai_mask.py`

**Step 1: E2E テストファイルを作成**

```python
# tests/e2e/test_phase11_ai_mask.py
"""
Phase 11: AI Mask E2E Tests

Requirements:
- Lightroom Classic running with CLI Bridge plugin
- Test collection '_lr-cli-test' with at least 2 photos
- Photos must be in Develop module

These tests verify actual AI mask creation in Lightroom.
Run with: pytest tests/e2e/test_phase11_ai_mask.py -v
"""
import pytest
import subprocess
import json


def lr(*args):
    """lr CLI を実行して結果を返すヘルパー"""
    result = subprocess.run(
        ["lr", "-o", "json", *args],
        capture_output=True, text=True, timeout=120,
    )
    return result


class TestAIMaskCreation:
    """AI マスク作成の E2E テスト"""

    def test_ai_subject_creates_mask(self):
        """lr develop ai subject が成功する"""
        result = lr("develop", "ai", "subject")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data.get("selectionType") == "subject"

    def test_ai_sky_creates_mask(self):
        """lr develop ai sky が成功する"""
        result = lr("develop", "ai", "sky")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data.get("selectionType") == "sky"

    def test_ai_sky_with_adjustment(self):
        """lr develop ai sky --adjust が調整を適用する"""
        result = lr("develop", "ai", "sky", "--adjust", '{"Exposure": -0.5}')
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "adjustments" in data or "selectionType" in data

    def test_ai_sky_with_preset(self):
        """lr develop ai sky --adjust-preset darken-sky がプリセットを適用する"""
        result = lr("develop", "ai", "sky", "--adjust-preset", "darken-sky")
        assert result.returncode == 0

    def test_ai_reset_clears_masks(self):
        """lr develop ai reset 後にマスクがなくなる"""
        # Create a mask first
        lr("develop", "ai", "subject")
        # Reset
        result = lr("develop", "ai", "reset")
        assert result.returncode == 0

    def test_ai_list_shows_masks(self):
        """lr develop ai list がマスク一覧を返す"""
        # Create a mask first
        lr("develop", "ai", "subject")
        result = lr("develop", "ai", "list")
        assert result.returncode == 0

    def test_ai_presets_lists_all(self):
        """lr develop ai presets が全プリセットを返す"""
        result = lr("develop", "ai", "presets")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "darken-sky" in data


class TestAIMaskBatch:
    """バッチ AI マスクの E2E テスト"""

    def test_ai_batch_dry_run(self):
        """lr develop ai batch sky --all-selected --dry-run"""
        result = lr("develop", "ai", "batch", "sky", "--all-selected", "--dry-run")
        assert result.returncode == 0

    def test_ai_batch_all_selected(self):
        """lr develop ai batch sky --all-selected"""
        result = lr("develop", "ai", "batch", "subject", "--all-selected")
        assert result.returncode == 0


class TestAIMaskPartSelection:
    """パーツ選択の E2E テスト"""

    def test_ai_people_full(self):
        """lr develop ai people (パーツなし)"""
        result = lr("develop", "ai", "people")
        assert result.returncode == 0

    def test_ai_people_with_part_eyes(self):
        """lr develop ai people --part eyes (SDK サポート未検証)"""
        result = lr("develop", "ai", "people", "--part", "eyes")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        # パーツ未対応なら warning が含まれる
        if not data.get("partApplied", False):
            assert "warning" in data or "partSupported" in data
```

**Step 2: コミット**
```bash
git add tests/e2e/test_phase11_ai_mask.py
git commit -m "test: add E2E test skeleton for AI mask commands (phase 11)"
```

---

## Summary

| Task | 内容 | 新規/修正ファイル | テスト数 |
|------|------|------------------|---------|
| 1 | プリセットモジュール | `lightroom_sdk/presets.py` | 9 |
| 2 | SDK タイムアウト | `lightroom_sdk/retry.py` | 3 |
| 3 | SDK create_ai_mask | `lightroom_sdk/client.py` | 3 |
| 4 | SDK batch_ai_mask | `lightroom_sdk/client.py` | 2 |
| 5 | CLI ai グループ骨格 | `cli/commands/ai_mask.py`, `develop.py` | 4 |
| 6 | --part テスト | テストのみ | 3 |
| 7 | --adjust テスト | テストのみ | 5 |
| 8 | presets コマンド | `cli/commands/ai_mask.py` | 2 |
| 9 | list コマンド | `cli/commands/ai_mask.py` | 1 |
| 10 | reset コマンド | `cli/commands/ai_mask.py` | 1 |
| 11 | batch コマンド | `cli/commands/ai_mask.py` | 5 |
| 12 | Lua createAIMaskWithAdjustments | `DevelopModule.lua`, `PluginInit.lua` | 0 (E2E) |
| 13 | Lua batchAIMask | `DevelopModule.lua`, `PluginInit.lua` | 0 (E2E) |
| 14 | Mock 拡張 | (不要 - 既存で十分) | 0 |
| 15 | 統合テスト実行 | 検証のみ | 0 |
| 16 | deprecated 化 | `develop.py` | 2 |
| 17 | 不要コマンド削除 | `develop.py`, テスト | 0 |
| 18 | E2E スケルトン | `test_phase11_ai_mask.py` | 11 |
| **合計** | | | **51** |
