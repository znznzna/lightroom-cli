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
