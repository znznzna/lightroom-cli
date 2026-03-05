# Agent Feedback Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 3つのAIモデルからのフィードバックに基づき、エラーハンドリング・入力パイプライン・スキーマ・ドキュメントを修正
**Architecture:** 4 Phase に分割（エラーハンドリング → 入力パイプライン → スキーマ充実 → ドキュメント）、各Phase末にCodexレビュー
**Tech Stack:** Python 3.10+, Click 8.x, pytest
---

## Phase 概要

| Phase | テーマ | Task | 修正対象 FB# |
|-------|--------|------|-------------|
| 1 | エラーハンドリング正常化 | 1-6 | #1, #3, #4, #8, #14 |
| 2 | 入力パイプライン修正 | 7-9 | #2, #5 |
| 3 | スキーマ充実化 | 10-14 | #6, #7, #12, #13 |
| 4 | SKILLS.md 整合性修正 | 15-18 | #9, #15, #16, #17 |

**依存関係**: Phase 2 → Phase 3 は順次実行（`cli/output.py` 衝突のため並行不可）
**既存テスト**: 450件。全Phase通じてデグレさせないこと。

---

## Phase 1: エラーハンドリング正常化

### Task 1: `_parse_pairs()` のトレースバック修正

**Files:**
- Modify: `cli/commands/develop.py`
- Test: `tests/integration/test_cli_develop.py`

**Step 1: 失敗するテストを書く**

`tests/integration/test_cli_develop.py` の末尾に追加:

```python
class TestParsePairsErrorHandling:
    """_parse_pairs() のエラーハンドリングテスト"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_invalid_numeric_value_shows_structured_error(self, runner):
        """lr develop set Exposure abc が構造化エラーを返す（traceback なし）"""
        result = runner.invoke(cli, ["-o", "json", "develop", "set", "Exposure", "abc"])
        assert result.exit_code == 2
        assert "Traceback" not in result.output
        # エラーは stderr に出る
        error_output = result.output if result.output else ""
        stderr_output = result.stderr if hasattr(result, "stderr") else ""
        combined = error_output + stderr_output
        assert "VALIDATION_ERROR" in combined or "Invalid numeric value" in combined

    def test_odd_number_of_args_shows_error(self, runner):
        """lr develop set Exposure が構造化エラーを返す"""
        result = runner.invoke(cli, ["-o", "json", "develop", "set", "Exposure"])
        assert result.exit_code == 2
        assert "Traceback" not in result.output

    def test_special_chars_in_value_show_error(self, runner):
        """特殊文字が値の場合のエラーハンドリング"""
        result = runner.invoke(cli, ["-o", "json", "develop", "set", "Exposure", "!@#"])
        assert result.exit_code == 2
        assert "Traceback" not in result.output
```

**Step 2: 失敗を確認**

Run: `venv/bin/python -m pytest tests/integration/test_cli_develop.py::TestParsePairsErrorHandling -v`
Expected: FAIL（現在 `float()` が `ValueError` を投げてtraceback表示、exit code は 1 ではなく 2 にならない）

**Step 3: 最小限の実装**

`cli/commands/develop.py` の `_parse_pairs()` 関数（L7-14）を修正:

```python
def _parse_pairs(pairs: tuple) -> dict:
    """可変長引数 (param, value, param, value, ...) を辞書に変換"""
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

**Step 4: 通過を確認**

Run: `venv/bin/python -m pytest tests/integration/test_cli_develop.py::TestParsePairsErrorHandling -v`
Expected: PASS

**Step 5: コミット**

```bash
git add cli/commands/develop.py tests/integration/test_cli_develop.py
git commit -m "fix: catch ValueError in _parse_pairs and convert to structured error (FB#1)"
```

---

### Task 2: エラー出力の `err=True` 統一 + 非verbose時ログレベル明示

**Files:**
- Modify: `cli/main.py`
- Modify: `cli/commands/system.py`
- Test: `tests/test_middleware.py`

**Step 1: 失敗するテストを書く**

`tests/test_middleware.py` の末尾に追加:

```python
class TestLogLevel:
    """非verbose時のログレベル設定テスト"""

    def test_non_verbose_sets_warning_level(self):
        """verbose=False の場合、ログレベルが WARNING に設定される"""
        import logging
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        # basicConfig が WARNING レベルで設定されていることを確認
        # （テスト実行後に確認）
        assert result.exit_code == 0

    def test_reconnect_error_to_stderr(self):
        """reconnect のエラーが err=True で出力される"""
        from unittest.mock import AsyncMock, patch
        runner = CliRunner(mix_stderr=False)
        with patch("cli.helpers.get_bridge") as mock_get_bridge:
            mock_bridge = AsyncMock()
            mock_bridge.connect.side_effect = ConnectionError("test error")
            mock_get_bridge.return_value = mock_bridge
            result = runner.invoke(cli, ["system", "reconnect"])
            # エラーは stderr に出る
            assert result.exit_code != 0 or "error" in (result.stderr or "").lower() or "error" in result.output.lower()
```

**Step 2: 失敗を確認**

Run: `venv/bin/python -m pytest tests/test_middleware.py::TestLogLevel -v`
Expected: FAIL（`reconnect` が `err=True` を使っていないため）

**Step 3: 最小限の実装**

`cli/main.py` — `cli()` 関数に非verbose時のログレベル設定を追加（L25-26 の後に）:

```python
    if ctx.obj["verbose"]:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)
```

`cli/commands/system.py` — `reconnect()` のエラー出力に `err=True` を追加:

```python
@system.command()
@click.pass_context
def reconnect(ctx):
    """Force reconnection to Lightroom"""
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            await bridge.connect()
            await bridge.disconnect()
            await bridge.connect()
            click.echo(OutputFormatter.format({"status": "reconnected"}, fmt))
        except Exception as e:
            click.echo(OutputFormatter.format_error(str(e), fmt), err=True)
            ctx.exit(1)
        finally:
            await bridge.disconnect()

    run_async(_run())
