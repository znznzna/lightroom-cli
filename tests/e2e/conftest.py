# tests/e2e/conftest.py
"""E2E test fixtures.

E2E tests require Lightroom Classic running with the plugin active.
Not runnable in CI.

Run: pytest tests/e2e/ -v -m e2e
"""
import pytest
import asyncio
from lightroom_sdk.paths import get_port_file


def pytest_collection_modifyitems(config, items):
    """Auto-skip e2e tests when Lightroom is not running."""
    port_file = get_port_file()
    if not port_file.exists():
        skip_e2e = pytest.mark.skip(
            reason=f"Lightroom not running (port file not found: {port_file})"
        )
        for item in items:
            if "e2e" in item.keywords:
                item.add_marker(skip_e2e)


@pytest.fixture
def lr_bridge():
    """Establish a real connection to Lightroom."""
    from lightroom_sdk.resilient_bridge import ResilientSocketBridge

    bridge = ResilientSocketBridge()
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(bridge.connect())
        yield bridge, loop
    finally:
        loop.run_until_complete(bridge.disconnect())
        loop.close()
