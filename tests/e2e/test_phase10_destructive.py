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