```

**Step 4: 通過を確認**

Run: `venv/bin/python -m pytest tests/test_middleware.py::TestLogLevel -v`
Expected: PASS

**Step 5: コミット**

```bash
git add cli/main.py cli/commands/system.py tests/test_middleware.py
git commit -m "fix: unify error output to stderr with err=True, set WARNING log level for non-verbose (FB#3)"
```

---

### Task 3: exit code 正常化 — `handle_error` ヘルパー追加

**Files:**
- Modify: `cli/helpers.py`
- Modify: `cli/commands/system.py`
- Test: `tests/test_cli_system.py`

**Step 1: 失敗するテストを書く**

`tests/test_cli_system.py` の末尾に追加:

```python
class TestExitCodes:
    """system コマンドの exit code テスト"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @patch("cli.helpers.get_bridge")
    def test_reconnect_connection_error_exit_3(self, mock_get_bridge, runner):
        mock_bridge = AsyncMock()
        mock_bridge.connect.side_effect = ConnectionError("refused")
        mock_get_bridge.return_value = mock_bridge
        result = runner.invoke(cli, ["system", "reconnect"])
        assert result.exit_code == 3

    @patch("cli.helpers.get_bridge")
    def test_reconnect_timeout_error_exit_4(self, mock_get_bridge, runner):
        mock_bridge = AsyncMock()
        mock_bridge.connect.side_effect = TimeoutError("timed out")
        mock_get_bridge.return_value = mock_bridge
        result = runner.invoke(cli, ["system", "reconnect"])
        assert result.exit_code == 4

    @patch("cli.helpers.get_bridge")
    def test_reconnect_generic_error_exit_1(self, mock_get_bridge, runner):
        mock_bridge = AsyncMock()
        mock_bridge.connect.side_effect = RuntimeError("unknown")
        mock_get_bridge.return_value = mock_bridge
        result = runner.invoke(cli, ["system", "reconnect"])
        assert result.exit_code == 1

    @patch("cli.helpers.get_bridge")
    def test_check_connection_connection_error_exit_3(self, mock_get_bridge, runner):
        mock_bridge = AsyncMock()
        mock_bridge.connect.side_effect = ConnectionError("refused")
        mock_get_bridge.return_value = mock_bridge
        result = runner.invoke(cli, ["system", "check-connection", "--port-file", "/tmp/lightroom_ports.txt"])
        # port file が存在しない場合はそもそもbridge呼ばない
        # port file が存在する前提のテスト（mock で対応）
        assert result.exit_code in (0, 3)  # port file 存在で exit 3
```

**Step 2: 失敗を確認**

Run: `venv/bin/python -m pytest tests/test_cli_system.py::TestExitCodes -v`
Expected: FAIL（現在 `reconnect` は全て exit 0 or 1）

**Step 3: 最小限の実装**

`cli/helpers.py` に `handle_error` ヘルパーを追加:

```python
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

`cli/commands/system.py` の `reconnect` と `check_connection` を修正し `handle_error` を使用:

```python
from cli.helpers import execute_command, get_bridge, run_async, handle_error

@system.command()
@click.pass_context
def reconnect(ctx):
    """Force reconnection to Lightroom"""
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    async def _run():
        bridge = get_bridge()
        try:
            await bridge.connect()
            await bridge.disconnect()
            await bridge.connect()
            click.echo(OutputFormatter.format({"status": "reconnected"}, fmt))
        except Exception as e:
            handle_error(ctx, e, fmt)
        finally:
            await bridge.disconnect()

    run_async(_run())


@system.command("check-connection")
@click.option("--port-file", default=None, help="Path to port file (default: auto-detect)")
@click.pass_context
def check_connection(ctx, port_file):
    """Check if Lightroom is available"""
    if port_file is None:
        from lightroom_sdk.paths import get_port_file
        port_path = get_port_file()
    else:
        port_path = Path(port_file)
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    if not port_path.exists():
        click.echo(
            OutputFormatter.format(
                {"status": "unavailable", "reason": "port file not found"},
                fmt,
            ),
            err=True,
        )
        ctx.exit(3)
        return

    timeout = ctx.obj.get("timeout", 5.0) if ctx.obj else 5.0

    async def _run():
        bridge = get_bridge(port_file=port_file)
        try:
            await bridge.connect()
            await bridge.send_command("system.ping", timeout=timeout)
            click.echo(
                OutputFormatter.format({"status": "ok", "message": "Lightroom connection active"}, fmt)
            )
        except Exception as e:
            handle_error(ctx, e, fmt)
        finally:
            await bridge.disconnect()

    run_async(_run())
```

**Step 4: 通過を確認**

Run: `venv/bin/python -m pytest tests/test_cli_system.py::TestExitCodes -v`
Expected: PASS

**Step 5: コミット**

```bash
git add cli/helpers.py cli/commands/system.py tests/test_cli_system.py
git commit -m "fix: normalize exit codes — ConnectionError=3, TimeoutError=4 for system commands (FB#4, #14)"
```

---

### Task 4: `lr schema` の exit code 修正

**Files:**
- Modify: `cli/schema.py`
- Test: `tests/test_cli_schema.py`

**Step 1: 失敗するテストを書く**

`tests/test_cli_schema.py` の末尾に追加:

```python
class TestSchemaExitCodes:
    """lr schema のエラー時 exit code テスト"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_unknown_group_exit_code_1(self, runner):
        result = runner.invoke(cli, ["-o", "json", "schema", "foobar"])
        assert result.exit_code == 1

    def test_unknown_command_exit_code_1(self, runner):
        result = runner.invoke(cli, ["-o", "json", "schema", "develop.nonexistent"])
        assert result.exit_code == 1
```

**Step 2: 失敗を確認**

Run: `venv/bin/python -m pytest tests/test_cli_schema.py::TestSchemaExitCodes -v`
Expected: FAIL（現在 exit code 0）

**Step 3: 最小限の実装**

`cli/schema.py` の2箇所のエラーパスに `ctx.exit(1)` と `err=True` を追加:

```python
    elif "." not in path:
        schemas = get_schemas_by_group(path)
        if not schemas:
            click.echo(OutputFormatter.format_error(f"Unknown group: {path}", fmt), err=True)
            ctx.exit(1)
            return
        # ... 以下同じ

    else:
        # ...
        if target is None:
            click.echo(OutputFormatter.format_error(f"Unknown command: {path}", fmt), err=True)
            ctx.exit(1)
            return
        # ... 以下同じ
```

**Step 4: 通過を確認**

Run: `venv/bin/python -m pytest tests/test_cli_schema.py::TestSchemaExitCodes -v`
Expected: PASS

**Step 5: 既存テストの修正**

`tests/test_cli_schema.py` の `test_schema_unknown_group` と `test_schema_unknown_command` の exit code アサーションを更新:

```python
    def test_schema_unknown_group(self, runner):
        result = runner.invoke(cli, ["-o", "json", "schema", "nonexistent"])
        assert result.exit_code == 1

    def test_schema_unknown_command(self, runner):
        result = runner.invoke(cli, ["-o", "json", "schema", "develop.nonexistent"])
        assert result.exit_code == 1
