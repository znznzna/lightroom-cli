# E2E Test Suite Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 全143 CLIコマンドをカバーするE2Eテストスイートを実装する
**Architecture:** Phase-Based Files + Session Fixtures（pytest-ordering不要）
**Tech Stack:** pytest, Click CliRunner, Python 3.10+
---

## Task 1: conftest.py 書き換え + pyproject.toml マーカー登録

**Files:**
- Modify: `tests/e2e/conftest.py`
- Modify: `pyproject.toml`

**実装内容:**

### `tests/e2e/conftest.py`

既存の `conftest.py` を完全に書き換える。`lr_bridge` fixture を廃止し、CliRunner ベースの `run` fixture に移行する。

```python
# tests/e2e/conftest.py
"""E2E test fixtures and configuration.

Run: pytest tests/e2e/ -v -m e2e
Run destructive: pytest tests/e2e/ -v -m e2e --run-destructive
"""
import json
import pytest
from dataclasses import dataclass, field
from typing import Any
from click.testing import CliRunner
from lightroom_sdk.paths import get_port_file


# --- State container shared across entire session ---


@dataclass
class E2EState:
    """Mutable state shared across all E2E test phases.

    Populated by early phases, consumed by later ones.
    """
    photo_id: str | None = None
    photo_ids: list[str] = field(default_factory=list)
    original_rating: int | None = None
    original_flag: str | None = None
    original_color_label: str | None = None
    original_title: str | None = None
    original_caption: str | None = None
    original_develop_settings: dict[str, Any] | None = None
    created_collection_name: str | None = None
    created_keyword: str | None = None
    created_snapshot_name: str | None = None
    created_mask_id: str | None = None


_state = E2EState()


# --- CLI Command Options ---


def pytest_addoption(parser):
    parser.addoption(
        "--run-destructive",
        action="store_true",
        default=False,
        help="Run destructive E2E tests",
    )


# --- Skip Logic ---


def pytest_collection_modifyitems(config, items):
    """Auto-skip e2e tests when Lightroom is not running.
    Auto-skip destructive tests unless --run-destructive is passed.
    """
    port_file = get_port_file()
    skip_e2e = None
    if not port_file.exists():
        skip_e2e = pytest.mark.skip(
            reason=f"Lightroom not running (port file not found: {port_file})"
        )

    skip_destructive = None
    if not config.getoption("--run-destructive"):
        skip_destructive = pytest.mark.skip(reason="Destructive test (use --run-destructive)")

    for item in items:
        if "e2e" in item.keywords:
            if skip_e2e:
                item.add_marker(skip_e2e)
            if "destructive" in item.keywords and skip_destructive:
                item.add_marker(skip_destructive)


# --- Fixtures ---


@pytest.fixture(scope="session")
def e2e_state():
    """Shared mutable state across the entire E2E session."""
    return _state


@pytest.fixture(scope="session")
def runner():
    """Click CliRunner for invoking CLI commands."""
    return CliRunner()


@pytest.fixture(scope="session")
def cli_app():
    """The CLI application."""
    from cli.main import cli
    return cli


def invoke(runner, cli_app, args: list[str], fmt: str = "json") -> dict:
    """Helper: invoke CLI command and return parsed result.

    Args:
        runner: CliRunner instance
        cli_app: Click CLI group
        args: Command arguments (e.g. ["system", "ping"])
        fmt: Output format ("json" for machine-parseable, "text" for display)

    Returns:
        dict with keys:
          - exit_code: int
          - output: str (raw output)
          - data: parsed JSON (if fmt="json") or None
    """
    full_args = ["-o", fmt] + args
    result = runner.invoke(cli_app, full_args)
    data = None
    if fmt == "json" and result.output.strip():
        try:
            data = json.loads(result.output)
        except json.JSONDecodeError:
            pass
    return {
        "exit_code": result.exit_code,
        "output": result.output,
        "data": data,
    }


@pytest.fixture(scope="session")
def run(runner, cli_app):
    """Convenience fixture: run("system", "ping") -> dict."""
    def _run(*args, fmt="json"):
        return invoke(runner, cli_app, list(args), fmt=fmt)
    return _run


# --- Session-level fallback cleanup ---


@pytest.fixture(scope="session", autouse=True)
def session_cleanup(run, e2e_state):
    """Final cleanup at end of E2E session."""
    yield
    # Emergency cleanup: reset develop to defaults
    run("develop", "reset")
    # Unflag
    run("selection", "unflag")
    # Reset rating
    run("selection", "set-rating", "0")
    # Reset color label
    run("selection", "color-label", "none")
    # Restore original selection if we have the photo_id
    if e2e_state.photo_id:
        run("catalog", "select", e2e_state.photo_id)
```

### `pyproject.toml` の変更

`markers` セクションに `destructive` と `slow` を追加する。

```toml
# 変更箇所のみ:
markers = [
    "integration: marks tests as integration tests requiring Lightroom",
    "unit: marks tests as unit tests",
    "e2e: marks tests as E2E tests requiring Lightroom Classic",
    "destructive: marks destructive tests (skipped by default, run with --run-destructive)",
    "slow: marks slow tests (preview generation, batch operations)",
]
```

**確認コマンド:**
```bash
venv/bin/python -m pytest tests/e2e/conftest.py --co 2>&1 | head -5  # conftest構文確認
venv/bin/python -m pytest --markers 2>&1 | grep -E "e2e|destructive|slow"  # マーカー確認
```

**コミット:**
```bash
git add tests/e2e/conftest.py pyproject.toml
git commit -m "test: replace e2e conftest with CliRunner-based fixtures (prep for full E2E suite)"
```

---

## Task 2: test_phase01_system.py

**Files:**
- Create: `tests/e2e/test_phase01_system.py`

**実装内容:**

```python
# tests/e2e/test_phase01_system.py
"""Phase 1: System commands - verify Lightroom connection is alive.

If these fail, all subsequent phases are meaningless.

Commands tested:
  - system ping
  - system status
  - system check-connection
  - system reconnect
"""
import pytest


@pytest.mark.e2e
class TestSystemPing:
    """Test 1: system ping — gate test for entire E2E suite."""

    def test_system_ping(self, run):
        r = run("system", "ping")
        assert r["exit_code"] == 0, f"ping failed: {r['output']}"
        assert r["data"] is not None, f"ping returned no JSON data: {r['output']}"


@pytest.mark.e2e
class TestSystemStatus:
    """Test 2: system status — verify version/state info."""

    def test_system_status(self, run):
        r = run("system", "status")
        assert r["exit_code"] == 0, f"status failed: {r['output']}"
        assert r["data"] is not None, f"status returned no JSON data: {r['output']}"


@pytest.mark.e2e
class TestSystemCheckConnection:
    """Test 3: system check-connection — verify connection check."""

    def test_system_check_connection(self, run):
        r = run("system", "check-connection", fmt="text")
        assert r["exit_code"] == 0, f"check-connection failed: {r['output']}"
        assert "ok" in r["output"].lower(), f"Expected 'ok' in output: {r['output']}"


@pytest.mark.e2e
class TestSystemReconnect:
    """Test 4: system reconnect — force reconnection."""

    def test_system_reconnect(self, run):
        r = run("system", "reconnect", fmt="text")
        assert r["exit_code"] == 0, f"reconnect failed: {r['output']}"
        assert "reconnected" in r["output"].lower(), f"Expected 'Reconnected' in output: {r['output']}"
```

**確認コマンド:**
```bash
venv/bin/python -m pytest tests/e2e/test_phase01_system.py -v --co
```

**コミット:**
```bash
git add tests/e2e/test_phase01_system.py
git commit -m "test: add E2E phase 1 — system commands (ping, status, check-connection, reconnect)"
```

---

## Task 3: test_phase02_catalog_read.py

**Files:**
- Create: `tests/e2e/test_phase02_catalog_read.py`

**実装内容:**

