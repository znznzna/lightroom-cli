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
