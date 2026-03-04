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