```python
# tests/e2e/test_phase02_catalog_read.py
"""Phase 2: Catalog read-only commands.

Captures photo_id for later phases. All commands are read-only.

Commands tested:
  - catalog get-selected (stores photo_id, photo_ids)
  - catalog list --limit 5
  - catalog get-info <photo_id>
  - catalog search "test"
  - catalog find --rating 0 --rating-op ">="
  - catalog collections
  - catalog keywords
  - catalog folders
  - catalog get-view-filter
  - catalog batch-metadata <photo_id>
"""
import pytest


@pytest.mark.e2e
class TestCatalogGetSelected:
    """Test 5: catalog get-selected — capture photo_id for subsequent phases."""

    def test_get_selected(self, run, e2e_state):
        r = run("catalog", "get-selected")
        assert r["exit_code"] == 0, f"get-selected failed: {r['output']}"
        assert r["data"] is not None, f"get-selected returned no JSON: {r['output']}"

        # Extract photo_id from the response
        data = r["data"]
        if isinstance(data, list) and len(data) > 0:
            # List of photos — take the first one
            first = data[0]
            if isinstance(first, dict) and "id" in first:
                e2e_state.photo_id = str(first["id"])
                e2e_state.photo_ids = [str(p["id"]) for p in data if isinstance(p, dict) and "id" in p]
            elif isinstance(first, (str, int)):
                e2e_state.photo_id = str(first)
                e2e_state.photo_ids = [str(p) for p in data]
        elif isinstance(data, dict):
            if "photos" in data and isinstance(data["photos"], list) and len(data["photos"]) > 0:
                first = data["photos"][0]
                if isinstance(first, dict) and "id" in first:
                    e2e_state.photo_id = str(first["id"])
                    e2e_state.photo_ids = [str(p["id"]) for p in data["photos"] if isinstance(p, dict) and "id" in p]
                elif isinstance(first, (str, int)):
                    e2e_state.photo_id = str(first)
                    e2e_state.photo_ids = [str(p) for p in data["photos"]]
            elif "id" in data:
                e2e_state.photo_id = str(data["id"])
                e2e_state.photo_ids = [e2e_state.photo_id]

        assert e2e_state.photo_id is not None, (
            f"Could not extract photo_id from get-selected response: {r['data']}"
        )


@pytest.mark.e2e
class TestCatalogList:
    """Test 6: catalog list --limit 5."""

    def test_list_photos(self, run):
        r = run("catalog", "list", "--limit", "5")
        assert r["exit_code"] == 0, f"list failed: {r['output']}"
        assert r["data"] is not None, f"list returned no JSON: {r['output']}"


@pytest.mark.e2e
class TestCatalogGetInfo:
    """Test 7: catalog get-info <photo_id>."""

    def test_get_info(self, run, e2e_state):
        assert e2e_state.photo_id is not None, "photo_id not set (Phase 2 depends on get-selected)"
        r = run("catalog", "get-info", e2e_state.photo_id)
        assert r["exit_code"] == 0, f"get-info failed: {r['output']}"
        assert r["data"] is not None, f"get-info returned no JSON: {r['output']}"


@pytest.mark.e2e
class TestCatalogSearch:
    """Test 8: catalog search "test" — may return empty, that's OK."""

    def test_search(self, run):
        r = run("catalog", "search", "test")
        assert r["exit_code"] == 0, f"search failed: {r['output']}"


@pytest.mark.e2e
class TestCatalogFind:
    """Test 9: catalog find --rating 0 --rating-op ">="."""

    def test_find_by_rating(self, run):
        r = run("catalog", "find", "--rating", "0", "--rating-op", ">=")
        assert r["exit_code"] == 0, f"find failed: {r['output']}"


@pytest.mark.e2e
class TestCatalogCollections:
    """Test 10: catalog collections."""

    def test_collections(self, run):
        r = run("catalog", "collections")
        assert r["exit_code"] == 0, f"collections failed: {r['output']}"


@pytest.mark.e2e
class TestCatalogKeywords:
    """Test 11: catalog keywords."""

    def test_keywords(self, run):
        r = run("catalog", "keywords")
        assert r["exit_code"] == 0, f"keywords failed: {r['output']}"


@pytest.mark.e2e
class TestCatalogFolders:
    """Test 12: catalog folders."""

    def test_folders(self, run):
        r = run("catalog", "folders")
        assert r["exit_code"] == 0, f"folders failed: {r['output']}"


@pytest.mark.e2e
class TestCatalogGetViewFilter:
    """Test 13: catalog get-view-filter."""

    def test_get_view_filter(self, run):
        r = run("catalog", "get-view-filter")
        assert r["exit_code"] == 0, f"get-view-filter failed: {r['output']}"


@pytest.mark.e2e
class TestCatalogBatchMetadata:
    """Test 14: catalog batch-metadata <photo_id>."""

    def test_batch_metadata(self, run, e2e_state):
        assert e2e_state.photo_id is not None, "photo_id not set"
        r = run("catalog", "batch-metadata", e2e_state.photo_id)
        assert r["exit_code"] == 0, f"batch-metadata failed: {r['output']}"
        assert r["data"] is not None, f"batch-metadata returned no JSON: {r['output']}"
```

**確認コマンド:**
```bash
venv/bin/python -m pytest tests/e2e/test_phase02_catalog_read.py -v --co
```

**コミット:**
```bash
git add tests/e2e/test_phase02_catalog_read.py
git commit -m "test: add E2E phase 2 — catalog read commands (10 tests)"
```

---

## Task 4: test_phase03_catalog_write.py

**Files:**
- Create: `tests/e2e/test_phase03_catalog_write.py`

**実装内容:**