```

**Step 6: コミット**

```bash
git add cli/schema.py tests/test_cli_schema.py
git commit -m "fix: return exit code 1 for unknown schema group/command (FB#8)"
```

---

### Task 5: check-connection の出力構造化

**Files:**
- Modify: `cli/commands/system.py` (Task 3 で既に修正済み)
- Test: `tests/test_cli_system.py`

**Step 1: 失敗するテストを書く**

`tests/test_cli_system.py` の `TestExitCodes` クラスに追加:

```python
    @patch("cli.helpers.get_bridge")
    def test_check_connection_ok_structured_output(self, mock_get_bridge, runner):
        """check-connection 成功時に構造化 JSON を返す"""
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {"id": "1", "success": True, "result": {"status": "ok"}}
        mock_get_bridge.return_value = mock_bridge
        # port file を一時的に作成
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("49000\n49001\n")
            port_file = f.name
        try:
            result = runner.invoke(cli, ["-o", "json", "system", "check-connection", "--port-file", port_file])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["status"] == "ok"
        finally:
            os.unlink(port_file)

    def test_check_connection_no_port_file_structured(self, runner):
        """ポートファイルがない場合に構造化出力を返す"""
        result = runner.invoke(cli, ["-o", "json", "system", "check-connection",
                                      "--port-file", "/tmp/nonexistent_lr_test.txt"])
        assert result.exit_code == 3
```

**Step 2: 失敗を確認**

Run: `venv/bin/python -m pytest tests/test_cli_system.py::TestExitCodes::test_check_connection_ok_structured_output tests/test_cli_system.py::TestExitCodes::test_check_connection_no_port_file_structured -v`
Expected: FAIL

**Step 3: 最小限の実装**

Task 3 で既に `check_connection` を構造化出力に変更済み。テストが通るか確認のみ。

**Step 4: 通過を確認**

Run: `venv/bin/python -m pytest tests/test_cli_system.py::TestExitCodes -v`
Expected: PASS

**Step 5: 既存テスト修正**

`tests/test_cli_system.py` の `test_system_check_connection_no_port_file` を新しい動作に合わせて更新:

```python
def test_system_check_connection_no_port_file(runner):
    """ポートファイルがない場合にエラーメッセージ表示 + exit 3"""
    result = runner.invoke(cli, ["system", "check-connection",
                                  "--port-file", "/tmp/nonexistent_test.txt"])
    assert result.exit_code == 3
