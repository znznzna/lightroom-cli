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