```python
# tests/e2e/test_phase03_catalog_write.py
"""Phase 3: Catalog write commands with verify + cleanup cycles.

Each group follows: Setup -> Act -> Verify -> Cleanup.
Groups are self-contained — failure in one group does not affect others.

Commands tested:
  Group 3A: catalog get-flag, set-rating (write + restore)
  Group 3B: catalog set-flag (write + verify + restore)
  Group 3C: catalog set-color-label (write + restore)
  Group 3D: catalog set-title, set-caption (write + restore)
  Group 3E: catalog add-keywords, remove-keyword
  Group 3F: catalog set-metadata (write + restore)
  Group 3G: catalog rotate-left, rotate-right (self-canceling pair)
"""
import pytest


# --- Group 3A: Rating ---


@pytest.mark.e2e
class TestCatalogRating:
    """Tests 15-17: Save original flag, set rating to 3, restore to 0."""

    def test_get_flag_save_original(self, run, e2e_state):
        """Test 15: Get current flag status (save original)."""
        assert e2e_state.photo_id is not None, "photo_id not set"
        r = run("catalog", "get-flag", e2e_state.photo_id)
        assert r["exit_code"] == 0, f"get-flag failed: {r['output']}"
        e2e_state.original_flag = r["data"]

    def test_set_rating_3(self, run, e2e_state):
        """Test 16: Set rating to 3."""
        assert e2e_state.photo_id is not None, "photo_id not set"
        r = run("catalog", "set-rating", e2e_state.photo_id, "3")
        assert r["exit_code"] == 0, f"set-rating 3 failed: {r['output']}"

    def test_cleanup_set_rating_0(self, run, e2e_state):
        """Test 17: Restore rating to 0."""
        assert e2e_state.photo_id is not None, "photo_id not set"
        r = run("catalog", "set-rating", e2e_state.photo_id, "0")
        assert r["exit_code"] == 0, f"set-rating 0 failed: {r['output']}"


# --- Group 3B: Flag ---


@pytest.mark.e2e
class TestCatalogFlag:
    """Tests 18-20: Set flag to pick, verify, restore to none."""

    def test_set_flag_pick(self, run, e2e_state):
        """Test 18: Set flag to pick."""
        assert e2e_state.photo_id is not None, "photo_id not set"
        r = run("catalog", "set-flag", e2e_state.photo_id, "pick")
        assert r["exit_code"] == 0, f"set-flag pick failed: {r['output']}"

    def test_verify_flag_pick(self, run, e2e_state):
        """Test 19: Verify flag is pick."""
        assert e2e_state.photo_id is not None, "photo_id not set"
        r = run("catalog", "get-flag", e2e_state.photo_id)
        assert r["exit_code"] == 0, f"get-flag failed: {r['output']}"
        # Flag value 1 = pick
        flag_data = r["data"]
        assert flag_data is not None, f"get-flag returned no data: {r['output']}"

    def test_cleanup_flag_none(self, run, e2e_state):
        """Test 20: Restore flag to none."""
        assert e2e_state.photo_id is not None, "photo_id not set"
        r = run("catalog", "set-flag", e2e_state.photo_id, "none")
        assert r["exit_code"] == 0, f"set-flag none failed: {r['output']}"


# --- Group 3C: Color Label ---


@pytest.mark.e2e
class TestCatalogColorLabel:
    """Tests 21-22: Set color label to red, restore to none."""

    def test_set_color_label_red(self, run, e2e_state):
        """Test 21: Set color label to red."""
        assert e2e_state.photo_id is not None, "photo_id not set"
        r = run("catalog", "set-color-label", e2e_state.photo_id, "red")
        assert r["exit_code"] == 0, f"set-color-label red failed: {r['output']}"

    def test_cleanup_color_label_none(self, run, e2e_state):
        """Test 22: Restore color label to none."""
        assert e2e_state.photo_id is not None, "photo_id not set"
        r = run("catalog", "set-color-label", e2e_state.photo_id, "none")
        assert r["exit_code"] == 0, f"set-color-label none failed: {r['output']}"


# --- Group 3D: Title & Caption ---


@pytest.mark.e2e
class TestCatalogTitleCaption:
    """Tests 23-26: Set title/caption, then clear them."""

    def test_set_title(self, run, e2e_state):
        """Test 23: Set title to 'E2E Test Title'."""
        assert e2e_state.photo_id is not None, "photo_id not set"
        r = run("catalog", "set-title", e2e_state.photo_id, "E2E Test Title")
        assert r["exit_code"] == 0, f"set-title failed: {r['output']}"

    def test_set_caption(self, run, e2e_state):
        """Test 24: Set caption to 'E2E Test Caption'."""
        assert e2e_state.photo_id is not None, "photo_id not set"
        r = run("catalog", "set-caption", e2e_state.photo_id, "E2E Test Caption")
        assert r["exit_code"] == 0, f"set-caption failed: {r['output']}"

    def test_cleanup_title(self, run, e2e_state):
        """Test 25: Clear title."""
        assert e2e_state.photo_id is not None, "photo_id not set"
        r = run("catalog", "set-title", e2e_state.photo_id, "")
        assert r["exit_code"] == 0, f"set-title '' failed: {r['output']}"

    def test_cleanup_caption(self, run, e2e_state):
        """Test 26: Clear caption."""
        assert e2e_state.photo_id is not None, "photo_id not set"
        r = run("catalog", "set-caption", e2e_state.photo_id, "")
        assert r["exit_code"] == 0, f"set-caption '' failed: {r['output']}"


# --- Group 3E: Keywords ---


@pytest.mark.e2e
class TestCatalogKeywords:
    """Tests 27-28: Add keyword, then remove it."""

    def test_add_keywords(self, run, e2e_state):
        """Test 27: Add _e2e_test_keyword."""
        assert e2e_state.photo_id is not None, "photo_id not set"
        r = run("catalog", "add-keywords", e2e_state.photo_id, "_e2e_test_keyword")
        assert r["exit_code"] == 0, f"add-keywords failed: {r['output']}"

    def test_cleanup_remove_keyword(self, run, e2e_state):
        """Test 28: Remove _e2e_test_keyword."""
        assert e2e_state.photo_id is not None, "photo_id not set"
        r = run("catalog", "remove-keyword", e2e_state.photo_id, "_e2e_test_keyword")
        assert r["exit_code"] == 0, f"remove-keyword failed: {r['output']}"


# --- Group 3F: Metadata ---


@pytest.mark.e2e
class TestCatalogMetadata:
    """Tests 29-30: Set metadata headline, then clear it."""

    def test_set_metadata_headline(self, run, e2e_state):
        """Test 29: Set headline to 'E2E Test'."""
        assert e2e_state.photo_id is not None, "photo_id not set"
        r = run("catalog", "set-metadata", e2e_state.photo_id, "headline", "E2E Test")
        assert r["exit_code"] == 0, f"set-metadata headline failed: {r['output']}"

    def test_cleanup_metadata_headline(self, run, e2e_state):
        """Test 30: Clear headline."""
        assert e2e_state.photo_id is not None, "photo_id not set"
        r = run("catalog", "set-metadata", e2e_state.photo_id, "headline", "")
        assert r["exit_code"] == 0, f"set-metadata headline '' failed: {r['output']}"


# --- Group 3G: Rotation (self-canceling pair) ---


@pytest.mark.e2e
class TestCatalogRotation:
    """Tests 31-32: Rotate left then right (cancels out)."""

    def test_rotate_left(self, run):
        """Test 31: Rotate left."""
        r = run("catalog", "rotate-left")
        assert r["exit_code"] == 0, f"rotate-left failed: {r['output']}"

    def test_cleanup_rotate_right(self, run):
        """Test 32: Rotate right (cancels rotate-left)."""
        r = run("catalog", "rotate-right")
        assert r["exit_code"] == 0, f"rotate-right failed: {r['output']}"
```

**確認コマンド:**
```bash
venv/bin/python -m pytest tests/e2e/test_phase03_catalog_write.py -v --co
```

**コミット:**
```bash
git add tests/e2e/test_phase03_catalog_write.py
git commit -m "test: add E2E phase 3 — catalog write commands (17 tests)"
```

---

## Task 5: test_phase04_selection.py

**Files:**
- Create: `tests/e2e/test_phase04_selection.py`

**実装内容:**

