# tests/e2e/test_lightroom_commands.py
"""Lightroom Classic live connection tests.

Auto-skipped when Lightroom is not running (port file missing).

Run: pytest tests/e2e/test_lightroom_commands.py -v -m e2e
"""
import pytest


@pytest.mark.e2e
class TestSystemCommands:
    """system module live tests"""

    def test_ping(self, lr_bridge):
        bridge, loop = lr_bridge
        result = loop.run_until_complete(
            bridge.send_command("system.ping", timeout=5.0)
        )
        assert result.get("success") is True

    def test_status(self, lr_bridge):
        bridge, loop = lr_bridge
        result = loop.run_until_complete(
            bridge.send_command("system.status", timeout=5.0)
        )
        assert result.get("success") is True
        assert "result" in result


@pytest.mark.e2e
class TestCatalogCommands:
    """catalog module live tests"""

    def test_get_selected_photos(self, lr_bridge):
        bridge, loop = lr_bridge
        result = loop.run_until_complete(
            bridge.send_command("catalog.getSelectedPhotos", timeout=10.0)
        )
        assert result.get("success") is True

    def test_get_active_catalog(self, lr_bridge):
        bridge, loop = lr_bridge
        result = loop.run_until_complete(
            bridge.send_command("catalog.getActiveCatalog", timeout=10.0)
        )
        assert result.get("success") is True


@pytest.mark.e2e
class TestDevelopCommands:
    """develop module live tests"""

    def test_get_settings(self, lr_bridge):
        """Get develop settings (requires photo selected)"""
        bridge, loop = lr_bridge
        result = loop.run_until_complete(
            bridge.send_command("develop.getSettings", timeout=10.0)
        )
        assert "success" in result or "error" in result

    def test_get_single_param(self, lr_bridge):
        """Get single parameter"""
        bridge, loop = lr_bridge
        result = loop.run_until_complete(
            bridge.send_command(
                "develop.getValue",
                params={"param": "Exposure"},
                timeout=10.0,
            )
        )
        assert "success" in result or "error" in result


@pytest.mark.e2e
class TestSelectionCommands:
    """selection module live tests"""

    def test_get_rating(self, lr_bridge):
        bridge, loop = lr_bridge
        result = loop.run_until_complete(
            bridge.send_command("selection.getRating", timeout=10.0)
        )
        assert "success" in result or "error" in result

    def test_get_flag(self, lr_bridge):
        bridge, loop = lr_bridge
        result = loop.run_until_complete(
            bridge.send_command("selection.getFlag", timeout=10.0)
        )
        assert "success" in result or "error" in result


@pytest.mark.e2e
class TestPreviewCommands:
    """preview module live tests"""

    def test_get_preview_info(self, lr_bridge):
        bridge, loop = lr_bridge
        result = loop.run_until_complete(
            bridge.send_command("preview.getInfo", timeout=15.0)
        )
        assert "success" in result or "error" in result
