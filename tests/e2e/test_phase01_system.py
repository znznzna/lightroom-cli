# tests/e2e/test_phase01_system.py
"""Phase 1: System commands - verify Lightroom connection is alive.

If these fail, all subsequent phases are meaningless.

Commands tested:
  - system ping
  - system status
  - system check-connection
  - system reconnect
"""

import pytest


@pytest.mark.e2e
class TestSystemPing:
    """Test 1: system ping — gate test for entire E2E suite."""

    def test_system_ping(self, run):
        r = run("system", "ping")
        assert r["exit_code"] == 0, f"ping failed: {r['output']}"
        assert r["data"] is not None, f"ping returned no JSON data: {r['output']}"


@pytest.mark.e2e
class TestSystemStatus:
    """Test 2: system status — verify version/state info."""

    def test_system_status(self, run):
        r = run("system", "status")
        assert r["exit_code"] == 0, f"status failed: {r['output']}"
        assert r["data"] is not None, f"status returned no JSON data: {r['output']}"


@pytest.mark.e2e
class TestSystemCheckConnection:
    """Test 3: system check-connection — verify connection check."""

    def test_system_check_connection(self, run):
        r = run("system", "check-connection", fmt="text")
        assert r["exit_code"] == 0, f"check-connection failed: {r['output']}"
        assert "ok" in r["output"].lower(), f"Expected 'ok' in output: {r['output']}"


@pytest.mark.e2e
class TestSystemReconnect:
    """Test 4: system reconnect — force reconnection."""

    def test_system_reconnect(self, run):
        r = run("system", "reconnect", fmt="text")
        assert r["exit_code"] == 0, f"reconnect failed: {r['output']}"
        assert "reconnected" in r["output"].lower(), f"Expected 'Reconnected' in output: {r['output']}"