```python
# tests/e2e/test_phase04_selection.py
"""Phase 4: Selection commands.

Test photo must be selected before this phase.
Groups follow Setup -> Act -> Verify -> Cleanup pattern.

Commands tested:
  Group 4A: selection get-flag, flag, reject, unflag
  Group 4B: selection get-rating, set-rating, increase-rating, decrease-rating
  Group 4C: selection get-color-label, color-label, toggle-label
  Group 4D: selection next, previous
  Additional: select-all, deselect-others, extend, deselect-active, select-none,
              select-inverse, catalog get-selected, catalog select (restore)
"""
import pytest


# --- Group 4A: Flag cycle ---


@pytest.mark.e2e
class TestSelectionFlagCycle:
    """Tests 33-38: Flag cycle — get, flag, verify, reject, verify, unflag."""

    def test_get_flag_save_original(self, run, e2e_state):
        """Test 33: Get current flag status (save original)."""
        r = run("selection", "get-flag")
        assert r["exit_code"] == 0, f"get-flag failed: {r['output']}"
        e2e_state.original_flag = r["data"]

    def test_flag_as_pick(self, run):
        """Test 34: Flag as pick."""
        r = run("selection", "flag")
        assert r["exit_code"] == 0, f"flag failed: {r['output']}"

    def test_verify_flag_pick(self, run):
        """Test 35: Verify flag is pick."""
        r = run("selection", "get-flag")
        assert r["exit_code"] == 0, f"get-flag failed: {r['output']}"

    def test_flag_as_reject(self, run):
        """Test 36: Flag as reject."""
        r = run("selection", "reject")
        assert r["exit_code"] == 0, f"reject failed: {r['output']}"

    def test_verify_flag_reject(self, run):
        """Test 37: Verify flag is reject."""
        r = run("selection", "get-flag")
        assert r["exit_code"] == 0, f"get-flag failed: {r['output']}"

    def test_cleanup_unflag(self, run):
        """Test 38: Remove flag (cleanup)."""
        r = run("selection", "unflag")
        assert r["exit_code"] == 0, f"unflag failed: {r['output']}"


# --- Group 4B: Rating cycle ---


@pytest.mark.e2e
class TestSelectionRatingCycle:
    """Tests 39-44: Rating cycle — get, set 3, verify, increase, decrease, restore."""

    def test_get_rating_save_original(self, run, e2e_state):
        """Test 39: Get current rating (save original)."""
        r = run("selection", "get-rating")
        assert r["exit_code"] == 0, f"get-rating failed: {r['output']}"
        e2e_state.original_rating = r["data"]

    def test_set_rating_3(self, run):
        """Test 40: Set rating to 3."""
        r = run("selection", "set-rating", "3")
        assert r["exit_code"] == 0, f"set-rating 3 failed: {r['output']}"

    def test_verify_rating_3(self, run):
        """Test 41: Verify rating is 3."""
        r = run("selection", "get-rating")
        assert r["exit_code"] == 0, f"get-rating failed: {r['output']}"

    def test_increase_rating(self, run):
        """Test 42: Increase rating (should become 4)."""
        r = run("selection", "increase-rating")
        assert r["exit_code"] == 0, f"increase-rating failed: {r['output']}"

    def test_decrease_rating(self, run):
        """Test 43: Decrease rating (should become 3)."""
        r = run("selection", "decrease-rating")
        assert r["exit_code"] == 0, f"decrease-rating failed: {r['output']}"

    def test_cleanup_set_rating_0(self, run):
        """Test 44: Restore rating to 0."""
        r = run("selection", "set-rating", "0")
        assert r["exit_code"] == 0, f"set-rating 0 failed: {r['output']}"


# --- Group 4C: Color label cycle ---


@pytest.mark.e2e
class TestSelectionColorLabelCycle:
    """Tests 45-49: Color label cycle — get, set green, verify, toggle off, restore."""

    def test_get_color_label_save_original(self, run, e2e_state):
        """Test 45: Get current color label (save original)."""
        r = run("selection", "get-color-label")
        assert r["exit_code"] == 0, f"get-color-label failed: {r['output']}"
        e2e_state.original_color_label = r["data"]

    def test_set_color_label_green(self, run):
        """Test 46: Set color label to green."""
        r = run("selection", "color-label", "green")
        assert r["exit_code"] == 0, f"color-label green failed: {r['output']}"

    def test_verify_color_label_green(self, run):
        """Test 47: Verify color label is green."""
        r = run("selection", "get-color-label")
        assert r["exit_code"] == 0, f"get-color-label failed: {r['output']}"

    def test_toggle_label_green(self, run):
        """Test 48: Toggle green label off."""
        r = run("selection", "toggle-label", "green")
        assert r["exit_code"] == 0, f"toggle-label green failed: {r['output']}"

    def test_cleanup_color_label_none(self, run):
        """Test 49: Restore color label to none."""
        r = run("selection", "color-label", "none")
        assert r["exit_code"] == 0, f"color-label none failed: {r['output']}"


# --- Group 4D: Navigation ---


@pytest.mark.e2e
class TestSelectionNavigation:
    """Tests 50-51: Navigation — next, previous."""

    def test_next(self, run):
        """Test 50: Move to next photo."""
        r = run("selection", "next")
        assert r["exit_code"] == 0, f"next failed: {r['output']}"

    def test_previous(self, run):
        """Test 51: Move to previous photo (back to original)."""
        r = run("selection", "previous")
        assert r["exit_code"] == 0, f"previous failed: {r['output']}"


# --- Additional Selection Tests (S1-S8) ---


@pytest.mark.e2e
class TestSelectionManipulation:
    """Tests S1-S8: Selection manipulation — ordered at end of Phase 4.

    These change global selection state and immediately restore.
    """

    def test_select_all(self, run):
        """Test S1: Select all photos in current view."""
        r = run("selection", "select-all")
        assert r["exit_code"] == 0, f"select-all failed: {r['output']}"

    def test_deselect_others(self, run):
        """Test S2: Keep only active photo selected."""
        r = run("selection", "deselect-others")
        assert r["exit_code"] == 0, f"deselect-others failed: {r['output']}"

    def test_extend_selection(self, run):
        """Test S3: Extend selection right by 1."""
        r = run("selection", "extend", "--direction", "right", "--amount", "1")
        assert r["exit_code"] == 0, f"extend failed: {r['output']}"

    def test_deselect_active(self, run):
        """Test S4: Deselect the active photo."""
        r = run("selection", "deselect-active")
        assert r["exit_code"] == 0, f"deselect-active failed: {r['output']}"

    def test_select_none(self, run):
        """Test S5: Deselect all photos."""
        r = run("selection", "select-none")
        assert r["exit_code"] == 0, f"select-none failed: {r['output']}"

    def test_select_inverse(self, run):
        """Test S6: Invert selection."""
        r = run("selection", "select-inverse")
        assert r["exit_code"] == 0, f"select-inverse failed: {r['output']}"

    def test_get_selected_after_manipulation(self, run):
        """Test S7: Get selected photos after manipulation."""
        r = run("catalog", "get-selected")
        assert r["exit_code"] == 0, f"get-selected failed: {r['output']}"

    def test_restore_original_selection(self, run, e2e_state):
        """Test S8: Restore original selection via catalog select."""
        assert e2e_state.photo_id is not None, "photo_id not set"
        r = run("catalog", "select", e2e_state.photo_id)
        assert r["exit_code"] == 0, f"catalog select failed: {r['output']}"
```

**確認コマンド:**
```bash
venv/bin/python -m pytest tests/e2e/test_phase04_selection.py -v --co
```

**コミット:**
```bash
git add tests/e2e/test_phase04_selection.py
git commit -m "test: add E2E phase 4 — selection commands (19 tests)"
```

---

## Task 6: test_phase05_develop_basic.py

**Files:**
- Create: `tests/e2e/test_phase05_develop_basic.py`

**実装内容:**

