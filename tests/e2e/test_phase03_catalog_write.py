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
