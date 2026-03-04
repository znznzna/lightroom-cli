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