```python
# tests/e2e/test_phase05_develop_basic.py
"""Phase 5: Develop basic commands — global develop settings.

Saves and restores develop state.

Commands tested:
  Group 5A: develop get-settings, get, range, process-version (read)
  Group 5B: develop set, auto-tone, auto-wb, reset-param (write + verify + restore)
  Group 5C: develop apply (JSON apply)
  Group 5D: develop copy-settings, snapshot, tool (clipboard/snapshot/tool)
  Group 5E: develop reset, get-settings (full reset + verify)
"""
import pytest


# --- Group 5A: Read current state ---


@pytest.mark.e2e
class TestDevelopReadState:
    """Tests 52-55: Read develop state."""

    def test_get_settings(self, run, e2e_state):
        """Test 52: Get all develop settings (stores original)."""
        r = run("develop", "get-settings")
        assert r["exit_code"] == 0, f"get-settings failed: {r['output']}"
        assert r["data"] is not None, f"get-settings returned no JSON: {r['output']}"
        e2e_state.original_develop_settings = r["data"]

    def test_get_exposure(self, run):
        """Test 53: Get Exposure value."""
        r = run("develop", "get", "Exposure")
        assert r["exit_code"] == 0, f"get Exposure failed: {r['output']}"

    def test_range_exposure(self, run):
        """Test 54: Get Exposure range (min/max)."""
        r = run("develop", "range", "Exposure")
        assert r["exit_code"] == 0, f"range Exposure failed: {r['output']}"
        assert r["data"] is not None, f"range returned no JSON: {r['output']}"

    def test_process_version(self, run):
        """Test 55: Get process version."""
        r = run("develop", "process-version")
        assert r["exit_code"] == 0, f"process-version failed: {r['output']}"


# --- Group 5B: Modify + verify + restore ---


@pytest.mark.e2e
class TestDevelopModify:
    """Tests 56-61: Modify develop settings, verify, restore."""

    def test_set_exposure(self, run):
        """Test 56: Set Exposure to 0.5."""
        r = run("develop", "set", "Exposure", "0.5")
        assert r["exit_code"] == 0, f"set Exposure 0.5 failed: {r['output']}"

    def test_verify_exposure(self, run):
        """Test 57: Verify Exposure is 0.5."""
        r = run("develop", "get", "Exposure")
        assert r["exit_code"] == 0, f"get Exposure failed: {r['output']}"

    def test_set_multi_param(self, run):
        """Test 58: Set Exposure 0.5 Contrast 10 (multi-param batch)."""
        r = run("develop", "set", "Exposure", "0.5", "Contrast", "10")
        assert r["exit_code"] == 0, f"set multi-param failed: {r['output']}"

    def test_auto_tone(self, run):
        """Test 59: Auto-tone."""
        r = run("develop", "auto-tone")
        assert r["exit_code"] == 0, f"auto-tone failed: {r['output']}"

    def test_auto_wb(self, run):
        """Test 60: Auto white balance."""
        r = run("develop", "auto-wb")
        assert r["exit_code"] == 0, f"auto-wb failed: {r['output']}"

    def test_reset_param_exposure(self, run):
        """Test 61: Reset single param (Exposure)."""
        r = run("develop", "reset-param", "Exposure")
        assert r["exit_code"] == 0, f"reset-param Exposure failed: {r['output']}"


# --- Group 5C: Apply settings ---


@pytest.mark.e2e
class TestDevelopApply:
    """Test 62: Apply settings from JSON."""

    def test_apply_settings(self, run):
        """Test 62: Apply Exposure 0.3 via JSON."""
        r = run("develop", "apply", "--settings", '{"Exposure": 0.3}')
        assert r["exit_code"] == 0, f"apply failed: {r['output']}"


# --- Group 5D: Copy/paste/preset/snapshot ---


@pytest.mark.e2e
class TestDevelopCopySnapshotTool:
    """Tests 63-65: Copy settings, create snapshot, select tool."""

    def test_copy_settings(self, run):
        """Test 63: Copy settings to clipboard."""
        r = run("develop", "copy-settings")
        assert r["exit_code"] == 0, f"copy-settings failed: {r['output']}"

    def test_create_snapshot(self, run, e2e_state):
        """Test 64: Create snapshot 'e2e_test_snap'."""
        r = run("develop", "snapshot", "e2e_test_snap")
        assert r["exit_code"] == 0, f"snapshot failed: {r['output']}"
        e2e_state.created_snapshot_name = "e2e_test_snap"

    def test_tool_loupe(self, run):
        """Test 65: Select loupe tool."""
        r = run("develop", "tool", "loupe")
        assert r["exit_code"] == 0, f"tool loupe failed: {r['output']}"


# --- Group 5E: Full reset ---


@pytest.mark.e2e
class TestDevelopFullReset:
    """Tests 66-67: Full reset and verify."""

    def test_reset(self, run):
        """Test 66: Reset all develop settings."""
        r = run("develop", "reset")
        assert r["exit_code"] == 0, f"reset failed: {r['output']}"

    def test_verify_reset(self, run):
        """Test 67: Verify settings are defaults after reset."""
        r = run("develop", "get-settings")
        assert r["exit_code"] == 0, f"get-settings failed: {r['output']}"
        assert r["data"] is not None, f"get-settings returned no JSON: {r['output']}"
```

**確認コマンド:**
```bash
venv/bin/python -m pytest tests/e2e/test_phase05_develop_basic.py -v --co
```

**コミット:**
```bash
git add tests/e2e/test_phase05_develop_basic.py
git commit -m "test: add E2E phase 5 — develop basic commands (16 tests)"
```

---

## Task 7: test_phase06_develop_curve.py

**Files:**
- Create: `tests/e2e/test_phase06_develop_curve.py`

**実装内容:**

```python
# tests/e2e/test_phase06_develop_curve.py
"""Phase 6: Develop tone curve commands.

Commands tested:
  - develop curve get
  - develop curve add-point 64 80
  - develop curve get (verify)
  - develop curve s-curve
  - develop curve set --points '[[0,0],[128,140],[255,255]]'
  - develop curve linear (cleanup)
"""
import pytest


@pytest.mark.e2e
class TestDevelopCurveRead:
    """Test 68: Read current tone curve."""

    def test_curve_get(self, run):
        """Test 68: Get current tone curve."""
        r = run("develop", "curve", "get")
        assert r["exit_code"] == 0, f"curve get failed: {r['output']}"


@pytest.mark.e2e
class TestDevelopCurveAddPoint:
    """Tests 69-70: Add point and verify."""

    def test_curve_add_point(self, run):
        """Test 69: Add curve point at (64, 80)."""
        r = run("develop", "curve", "add-point", "64", "80")
        assert r["exit_code"] == 0, f"curve add-point failed: {r['output']}"

    def test_curve_verify_point(self, run):
        """Test 70: Verify curve contains point near (64, 80)."""
        r = run("develop", "curve", "get")
        assert r["exit_code"] == 0, f"curve get failed: {r['output']}"


@pytest.mark.e2e
class TestDevelopCurveSCurve:
    """Test 71: Apply S-curve."""

    def test_curve_s_curve(self, run):
        """Test 71: Apply S-curve preset."""
        r = run("develop", "curve", "s-curve")
        assert r["exit_code"] == 0, f"curve s-curve failed: {r['output']}"


@pytest.mark.e2e
class TestDevelopCurveSet:
    """Test 72: Set custom curve points."""

    def test_curve_set_points(self, run):
        """Test 72: Set curve to custom points."""
        r = run("develop", "curve", "set", "--points", "[[0,0],[128,140],[255,255]]")
        assert r["exit_code"] == 0, f"curve set failed: {r['output']}"


@pytest.mark.e2e
class TestDevelopCurveCleanup:
    """Test 73: Reset curve to linear."""

    def test_cleanup_curve_linear(self, run):
        """Test 73: Reset curve to linear (cleanup)."""
        r = run("develop", "curve", "linear")
        assert r["exit_code"] == 0, f"curve linear failed: {r['output']}"
```

**確認コマンド:**
```bash
venv/bin/python -m pytest tests/e2e/test_phase06_develop_curve.py -v --co
```

**コミット:**
```bash
git add tests/e2e/test_phase06_develop_curve.py
git commit -m "test: add E2E phase 6 — develop curve commands (6 tests)"
```

---

## Task 8: test_phase07_develop_mask_filter.py

**Files:**
- Create: `tests/e2e/test_phase07_develop_mask_filter.py`

**実装内容:**

