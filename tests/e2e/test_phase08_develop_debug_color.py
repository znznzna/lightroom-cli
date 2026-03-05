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