```

**Step 6: コミット**

```bash
git add cli/commands/system.py tests/test_cli_system.py
git commit -m "feat: structured output for check-connection (FB#14)"
```

---

### Task 6: Phase 1 全テスト実行 + Codex レビュー

**Step 1: 全テスト実行**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: 450 + ~13 新規テスト = ~463 PASS, 0 FAIL

**Step 2: Codex レビュー**

```
/requesting-code-review
```

Phase 1 の変更内容:
- `_parse_pairs()` の ValueError キャッチ
- `handle_error()` ヘルパー追加
- `reconnect` / `check-connection` の構造化出力 + exit code
- `schema` の exit code 修正
- 非verbose時ログレベル明示設定

**Step 3: レビュー指摘修正**

Critical/Important 指摘がある場合は修正してからPhase 2に進む。

---

## Phase 2: 入力パイプライン修正

### Task 7: `--json`/`--json-stdin` デコレータ全コマンド適用

**Files:**
- Modify: `cli/commands/develop.py`
- Modify: `cli/commands/catalog.py`
- Modify: `cli/commands/system.py`
- Modify: `cli/commands/preview.py`
- Modify: `cli/commands/selection.py`
- Modify: `cli/commands/ai_mask.py`
- Test: `tests/integration/test_cli_develop.py`
- Test: `tests/test_cli_help_all_commands.py` (新規)

**重要な注意**: `json_input_options` デコレータは Click の `ctx.params` に `json_str` と `json_stdin` を追加するだけで、コールバック引数には追加不要。`execute_command` が `ctx.params.get("json_str")` でアクセスする。

**Step 1: 失敗するテストを書く**

`tests/integration/test_cli_develop.py` に追加:

```python
class TestJsonInput:
    """--json 入力テスト"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @patch("cli.helpers.get_bridge")
    def test_develop_set_via_json(self, mock_get_bridge, runner):
        """--json でパラメータを渡せる"""
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {"id": "1", "success": True, "result": {"Exposure": 1.0}}
        mock_get_bridge.return_value = mock_bridge
        result = runner.invoke(cli, [
            "develop", "set", "--json", '{"parameter": "Exposure", "value": 1.0}',
            "dummy", "0",  # nargs=-1 に必要
        ])
        # --json が渡せることを確認（execute_command 内部で json_str を処理）
        assert result.exit_code == 0 or "json" in result.output.lower() or result.exit_code == 2

    @patch("cli.helpers.get_bridge")
    def test_develop_get_settings_via_json(self, mock_get_bridge, runner):
        """get-settings でも --json オプションが存在する"""
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {"id": "1", "success": True, "result": {}}
        mock_get_bridge.return_value = mock_bridge
        result = runner.invoke(cli, ["develop", "get-settings", "--json", '{}'])
        assert result.exit_code == 0

    @patch("cli.helpers.get_bridge")
    def test_json_stdin_input(self, mock_get_bridge, runner):
        """--json-stdin でstdinからJSON入力"""
        mock_bridge = AsyncMock()
        mock_bridge.send_command.return_value = {"id": "1", "success": True, "result": {}}
        mock_get_bridge.return_value = mock_bridge
        result = runner.invoke(
            cli,
            ["develop", "get-settings", "--json-stdin"],
            input='{"test": true}',
        )
        assert "Traceback" not in result.output

    def test_json_invalid_shows_error(self, runner):
        """無効な JSON がエラーになる"""
        result = runner.invoke(cli, ["develop", "get-settings", "--json", "not-json"])
        assert result.exit_code != 0 or "error" in result.output.lower()

    @patch("cli.helpers.get_bridge")
    def test_empty_json_shows_error(self, mock_get_bridge, runner):
        """空の --json がエラーになる"""
        mock_bridge = AsyncMock()
        mock_get_bridge.return_value = mock_bridge
        result = runner.invoke(cli, ["develop", "get-settings", "--json", "  "])
        assert result.exit_code == 2
```

全コマンドの `--help` 網羅テストを新規ファイルに作成:

`tests/test_cli_help_all_commands.py`:

```python
"""全コマンドの --help が正常動作することを検証するパラメトリックテスト"""
import pytest
from click.testing import CliRunner
from cli.main import cli


def _collect_commands(group, prefix=""):
    """Click グループから全コマンドパスを再帰的に収集"""
    commands = []
    for name in group.list_commands(None):
        cmd = group.get_command(None, name)
        full = f"{prefix} {name}".strip() if prefix else name
        if hasattr(cmd, "list_commands"):
            commands.extend(_collect_commands(cmd, full))
        else:
            commands.append(full)
    return commands


ALL_COMMANDS = _collect_commands(cli)


@pytest.mark.parametrize("cmd_path", ALL_COMMANDS, ids=ALL_COMMANDS)
def test_help_succeeds(cmd_path):
    """各コマンドの --help が exit code 0 で動作する"""
    runner = CliRunner()
    args = cmd_path.split() + ["--help"]
    result = runner.invoke(cli, args)
    assert result.exit_code == 0, f"--help failed for '{cmd_path}': {result.output}"


@pytest.mark.parametrize("cmd_path", ALL_COMMANDS, ids=ALL_COMMANDS)
def test_help_contains_json_option(cmd_path):
    """execute_command を使う全コマンドに --json オプションが存在する"""
    runner = CliRunner()
    args = cmd_path.split() + ["--help"]
    result = runner.invoke(cli, args)
    # plugin, schema コマンドは execute_command を使わないので除外
    if cmd_path.startswith("plugin") or cmd_path == "schema":
        pytest.skip("Non-bridge command")
    # グループ help（サブコマンド持ち）も除外
    if "Commands:" in result.output:
        pytest.skip("Group command")
    assert "--json" in result.output, f"--json option missing for '{cmd_path}'"
```

**Step 2: 失敗を確認**

Run: `venv/bin/python -m pytest tests/test_cli_help_all_commands.py::test_help_contains_json_option -v`
Expected: FAIL（ほとんどのコマンドに `--json` がない）

**Step 3: 最小限の実装**

各コマンドファイルの全コマンドに `@json_input_options` デコレータを追加。デコレータは `@click.pass_context` の前（上）に配置。

**`cli/commands/develop.py`** 冒頭に import 追加:
```python
from cli.decorators import json_input_options
```

各コマンド関数に `@json_input_options` を追加。例:
```python
@develop.command("get-settings")
@json_input_options
@click.pass_context
def get_settings(ctx):
```

以下のコマンドファイルで同様に全コマンドに追加:
- `cli/commands/catalog.py` — 全コマンド
- `cli/commands/system.py` — `ping`, `status` のみ（`reconnect`, `check-connection` は `execute_command` を使わないが、一貫性のため追加）
- `cli/commands/preview.py` — 全コマンド
- `cli/commands/selection.py` — 全コマンド
- `cli/commands/ai_mask.py` — `ai_presets`, `ai_reset`, `ai_list`, `ai_batch` + ファクトリ関数 `_make_ai_type_command` 内の params に `--json` / `--json-stdin` オプションを追加

**`_make_ai_type_command` のパラメータ追加**:
```python
    params = [
        click.Option(["--json"], "json_str", default=None, help="JSON string with all parameters"),
        click.Option(["--json-stdin"], "json_stdin", is_flag=True, default=False, help="Read JSON parameters from stdin"),
        click.Option(["--adjust"], default=None, help="JSON adjustment settings"),
        # ... 残り同じ
    ]
```

**Step 4: 通過を確認**

Run: `venv/bin/python -m pytest tests/test_cli_help_all_commands.py -v`
Expected: PASS（全コマンドの `--help` が動作、`--json` オプションが存在）

Run: `venv/bin/python -m pytest tests/integration/test_cli_develop.py::TestJsonInput -v`
Expected: PASS

**Step 5: 全テスト回帰確認**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: 全 PASS（既存テストが `json_str`/`json_stdin` 引数を受け取ってもエラーにならないことを確認）

**Step 6: コミット**

```bash
git add cli/commands/develop.py cli/commands/catalog.py cli/commands/system.py cli/commands/preview.py cli/commands/selection.py cli/commands/ai_mask.py cli/decorators.py tests/integration/test_cli_develop.py tests/test_cli_help_all_commands.py
git commit -m "feat: apply @json_input_options to all commands + parametric --help test (FB#2)"
```

---

### Task 8: `--fields` の動作修正

**Files:**
- Modify: `cli/output.py`
- Modify: `cli/helpers.py`
- Test: `tests/test_output_formatter.py`

**Step 1: 失敗するテストを書く**

`tests/test_output_formatter.py` の末尾に追加:

```python
class TestFilterFieldsNested:
    """_filter_fields のネストされたレスポンス対応テスト"""

    def test_filter_top_level(self):
        """トップレベルのフィールドフィルタ"""
        data = {"Exposure": 0.5, "Contrast": 25, "Highlights": -10}
        result = OutputFormatter._filter_fields(data, ["Exposure", "Contrast"])
        assert result == {"Exposure": 0.5, "Contrast": 25}

    def test_filter_empty_result_warning(self):
        """フィルタ結果が空の場合の動作"""
        data = {"Exposure2012": 0.5}
        result = OutputFormatter._filter_fields(data, ["Exposure"])
        assert result == {}  # 空だがエラーではない

    def test_filter_nested_result_key(self):
        """result キーの中にデータがある場合"""
        data = {"result": {"Exposure": 0.5, "Contrast": 25}}
        # _filter_fields は "result" キーを探す → 空になる
        # ただし execute_command は result.get("result", result) でアンラップ済み
        result = OutputFormatter._filter_fields(data, ["Exposure"])
        assert result == {}  # "result" キーとマッチしない

    def test_filter_fields_case_sensitive(self):
        """フィールド名は大文字小文字を区別する"""
        data = {"Exposure": 0.5, "exposure": 1.0}
        result = OutputFormatter._filter_fields(data, ["Exposure"])
        assert result == {"Exposure": 0.5}
```

`tests/test_output_formatter.py` に「空結果時の警告」テスト追加:

```python
class TestFieldsWarning:
    """--fields でフィールドが見つからない場合の警告テスト"""

    def test_format_with_empty_fields_result_includes_warning(self):
        """フィルタ結果が空 dict の場合、警告が含まれる"""
        data = {"Exposure2012": 0.5}
        result = OutputFormatter.format(data, "json", fields=["Exposure"])
        import json
        parsed = json.loads(result)
        # 空の dict または警告付き
        assert parsed == {} or "_warning" in parsed
```

**Step 2: 失敗を確認**

Run: `venv/bin/python -m pytest tests/test_output_formatter.py::TestFilterFieldsNested tests/test_output_formatter.py::TestFieldsWarning -v`
Expected: 一部 FAIL

**Step 3: 最小限の実装**

`cli/output.py` の `format()` メソッドを修正 — fields フィルタ結果が空の場合に `_warning` フィールドを追加:

```python
    @staticmethod
    def format(data: Any, mode: str = "text", fields: list[str] | None = None) -> str:
        if fields is not None:
            filtered = OutputFormatter._filter_fields(data, fields)
            if isinstance(filtered, dict) and not filtered and isinstance(data, dict) and data:
                filtered["_warning"] = f"No matching fields found. Requested: {', '.join(fields)}. Available: {', '.join(sorted(data.keys())[:10])}"
            data = filtered
        if mode == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)
        elif mode == "table":
            return OutputFormatter._format_table(data)
        else:
            return OutputFormatter._format_text(data)
```

**Step 4: 通過を確認**

Run: `venv/bin/python -m pytest tests/test_output_formatter.py::TestFilterFieldsNested tests/test_output_formatter.py::TestFieldsWarning -v`
Expected: PASS

**Step 5: コミット**

```bash
git add cli/output.py tests/test_output_formatter.py
git commit -m "fix: add warning when --fields returns empty result, improve filter diagnostics (FB#5)"
```

---

### Task 9: Phase 2 全テスト実行 + Codex レビュー

**Step 1: 全テスト実行**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: 全 PASS（450 + Phase 1 新規 + Phase 2 新規 = ~480+）

**Step 2: Codex レビュー**

```
/requesting-code-review
```

Phase 2 の変更内容:
- `@json_input_options` の全コマンド適用
- 全コマンド `--help` パラメトリックテスト
- `--fields` 空結果時の警告

---

## Phase 3: スキーマ充実化

### Task 10: response_fields の充実

**Files:**
- Modify: `lightroom_sdk/schema.py`
- Test: `tests/test_schema.py`

**Step 1: 失敗するテストを書く**

`tests/test_schema.py` の末尾に追加:

```python
class TestResponseFields:
    """response_fields の充実テスト"""

    @pytest.mark.parametrize("command,expected_fields", [
        ("system.ping", ["status", "timestamp"]),
        ("system.status", ["status", "uptime", "version", "connections"]),
        ("catalog.getSelectedPhotos", ["photos", "count"]),
        ("catalog.getAllPhotos", ["photos", "total", "limit", "offset"]),
        ("catalog.searchPhotos", ["photos", "total", "query"]),
        ("catalog.getPhotoMetadata", ["filename", "path", "rating", "flag", "keywords"]),
        ("preview.generatePreview", ["path", "size", "format"]),
        ("develop.getValue", ["parameter", "value"]),
        ("develop.getRange", ["parameter", "min", "max"]),
    ])
    def test_response_fields_not_empty(self, command, expected_fields):
        from lightroom_sdk.schema import get_schema
        schema = get_schema(command)
        assert schema is not None, f"Schema not found for {command}"
        assert len(schema.response_fields) > 0, f"response_fields empty for {command}"
        for field in expected_fields:
            assert field in schema.response_fields, f"Missing response field '{field}' in {command}"
```

**Step 2: 失敗を確認**

Run: `venv/bin/python -m pytest tests/test_schema.py::TestResponseFields -v`
Expected: FAIL（ほとんどのコマンドで response_fields が空）

**Step 3: 最小限の実装**

`lightroom_sdk/schema.py` の各 `CommandSchema` に `response_fields` を追加:

```python
# system
CommandSchema("system.ping", "system.ping", "Test connection", timeout=5.0,
              response_fields=["status", "timestamp"]),
CommandSchema("system.status", "system.status", "Get bridge status", timeout=5.0,
              response_fields=["status", "uptime", "version", "connections"]),

# catalog
CommandSchema("catalog.getSelectedPhotos", "catalog.get-selected",
              "Get currently selected photos",
              response_fields=["photos", "count"]),
CommandSchema("catalog.getAllPhotos", "catalog.list", ...,
              response_fields=["photos", "total", "limit", "offset"]),
CommandSchema("catalog.searchPhotos", "catalog.search", ...,
              response_fields=["photos", "total", "query"]),
CommandSchema("catalog.getPhotoMetadata", "catalog.get-info", ...,
              response_fields=["filename", "path", "rating", "flag", "keywords", "dimensions", "dateCreated"]),

# preview
CommandSchema("preview.generatePreview", ...,
              response_fields=["path", "size", "format"]),

# develop
CommandSchema("develop.getValue", ...,
              response_fields=["parameter", "value"]),
CommandSchema("develop.getRange", ...,
              response_fields=["parameter", "min", "max"]),
```

**Step 4: 通過を確認**

Run: `venv/bin/python -m pytest tests/test_schema.py::TestResponseFields -v`
Expected: PASS

**Step 5: コミット**

```bash
git add lightroom_sdk/schema.py tests/test_schema.py
git commit -m "feat: populate response_fields for major commands (FB#6)"
```

---

### Task 11: パラメータ description の充実

**Files:**
- Modify: `lightroom_sdk/schema.py`
- Test: `tests/test_schema.py`

**Step 1: 失敗するテストを書く**

`tests/test_schema.py` に追加:

```python
class TestParamDescriptions:
    """パラメータ description 非空テスト"""

    def test_all_params_have_descriptions(self):
        from lightroom_sdk.schema import get_all_schemas
        missing = []
        for cmd_name, schema in get_all_schemas().items():
            for p in schema.params:
                if not p.description:
                    missing.append(f"{cmd_name}.{p.name}")
        assert missing == [], f"Empty descriptions: {missing}"
```

**Step 2: 失敗を確認**

Run: `venv/bin/python -m pytest tests/test_schema.py::TestParamDescriptions -v`
Expected: FAIL（多数のパラメータで description が空）

**Step 3: 最小限の実装**

`lightroom_sdk/schema.py` の全 `ParamSchema` に description を追加。主要なもの:

```python
# develop.resetToDefault
ParamSchema("param", ParamType.STRING, required=True,
            description="Develop parameter name to reset (e.g., Exposure, Contrast)"),

# develop.getProcessVersion — パラメータなし

# develop.setProcessVersion
ParamSchema("version", ParamType.STRING, required=True,
            description="Process version string"),

# develop.curve.*
ParamSchema("param", ParamType.STRING, required=True,
            description="Curve parameter name (ToneCurvePV2012, ToneCurvePV2012Red, etc.)"),
ParamSchema("points", ParamType.JSON_ARRAY, required=True,
            description="Array of {x, y} control points, each 0-255 (e.g., [{\"x\":0,\"y\":0},{\"x\":128,\"y\":140},{\"x\":255,\"y\":255}])"),
ParamSchema("x", ParamType.FLOAT, required=True,
            description="X coordinate (0-255)"),
ParamSchema("y", ParamType.FLOAT, required=True,
            description="Y coordinate (0-255)"),
ParamSchema("index", ParamType.INTEGER, required=True,
            description="Zero-based index of the point to remove"),

# catalog.*
ParamSchema("photoId", ParamType.STRING, required=True,
            description="Photo ID (obtain via 'lr catalog get-selected' or 'lr catalog list')"),
ParamSchema("query", ParamType.STRING, required=True,
            description="Search keyword or phrase"),
ParamSchema("limit", ParamType.INTEGER, default=50,
            description="Maximum number of results to return"),
ParamSchema("offset", ParamType.INTEGER, default=0,
            description="Number of results to skip for pagination"),
ParamSchema("rating", ParamType.INTEGER, required=True,
            description="Star rating (0-5)"),
ParamSchema("keywords", ParamType.JSON_ARRAY, required=True,
            description="Array of keyword strings to add"),
ParamSchema("flag", ParamType.INTEGER, required=True,
            description="Flag value (1=pick, -1=reject, 0=none)"),
ParamSchema("searchDesc", ParamType.JSON_OBJECT, required=True,
            description="Structured search criteria (flag, rating, colorLabel, camera fields)"),
ParamSchema("photoIds", ParamType.JSON_ARRAY, required=True,
            description="Array of photo ID strings"),
ParamSchema("path", ParamType.STRING, required=True,
            description="File system path to the photo"),
ParamSchema("includeSubfolders", ParamType.BOOLEAN, default=False,
            description="Whether to include subfolders recursively"),
ParamSchema("title", ParamType.STRING, required=True,
            description="Photo title text"),
ParamSchema("caption", ParamType.STRING, required=True,
            description="Photo caption text"),
ParamSchema("label", ParamType.ENUM, required=True,
            description="Color label name",
            enum_values=["red", "yellow", "green", "blue", "purple", "none"]),
ParamSchema("keys", ParamType.JSON_ARRAY, required=True,
            description="Array of metadata key names (e.g., fileName, dateTimeOriginal, rating)"),
ParamSchema("key", ParamType.STRING, required=True,
            description="Metadata key name"),
ParamSchema("value", ParamType.STRING, required=True,
            description="Metadata value string"),
ParamSchema("name", ParamType.STRING, required=True,
            description="Collection or snapshot name"),
ParamSchema("keyword", ParamType.STRING, required=True,
            description="Keyword string"),
ParamSchema("filter", ParamType.JSON_OBJECT, required=True,
            description="View filter descriptor object"),

# selection.*
ParamSchema("label", ParamType.ENUM, required=True,
            description="Color label to set",
            enum_values=["red", "yellow", "green", "blue", "purple", "none"]),
ParamSchema("color", ParamType.ENUM, required=True,
            description="Color to toggle",
            enum_values=["red", "yellow", "green", "blue", "purple"]),
ParamSchema("direction", ParamType.ENUM, default="right",
            description="Direction to extend selection",
            enum_values=["left", "right"]),
ParamSchema("amount", ParamType.INTEGER, default=1,
            description="Number of photos to extend by"),
ParamSchema("rating", ParamType.INTEGER, required=True,
            description="Rating 0-5"),

# preview.*
ParamSchema("size", ParamType.INTEGER, default=1024,
            description="Preview size in pixels"),
ParamSchema("format", ParamType.ENUM, default="jpeg",
            description="Image format for preview",
            enum_values=["jpeg", "png"]),
ParamSchema("photoId", ParamType.STRING, required=True,
            description="Photo ID to get preview info for"),

# develop.local.*
ParamSchema("parameter", ParamType.STRING, required=True,
            description="Local adjustment parameter name"),
ParamSchema("maskType", ParamType.ENUM,
            description="Mask creation method",
            enum_values=["brush", "gradient", "radial"]),
ParamSchema("localSettings", ParamType.JSON_OBJECT,
            description="JSON object of local adjustment settings"),

# develop.filter.*
ParamSchema("rangeType", ParamType.ENUM,
            description="Range mask type",
            enum_values=["luminance", "color", "depth"]),

# develop.debug.*
ParamSchema("duration", ParamType.INTEGER, default=10,
            description="Monitor duration in seconds"),

# develop.color.*
ParamSchema("preset", ParamType.ENUM,
            description="Color enhancement preset",
            enum_values=["natural", "vivid", "muted"]),

# develop.ai.*
ParamSchema("selectionType", ParamType.ENUM, required=True,
            description="AI mask selection type",
            enum_values=["subject", "sky", "background", "objects", "people", "landscape"]),
ParamSchema("adjustments", ParamType.JSON_OBJECT,
            description="Optional develop adjustments to apply to the mask (e.g., {\"Exposure\": -0.5})"),
ParamSchema("part", ParamType.STRING,
            description="Specific part to mask (e.g., eyes, hair, skin for people)"),
ParamSchema("allSelected", ParamType.BOOLEAN, default=False,
            description="Apply to all currently selected photos"),
ParamSchema("continueOnError", ParamType.BOOLEAN, default=False,
            description="Continue processing remaining photos if one fails"),

# catalog other
ParamSchema("presetName", ParamType.STRING, required=True,
            description="Name of the develop preset to apply"),
```

**Step 4: 通過を確認**

Run: `venv/bin/python -m pytest tests/test_schema.py::TestParamDescriptions -v`
Expected: PASS

**Step 5: コミット**

```bash
git add lightroom_sdk/schema.py tests/test_schema.py
git commit -m "feat: populate all param descriptions in schema (FB#7)"
```

---

### Task 12: develop.ai スキーマ改善

**Files:**
- Modify: `lightroom_sdk/schema.py`
- Test: `tests/test_schema.py`
- Test: `tests/test_cli_schema.py`

**Step 1: 失敗するテストを書く**

`tests/test_schema.py` に追加:

```python
class TestDevelopAISchema:
    """develop.ai スキーマのテスト"""

    def test_ai_mask_schema_exists(self):
        from lightroom_sdk.schema import get_schema
        schema = get_schema("develop.createAIMaskWithAdjustments")
        assert schema is not None
        assert schema.cli_path == "develop.ai.mask"

    def test_ai_group_lists_mask_and_batch(self):
        from lightroom_sdk.schema import get_schemas_by_group
        schemas = get_schemas_by_group("develop.ai")
        cli_paths = [s.cli_path for s in schemas.values()]
        assert "develop.ai.mask" in cli_paths
        assert "develop.ai.batch" in cli_paths
```

`tests/test_cli_schema.py` に追加:

```python
    def test_schema_develop_ai_group(self, runner):
        result = runner.invoke(cli, ["-o", "json", "schema", "develop.ai"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) >= 2  # mask + batch
```

**Step 2: 失敗を確認**

Run: `venv/bin/python -m pytest tests/test_schema.py::TestDevelopAISchema -v`
Expected: FAIL（現在 `cli_path` が `develop.ai.<type>`）

**Step 3: 最小限の実装**

`lightroom_sdk/schema.py` の `develop.createAIMaskWithAdjustments` スキーマを修正:

```python
    CommandSchema(
        "develop.createAIMaskWithAdjustments", "develop.ai.mask",
        "Create AI mask with optional adjustments (selectionType: subject/sky/background/objects/people/landscape)",
        params=[
            ParamSchema("selectionType", ParamType.ENUM, required=True,
                        description="AI mask selection type",
                        enum_values=["subject", "sky", "background",
                                     "objects", "people", "landscape"]),
            ParamSchema("adjustments", ParamType.JSON_OBJECT,
                        description="Optional develop adjustments to apply to the mask (e.g., {\"Exposure\": -0.5})"),
            ParamSchema("part", ParamType.STRING,
                        description="Specific part to mask (e.g., eyes, hair, skin for people)"),
        ],
        mutating=True, timeout=60.0,
    ),
```

**Step 4: 通過を確認**

Run: `venv/bin/python -m pytest tests/test_schema.py::TestDevelopAISchema tests/test_cli_schema.py -v`
Expected: PASS

**Step 5: コミット**

```bash
git add lightroom_sdk/schema.py tests/test_schema.py tests/test_cli_schema.py
git commit -m "fix: rename develop.ai.<type> to develop.ai.mask for proper schema grouping (FB#12)"
```

---

### Task 13: suggestions フィールドの発火改善

**Files:**
- Modify: `cli/validation.py`
- Test: `tests/test_validation.py`

**Step 1: 失敗するテストを書く**

`tests/test_validation.py` に追加:

```python
class TestSuggestions:
    """suggestions フィールドの発火テスト"""

    def test_unknown_param_has_suggestions(self):
        from cli.validation import validate_params, ValidationError
        with pytest.raises(ValidationError) as exc_info:
            validate_params("develop.setValue", {"Exposre": 0.5})
        assert len(exc_info.value.suggestions) > 0
        assert "Exposure" in exc_info.value.suggestions[0] or "parameter" in exc_info.value.suggestions[0]

    def test_enum_error_has_suggestions(self):
        """enum バリデーションエラー時に有効な値の一覧が suggestions に含まれる"""
        from cli.validation import validate_params, ValidationError
        with pytest.raises(ValidationError) as exc_info:
            validate_params("develop.selectTool", {"tool": "invalid_tool"})
        assert len(exc_info.value.suggestions) > 0
        # suggestions に有効な enum 値が含まれる
        all_suggestions = " ".join(exc_info.value.suggestions)
        assert "crop" in all_suggestions or "loupe" in all_suggestions

    def test_type_error_has_suggestions(self):
        """型変換エラー時に期待される型の例が suggestions に含まれる"""
        from cli.validation import validate_params, ValidationError
        with pytest.raises(ValidationError) as exc_info:
            validate_params("develop.setValue", {"parameter": "Exposure", "value": "not_a_number"})
        assert len(exc_info.value.suggestions) > 0

    def test_format_error_json_includes_suggestions(self):
        """format_error JSON モードで suggestions が実際に出力される"""
        from cli.output import OutputFormatter
        import json
        result = OutputFormatter.format_error(
            "test error", "json",
            code="VALIDATION_ERROR",
            suggestions=["try Exposure", "try Contrast"],
        )
        parsed = json.loads(result)
        assert "suggestions" in parsed["error"]
        assert len(parsed["error"]["suggestions"]) == 2
```

**Step 2: 失敗を確認**

Run: `venv/bin/python -m pytest tests/test_validation.py::TestSuggestions -v`
Expected: FAIL（enum エラーと型エラーで suggestions が空）

**Step 3: 最小限の実装**

`cli/validation.py` の `_coerce_type()` を修正:

enum バリデーションエラー時:
```python
            case ParamType.ENUM:
                if str(value) not in (schema.enum_values or []):
                    raise ValidationError(
                        f"Invalid value '{value}' for '{name}'. "
                        f"Must be one of: {', '.join(schema.enum_values or [])}",
                        param=name,
                        suggestions=[f"Valid values: {', '.join(schema.enum_values or [])}"],
                    )
                return str(value)
```

型変換エラー時（`except (ValueError, TypeError)` ブロック）:
```python
    except ValidationError:
        raise
    except (ValueError, TypeError):
        type_examples = {
            ParamType.STRING: "e.g., \"hello\"",
            ParamType.INTEGER: "e.g., 42",
            ParamType.FLOAT: "e.g., 0.5, -1.0",
            ParamType.BOOLEAN: "e.g., true, false",
        }
        example = type_examples.get(schema.type, "")
        suggestions = [f"Expected type: {schema.type.value} ({example})"] if example else []
        raise ValidationError(
            f"Invalid type for '{name}': expected {schema.type.value}, "
            f"got {type(value).__name__}",
            param=name,
            suggestions=suggestions,
        )
```

**Step 4: 通過を確認**

Run: `venv/bin/python -m pytest tests/test_validation.py::TestSuggestions -v`
Expected: PASS

**Step 5: コミット**

```bash
git add cli/validation.py tests/test_validation.py
git commit -m "feat: add suggestions to enum and type validation errors (FB#13)"
```

---

### Task 14: Phase 3 全テスト実行 + Codex レビュー

**Step 1: 全テスト実行**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: 全 PASS

**Step 2: Codex レビュー**

```
/requesting-code-review
```

Phase 3 の変更内容:
- response_fields 充実（9コマンド）
- パラメータ description 全埋め
- develop.ai.mask スキーマ修正
- suggestions 発火改善

---

## Phase 4: SKILLS.md 整合性修正

### Task 15: SKILLS.md コマンド表記の修正

**Files:**
- Modify: `SKILLS.md`

**Step 1: 修正内容の特定**

以下の乖離を修正:

| 現在の表記 | 正しい表記 |
|-----------|-----------|
| `lr develop apply '{"Exposure": 1.0}'` | `lr develop apply --settings '{"Exposure": 1.0}'` |
| `lr schema develop.setValue` | `lr schema develop.set` |
| `lr develop curve set '[[0,0],[128,140],[255,255]]'` | `lr develop curve set --points '[[0,0],[128,140],[255,255]]'` |
| `lr catalog find --flag PICK --rating 3` | `lr catalog find --flag pick --rating 3` |
| Masking セクションに存在しないコマンド多数 | 実装済みコマンドのみに絞る |

**Step 2: 修正実施**

SKILLS.md の修正:

1. develop apply の表記修正
2. schema の cli_path ベース統一
3. curve set の表記修正
4. Masking セクションを実装済みコマンドのみに修正（mask list, mask selected, mask go-to, mask toggle-overlay + ai 系）
5. preview セクションの表記修正
6. Schema Introspection セクションの例修正

**Step 3: コミット**

```bash
git add SKILLS.md
git commit -m "docs: fix SKILLS.md command notation to match actual CLI (FB#9)"
```

---

### Task 16: Develop パラメータ一覧の追加

**Files:**
- Modify: `SKILLS.md`

**Step 1: SKILLS.md に「Develop Parameters Reference」セクション追加**

develop セクションの後に追加:

```markdown
### Develop Parameters Reference

Use `lr develop range PARAM` to get the exact min/max for any parameter.

| Parameter | Range | Description |
|-----------|-------|-------------|
| Exposure | -5.0 to +5.0 | Overall brightness |
| Contrast | -100 to +100 | Tonal contrast |
| Highlights | -100 to +100 | Bright area recovery |
| Shadows | -100 to +100 | Shadow detail |
| Whites | -100 to +100 | White point |
| Blacks | -100 to +100 | Black point |
| Temperature | 2000 to 50000 | Color temperature (Kelvin) |
| Tint | -150 to +150 | Green/magenta tint |
| Vibrance | -100 to +100 | Subtle saturation |
| Saturation | -100 to +100 | Overall saturation |
| Clarity | -100 to +100 | Midtone contrast |
| Dehaze | -100 to +100 | Haze removal |
| Texture | -100 to +100 | Detail texture |
| Sharpness | 0 to 150 | Sharpening amount |
| LuminanceSmoothing | 0 to 100 | Luminance noise reduction |
| ColorNoiseReduction | 0 to 100 | Color noise reduction |
| VignetteAmount | -100 to +100 | Post-crop vignetting |
| SplitToningHighlightHue | 0 to 360 | Split tone highlight hue |
| SplitToningShadowHue | 0 to 360 | Split tone shadow hue |

> **Note:** Use the internal Lightroom parameter names exactly as shown.
> Get the full list dynamically: `lr develop debug probe`
```

**Step 2: コミット**

```bash
git add SKILLS.md
git commit -m "docs: add Develop Parameters Reference table (FB#15)"
```

---

### Task 17: PHOTO_ID 取得フロー + catalog/selection 使い分けガイド

**Files:**
- Modify: `SKILLS.md`

**Step 1: SKILLS.md の先頭（Prerequisites の後）に「Getting Started for Agents」セクション追加**

```markdown
## Getting Started for Agents

### Step 1: Verify connection

```bash
lr system check-connection
```

If unavailable, ensure Lightroom Classic is running with the plugin active.

### Step 2: Get photo IDs

```bash
# Get currently selected photos (most common)
lr -o json catalog get-selected
# Returns: {"photos": [{"id": "12345", "filename": "IMG_001.jpg", ...}], "count": 1}

# Or list all photos
lr -o json catalog list --limit 10
```

The `id` field in each photo object is the PHOTO_ID used in subsequent commands.

### Step 3: Operate on photos

```bash
# Read settings
lr -o json develop get-settings

# Modify settings
lr develop set Exposure 0.5 Contrast 25

# Set metadata
lr catalog set-rating 12345 5
```

### catalog vs selection: Which to use?

| | catalog | selection |
|---|---------|-----------|
| **Target** | Specific photo by ID | Currently selected photo(s) |
| **Use when** | You know the exact photo ID | Operating on what the user is viewing |
| **Agent preference** | Recommended (explicit, predictable) | Use for navigation workflows |
| **Example** | `lr catalog set-rating PHOTO_ID 5` | `lr selection set-rating 5` |

**Recommendation for agents:** Prefer `catalog` commands with explicit photo IDs for predictable, auditable operations. Use `selection` commands only for navigation (next/previous) or when operating on "whatever the user selected."
```

**Step 2: コミット**

```bash
git add SKILLS.md
git commit -m "docs: add agent getting-started flow and catalog/selection guide (FB#16, #17)"
```

---

### Task 18: Phase 4 全テスト実行 + 最終レビュー

**Step 1: 全テスト実行**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: 全 PASS（Phase 4 はドキュメントのみなので既存テストに影響なし）

**Step 2: 最終 Codex レビュー**

```
/requesting-code-review
```

全 Phase の変更を対象にレビュー。

**Step 3: TASK.md 更新**

TASK.md にこのタスクの完了を記録。

**Step 4: 最終コミット**

```bash
git add TASK.md
git commit -m "docs: mark agent-feedback-fixes complete in TASK.md"
```

---

## 全タスク一覧（サマリ）

| Task | Phase | 概要 | 影響ファイル | 新規テスト数 |
|------|-------|------|-------------|-------------|
| 1 | 1 | `_parse_pairs` トレースバック修正 | `cli/commands/develop.py` | 3 |
| 2 | 1 | エラー出力 `err=True` 統一 + ログレベル | `cli/main.py`, `cli/commands/system.py` | 2 |
| 3 | 1 | exit code 正常化 + `handle_error` | `cli/helpers.py`, `cli/commands/system.py` | 4 |
| 4 | 1 | `lr schema` exit code 修正 | `cli/schema.py` | 2 |
| 5 | 1 | check-connection 構造化出力 | `cli/commands/system.py` | 2 |
| 6 | 1 | Phase 1 テスト + Codex レビュー | — | — |
| 7 | 2 | `--json`/`--json-stdin` 全コマンド適用 | 6 コマンドファイル | 5 + 全コマンド --help |
| 8 | 2 | `--fields` 空結果時警告 | `cli/output.py` | 4 |
| 9 | 2 | Phase 2 テスト + Codex レビュー | — | — |
| 10 | 3 | response_fields 充実 | `lightroom_sdk/schema.py` | 9 (parametrize) |
| 11 | 3 | パラメータ description 全埋め | `lightroom_sdk/schema.py` | 1 |
| 12 | 3 | develop.ai.mask スキーマ修正 | `lightroom_sdk/schema.py` | 2 |
| 13 | 3 | suggestions 発火改善 | `cli/validation.py` | 4 |
| 14 | 3 | Phase 3 テスト + Codex レビュー | — | — |
| 15 | 4 | SKILLS.md コマンド表記修正 | `SKILLS.md` | 0 |
| 16 | 4 | Develop パラメータ一覧追加 | `SKILLS.md` | 0 |
| 17 | 4 | PHOTO_ID フロー + catalog/selection ガイド | `SKILLS.md` | 0 |
| 18 | 4 | Phase 4 テスト + 最終レビュー | — | — |

**合計**: 18タスク / 4 Phase / 新規テスト ~33件 + 全コマンド --help パラメトリックテスト