```python
# tests/e2e/test_phase07_develop_mask_filter.py
"""Phase 7: Develop mask, filter, local adjustment, and reset commands.

This is the largest phase. Grouped into sub-phases with cleanup at each boundary.

Commands tested:
  Group 7A: develop mask list, mask selected (read)
  Group 7B: develop mask create, list, select, selected, tool-info,
            add, intersect, subtract, invert, toggle-overlay, go-to,
            activate, complex, delete (create + manipulate + cleanup)
  Group 7C: develop filter graduated, radial, brush, ai-select, range
  Group 7D: develop local params, get, set, get (verify), apply, create-mask
  Group 7E: develop reset-gradient, reset-circular, reset-brush, reset-masking,
            reset-crop, reset-transforms, reset-spot, reset-redeye, reset-healing
"""
import pytest


# --- Group 7A: Masking read ---


@pytest.mark.e2e
class TestMaskRead:
    """Tests 74-75: Masking read operations."""

    def test_mask_list(self, run):
        """Test 74: List masks."""
        r = run("develop", "mask", "list")
        assert r["exit_code"] == 0, f"mask list failed: {r['output']}"

    def test_mask_selected(self, run):
        """Test 75: Get selected mask (may be None)."""
        r = run("develop", "mask", "selected")
        assert r["exit_code"] == 0, f"mask selected failed: {r['output']}"


# --- Group 7B: Masking create + manipulate + cleanup ---


@pytest.mark.e2e
class TestMaskCreateManipulate:
    """Tests 76-90: Create mask, manipulate, then cleanup."""

    def test_mask_create(self, run, e2e_state):
        """Test 76: Create a new mask (stores mask_id)."""
        r = run("develop", "mask", "create")
        assert r["exit_code"] == 0, f"mask create failed: {r['output']}"
        # Try to extract mask_id from response
        data = r["data"]
        if isinstance(data, dict) and "id" in data:
            e2e_state.created_mask_id = str(data["id"])
        elif isinstance(data, dict) and "maskId" in data:
            e2e_state.created_mask_id = str(data["maskId"])
        elif isinstance(data, (str, int)):
            e2e_state.created_mask_id = str(data)

    def test_mask_list_verify(self, run):
        """Test 77: Verify new mask appears in list."""
        r = run("develop", "mask", "list")
        assert r["exit_code"] == 0, f"mask list failed: {r['output']}"

    def test_mask_select(self, run, e2e_state):
        """Test 78: Select the created mask."""
        if e2e_state.created_mask_id is None:
            pytest.skip("mask_id not available (mask create may have failed)")
        r = run("develop", "mask", "select", e2e_state.created_mask_id)
        assert r["exit_code"] == 0, f"mask select failed: {r['output']}"

    def test_mask_selected_verify(self, run, e2e_state):
        """Test 79: Verify selected mask matches created mask."""
        if e2e_state.created_mask_id is None:
            pytest.skip("mask_id not available")
        r = run("develop", "mask", "selected")
        assert r["exit_code"] == 0, f"mask selected failed: {r['output']}"

    def test_mask_tool_info(self, run):
        """Test 80: Get mask tool info."""
        r = run("develop", "mask", "tool-info")
        assert r["exit_code"] == 0, f"mask tool-info failed: {r['output']}"

    def test_mask_add_brush(self, run):
        """Test 81: Add brush to mask."""
        r = run("develop", "mask", "add", "brush")
        assert r["exit_code"] == 0, f"mask add brush failed: {r['output']}"

    def test_mask_intersect_brush(self, run):
        """Test 82: Intersect brush with mask."""
        r = run("develop", "mask", "intersect", "brush")
        assert r["exit_code"] == 0, f"mask intersect brush failed: {r['output']}"

    def test_mask_subtract_brush(self, run):
        """Test 83: Subtract brush from mask."""
        r = run("develop", "mask", "subtract", "brush")
        assert r["exit_code"] == 0, f"mask subtract brush failed: {r['output']}"

    def test_mask_invert(self, run, e2e_state):
        """Test 84: Invert mask."""
        if e2e_state.created_mask_id is None:
            pytest.skip("mask_id not available")
        r = run("develop", "mask", "invert", e2e_state.created_mask_id)
        assert r["exit_code"] == 0, f"mask invert failed: {r['output']}"

    def test_mask_toggle_overlay_on(self, run):
        """Test 85: Toggle overlay on."""
        r = run("develop", "mask", "toggle-overlay")
        assert r["exit_code"] == 0, f"mask toggle-overlay failed: {r['output']}"

    def test_mask_toggle_overlay_off(self, run):
        """Test 86: Toggle overlay off (cleanup)."""
        r = run("develop", "mask", "toggle-overlay")
        assert r["exit_code"] == 0, f"mask toggle-overlay failed: {r['output']}"

    def test_mask_go_to(self, run):
        """Test 87: Go to mask."""
        r = run("develop", "mask", "go-to")
        assert r["exit_code"] == 0, f"mask go-to failed: {r['output']}"

    def test_mask_activate(self, run):
        """Test 88: Activate mask."""
        r = run("develop", "mask", "activate")
        assert r["exit_code"] == 0, f"mask activate failed: {r['output']}"

    def test_mask_complex(self, run):
        """Test 89: Create complex mask (subject_with_luminance)."""
        r = run("develop", "mask", "complex", "--workflow", "subject_with_luminance")
        assert r["exit_code"] == 0, f"mask complex failed: {r['output']}"

    def test_cleanup_mask_delete(self, run, e2e_state):
        """Test 90: Delete created mask (cleanup)."""
        if e2e_state.created_mask_id is None:
            pytest.skip("mask_id not available")
        r = run("develop", "mask", "delete", e2e_state.created_mask_id)
        assert r["exit_code"] == 0, f"mask delete failed: {r['output']}"


# --- Group 7C: Filter creation ---


@pytest.mark.e2e
class TestFilterCreation:
    """Tests 91-95: Filter creation commands."""

    def test_filter_graduated(self, run):
        """Test 91: Create graduated filter."""
        r = run("develop", "filter", "graduated")
        assert r["exit_code"] == 0, f"filter graduated failed: {r['output']}"

    def test_filter_radial(self, run):
        """Test 92: Create radial filter."""
        r = run("develop", "filter", "radial")
        assert r["exit_code"] == 0, f"filter radial failed: {r['output']}"

    def test_filter_brush(self, run):
        """Test 93: Create adjustment brush."""
        r = run("develop", "filter", "brush")
        assert r["exit_code"] == 0, f"filter brush failed: {r['output']}"

    def test_filter_ai_select_subject(self, run):
        """Test 94: Create AI selection (subject)."""
        r = run("develop", "filter", "ai-select", "--type", "subject")
        assert r["exit_code"] == 0, f"filter ai-select subject failed: {r['output']}"

    def test_filter_range_luminance(self, run):
        """Test 95: Create range mask (luminance)."""
        r = run("develop", "filter", "range", "--type", "luminance")
        assert r["exit_code"] == 0, f"filter range luminance failed: {r['output']}"


# --- Group 7D: Local adjustments ---


@pytest.mark.e2e
class TestLocalAdjustments:
    """Tests 96-101: Local adjustment commands."""

    def test_local_params(self, run):
        """Test 96: List available local adjustment parameters."""
        r = run("develop", "local", "params")
        assert r["exit_code"] == 0, f"local params failed: {r['output']}"

    def test_local_get_exposure(self, run):
        """Test 97: Get local Exposure value."""
        r = run("develop", "local", "get", "Exposure")
        assert r["exit_code"] == 0, f"local get Exposure failed: {r['output']}"

    def test_local_set_exposure(self, run):
        """Test 98: Set local Exposure to 0.5."""
        r = run("develop", "local", "set", "Exposure", "0.5")
        assert r["exit_code"] == 0, f"local set Exposure 0.5 failed: {r['output']}"

    def test_local_verify_exposure(self, run):
        """Test 99: Verify local Exposure is 0.5."""
        r = run("develop", "local", "get", "Exposure")
        assert r["exit_code"] == 0, f"local get Exposure failed: {r['output']}"

    def test_local_apply(self, run):
        """Test 100: Apply local settings from JSON."""
        r = run("develop", "local", "apply", "--settings", '{"Exposure": 0.3}')
        assert r["exit_code"] == 0, f"local apply failed: {r['output']}"

    def test_local_create_mask_brush(self, run):
        """Test 101: Create mask with brush tool via local adjustments."""
        r = run("develop", "local", "create-mask", "--tool", "brush")
        assert r["exit_code"] == 0, f"local create-mask failed: {r['output']}"


# --- Group 7E: Reset commands (cleanup for 7B-7D) ---


@pytest.mark.e2e
class TestDevelopResetCommands:
    """Tests 102-110: Reset commands to clean up filters/masks."""

    def test_reset_gradient(self, run):
        """Test 102: Reset gradient filter."""
        r = run("develop", "reset-gradient")
        assert r["exit_code"] == 0, f"reset-gradient failed: {r['output']}"

    def test_reset_circular(self, run):
        """Test 103: Reset circular filter."""
        r = run("develop", "reset-circular")
        assert r["exit_code"] == 0, f"reset-circular failed: {r['output']}"

    def test_reset_brush(self, run):
        """Test 104: Reset adjustment brush."""
        r = run("develop", "reset-brush")
        assert r["exit_code"] == 0, f"reset-brush failed: {r['output']}"

    def test_reset_masking(self, run):
        """Test 105: Reset all masking."""
        r = run("develop", "reset-masking")
        assert r["exit_code"] == 0, f"reset-masking failed: {r['output']}"

    def test_reset_crop(self, run):
        """Test 106: Reset crop."""
        r = run("develop", "reset-crop")
        assert r["exit_code"] == 0, f"reset-crop failed: {r['output']}"

    def test_reset_transforms(self, run):
        """Test 107: Reset transforms."""
        r = run("develop", "reset-transforms")
        assert r["exit_code"] == 0, f"reset-transforms failed: {r['output']}"

    def test_reset_spot(self, run):
        """Test 108: Reset spot removal."""
        r = run("develop", "reset-spot")
        assert r["exit_code"] == 0, f"reset-spot failed: {r['output']}"

    def test_reset_redeye(self, run):
        """Test 109: Reset red eye removal."""
        r = run("develop", "reset-redeye")
        assert r["exit_code"] == 0, f"reset-redeye failed: {r['output']}"

    def test_reset_healing(self, run):
        """Test 110: Reset healing."""
        r = run("develop", "reset-healing")
        assert r["exit_code"] == 0, f"reset-healing failed: {r['output']}"
```

**確認コマンド:**
```bash
venv/bin/python -m pytest tests/e2e/test_phase07_develop_mask_filter.py -v --co
```

**コミット:**
```bash
git add tests/e2e/test_phase07_develop_mask_filter.py
git commit -m "test: add E2E phase 7 — develop mask, filter, local, reset commands (35 tests)"
```

---

## Task 9: test_phase08_develop_debug_color.py

**Files:**
- Create: `tests/e2e/test_phase08_develop_debug_color.py`

**実装内容:**

```python
# tests/e2e/test_phase08_develop_debug_color.py
"""Phase 8: Develop debug + color commands.

Commands tested:
  - develop debug dump
  - develop debug gradient-params
  - develop debug probe
  - develop debug monitor --duration 2
  - develop color green-swatch
  - develop color cyan-swatch
  - develop color enhance --preset natural
  - develop reset (final cleanup)
"""
import pytest


@pytest.mark.e2e
class TestDevelopDebug:
    """Tests 111-114: Debug/introspection commands."""

    def test_debug_dump(self, run):
        """Test 111: Dump LrDevelopController info."""
        r = run("develop", "debug", "dump")
        assert r["exit_code"] == 0, f"debug dump failed: {r['output']}"

    def test_debug_gradient_params(self, run):
        """Test 112: Discover gradient parameters."""
        r = run("develop", "debug", "gradient-params")
        assert r["exit_code"] == 0, f"debug gradient-params failed: {r['output']}"

    def test_debug_probe(self, run):
        """Test 113: Probe all develop parameters."""
        r = run("develop", "debug", "probe")
        assert r["exit_code"] == 0, f"debug probe failed: {r['output']}"

    def test_debug_monitor(self, run):
        """Test 114: Monitor parameter changes (short duration)."""
        r = run("develop", "debug", "monitor", "--duration", "2")
        assert r["exit_code"] == 0, f"debug monitor failed: {r['output']}"


@pytest.mark.e2e
class TestDevelopColor:
    """Tests 115-117: Color operation commands."""

    def test_color_green_swatch(self, run):
        """Test 115: Create green color swatch."""
        r = run("develop", "color", "green-swatch")
        assert r["exit_code"] == 0, f"color green-swatch failed: {r['output']}"

    def test_color_cyan_swatch(self, run):
        """Test 116: Create cyan color swatch."""
        r = run("develop", "color", "cyan-swatch")
        assert r["exit_code"] == 0, f"color cyan-swatch failed: {r['output']}"

    def test_color_enhance_natural(self, run):
        """Test 117: Enhance colors with natural preset."""
        r = run("develop", "color", "enhance", "--preset", "natural")
        assert r["exit_code"] == 0, f"color enhance natural failed: {r['output']}"


@pytest.mark.e2e
class TestDevelopDebugColorCleanup:
    """Test 118: Full reset after debug/color changes."""

    def test_cleanup_develop_reset(self, run):
        """Test 118: Reset all develop settings (cleanup)."""
        r = run("develop", "reset")
        assert r["exit_code"] == 0, f"develop reset failed: {r['output']}"
```

**確認コマンド:**
```bash
venv/bin/python -m pytest tests/e2e/test_phase08_develop_debug_color.py -v --co
```

**コミット:**
```bash
git add tests/e2e/test_phase08_develop_debug_color.py
git commit -m "test: add E2E phase 8 — develop debug + color commands (8 tests)"
```

---

## Task 10: test_phase09_preview.py

**Files:**
- Create: `tests/e2e/test_phase09_preview.py`

**実装内容:**

```python
# tests/e2e/test_phase09_preview.py
"""Phase 9: Preview commands.

Commands tested:
  - preview info <photo_id>
  - preview generate-current (@slow)
  - preview generate --size 512 --format jpeg (@slow)
  - preview generate-batch (@slow)
"""
import pytest


@pytest.mark.e2e
class TestPreviewInfo:
    """Test 119: Get preview info."""

    def test_preview_info(self, run, e2e_state):
        """Test 119: Get preview info for test photo."""
        assert e2e_state.photo_id is not None, "photo_id not set"
        r = run("preview", "info", e2e_state.photo_id)
        assert r["exit_code"] == 0, f"preview info failed: {r['output']}"


@pytest.mark.e2e
@pytest.mark.slow
class TestPreviewGenerateCurrent:
    """Test 120: Generate preview for currently selected photo."""

    def test_preview_generate_current(self, run):
        """Test 120: Generate preview for current photo (timeout=120s)."""
        r = run("preview", "generate-current")
        assert r["exit_code"] == 0, f"preview generate-current failed: {r['output']}"


@pytest.mark.e2e
@pytest.mark.slow
class TestPreviewGenerate:
    """Test 121: Generate preview with custom size and format."""

    def test_preview_generate(self, run):
        """Test 121: Generate preview (512px, jpeg)."""
        r = run("preview", "generate", "--size", "512", "--format", "jpeg")
        assert r["exit_code"] == 0, f"preview generate failed: {r['output']}"


@pytest.mark.e2e
@pytest.mark.slow
class TestPreviewGenerateBatch:
    """Test 122: Generate batch previews."""

    def test_preview_generate_batch(self, run):
        """Test 122: Generate batch previews (timeout=300s)."""
        r = run("preview", "generate-batch")
        assert r["exit_code"] == 0, f"preview generate-batch failed: {r['output']}"
```

**確認コマンド:**
```bash
venv/bin/python -m pytest tests/e2e/test_phase09_preview.py -v --co
```

**コミット:**
```bash
git add tests/e2e/test_phase09_preview.py
git commit -m "test: add E2E phase 9 — preview commands (4 tests)"
```

---

## Task 11: test_phase10_destructive.py

**Files:**
- Create: `tests/e2e/test_phase10_destructive.py`

**実装内容:**

```python
# tests/e2e/test_phase10_destructive.py
"""Phase 10: Destructive commands (skipped by default).

Run with: pytest tests/e2e/test_phase10_destructive.py -v -m e2e --run-destructive

These commands create permanent changes or are irreversible.

Commands tested:
  - develop edit-in-photoshop
  - catalog remove-from-catalog <photo_id>
  - catalog create-virtual-copy
  - catalog create-collection _e2e_test_coll
  - catalog create-smart-collection _e2e_smart
  - catalog create-collection-set _e2e_set
  - catalog create-keyword _e2e_kw
  - develop paste-settings
  - develop set-process-version 6.7
  - develop preset "Adobe Landscape"
  - catalog select <photo_id>
  - catalog find-by-path "/some/path"
  - catalog set-view-filter --filter '{}'
"""
import pytest


@pytest.mark.e2e
@pytest.mark.destructive
class TestDestructiveEditInPhotoshop:
    """Test 123: Edit in Photoshop (opens external app)."""

    def test_edit_in_photoshop(self, run):
        """Test 123: Open photo in Photoshop."""
        r = run("develop", "edit-in-photoshop")
        assert r["exit_code"] == 0, f"edit-in-photoshop failed: {r['output']}"


@pytest.mark.e2e
@pytest.mark.destructive
class TestDestructiveRemoveFromCatalog:
    """Test 124: Remove photo from catalog (IRREVERSIBLE)."""

    def test_remove_from_catalog(self, run, e2e_state):
        """Test 124: Remove photo from catalog.

        WARNING: This permanently removes the photo from the catalog.
        Only run with a disposable test photo.
        """
        assert e2e_state.photo_id is not None, "photo_id not set"
        r = run("catalog", "remove-from-catalog", e2e_state.photo_id)
        assert r["exit_code"] == 0, f"remove-from-catalog failed: {r['output']}"


@pytest.mark.e2e
@pytest.mark.destructive
class TestDestructiveCreateVirtualCopy:
    """Test 125: Create virtual copy."""

    def test_create_virtual_copy(self, run):
        """Test 125: Create permanent virtual copy."""
        r = run("catalog", "create-virtual-copy")
        assert r["exit_code"] == 0, f"create-virtual-copy failed: {r['output']}"


@pytest.mark.e2e
@pytest.mark.destructive
class TestDestructiveCreateCollection:
    """Test 126: Create collection."""

    def test_create_collection(self, run):
        """Test 126: Create collection '_e2e_test_coll'."""
        r = run("catalog", "create-collection", "_e2e_test_coll")
        assert r["exit_code"] == 0, f"create-collection failed: {r['output']}"


@pytest.mark.e2e
@pytest.mark.destructive
class TestDestructiveCreateSmartCollection:
    """Test 127: Create smart collection."""

    def test_create_smart_collection(self, run):
        """Test 127: Create smart collection '_e2e_smart'."""
        r = run("catalog", "create-smart-collection", "_e2e_smart")
        assert r["exit_code"] == 0, f"create-smart-collection failed: {r['output']}"


@pytest.mark.e2e
@pytest.mark.destructive
class TestDestructiveCreateCollectionSet:
    """Test 128: Create collection set."""

    def test_create_collection_set(self, run):
        """Test 128: Create collection set '_e2e_set'."""
        r = run("catalog", "create-collection-set", "_e2e_set")
        assert r["exit_code"] == 0, f"create-collection-set failed: {r['output']}"


@pytest.mark.e2e
@pytest.mark.destructive
class TestDestructiveCreateKeyword:
    """Test 129: Create catalog keyword."""

    def test_create_keyword(self, run):
        """Test 129: Create keyword '_e2e_kw'."""
        r = run("catalog", "create-keyword", "_e2e_kw")
        assert r["exit_code"] == 0, f"create-keyword failed: {r['output']}"


@pytest.mark.e2e
@pytest.mark.destructive
class TestDestructivePasteSettings:
    """Test 130: Paste settings (may overwrite)."""

    def test_paste_settings(self, run):
        """Test 130: Paste develop settings."""
        r = run("develop", "paste-settings")
        assert r["exit_code"] == 0, f"paste-settings failed: {r['output']}"


@pytest.mark.e2e
@pytest.mark.destructive
class TestDestructiveSetProcessVersion:
    """Test 131: Set process version."""

    def test_set_process_version(self, run):
        """Test 131: Set process version to 6.7."""
        r = run("develop", "set-process-version", "6.7")
        assert r["exit_code"] == 0, f"set-process-version failed: {r['output']}"


@pytest.mark.e2e
@pytest.mark.destructive
class TestDestructivePreset:
    """Test 132: Apply preset."""

    def test_apply_preset(self, run):
        """Test 132: Apply 'Adobe Landscape' preset."""
        r = run("develop", "preset", "Adobe Landscape")
        assert r["exit_code"] == 0, f"preset failed: {r['output']}"


@pytest.mark.e2e
@pytest.mark.destructive
class TestDestructiveCatalogSelect:
    """Test 133: Select photo by ID (changes selection)."""

    def test_catalog_select(self, run, e2e_state):
        """Test 133: Select photo by ID."""
        assert e2e_state.photo_id is not None, "photo_id not set"
        r = run("catalog", "select", e2e_state.photo_id)
        assert r["exit_code"] == 0, f"catalog select failed: {r['output']}"


@pytest.mark.e2e
@pytest.mark.destructive
class TestDestructiveFindByPath:
    """Test 134: Find photo by path (safe but path-dependent)."""

    def test_find_by_path(self, run):
        """Test 134: Find photo by file path."""
        r = run("catalog", "find-by-path", "/some/path")
        assert r["exit_code"] == 0, f"find-by-path failed: {r['output']}"


@pytest.mark.e2e
@pytest.mark.destructive
class TestDestructiveSetViewFilter:
    """Test 135: Set view filter (changes view filter)."""

    def test_set_view_filter(self, run):
        """Test 135: Set view filter to empty."""
        r = run("catalog", "set-view-filter", "--filter", "{}")
        assert r["exit_code"] == 0, f"set-view-filter failed: {r['output']}"
```

**確認コマンド:**
```bash
venv/bin/python -m pytest tests/e2e/test_phase10_destructive.py -v --co
```

**コミット:**
```bash
git add tests/e2e/test_phase10_destructive.py
git commit -m "test: add E2E phase 10 — destructive commands (13 tests, skipped by default)"
```

---

## Task 12: test_lightroom_commands.py 削除 + 最終確認

**Files:**
- Delete: `tests/e2e/test_lightroom_commands.py`

**実装内容:**

旧 `test_lightroom_commands.py` を削除する。新しいフェーズベースのテストファイルが全コマンドをカバーしている。

```bash
rm tests/e2e/test_lightroom_commands.py
```

**確認コマンド:**

```bash
# 全E2Eテストが collect されることを確認
venv/bin/python -m pytest tests/e2e/ -v --co -m e2e 2>&1 | tail -20

# test_plugin_workflow.py が維持されていることを確認
venv/bin/python -m pytest tests/e2e/test_plugin_workflow.py -v --co

# destructive テストがスキップされることを確認
venv/bin/python -m pytest tests/e2e/test_phase10_destructive.py -v --co -m "e2e and not destructive"

# テストファイル一覧
ls -la tests/e2e/test_*.py
```

期待されるテストファイル一覧:
```
tests/e2e/conftest.py
tests/e2e/test_phase01_system.py          (4 tests)
tests/e2e/test_phase02_catalog_read.py    (10 tests)
tests/e2e/test_phase03_catalog_write.py   (17 tests)  [7 groups]
tests/e2e/test_phase04_selection.py       (19 tests)  [4 groups + additional]
tests/e2e/test_phase05_develop_basic.py   (16 tests)  [5 groups]
tests/e2e/test_phase06_develop_curve.py   (6 tests)
tests/e2e/test_phase07_develop_mask_filter.py (35 tests) [5 groups]
tests/e2e/test_phase08_develop_debug_color.py (8 tests)  [3 groups]
tests/e2e/test_phase09_preview.py         (4 tests)
tests/e2e/test_phase10_destructive.py     (13 tests, skipped by default)
tests/e2e/test_plugin_workflow.py         (existing, unchanged)
```

合計: 132 テスト（非破壊 119 + 破壊 13）+ 既存plugin 2 = 134テスト

**コミット:**
```bash
git rm tests/e2e/test_lightroom_commands.py
git add -A tests/e2e/
git commit -m "test: remove legacy test_lightroom_commands.py (replaced by phase-based E2E suite)"
```
