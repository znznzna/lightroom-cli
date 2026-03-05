# tests/e2e/conftest.py
"""E2E test fixtures and configuration.

Run: pytest tests/e2e/ -v -m e2e
Run destructive: pytest tests/e2e/ -v -m e2e --run-destructive
"""
import json
import pytest
from dataclasses import dataclass, field
from typing import Any
from click.testing import CliRunner
from lightroom_sdk.paths import get_port_file


# --- State container shared across entire session ---


@dataclass
class E2EState:
    """Mutable state shared across all E2E test phases.

    Populated by early phases, consumed by later ones.
    """
    photo_id: str | None = None
    photo_ids: list[str] = field(default_factory=list)
    original_rating: int | None = None
    original_flag: str | None = None
    original_color_label: str | None = None
    original_title: str | None = None
    original_caption: str | None = None
    original_develop_settings: dict[str, Any] | None = None
    created_collection_name: str | None = None
    created_keyword: str | None = None
    created_snapshot_name: str | None = None
    created_mask_id: str | None = None


_state = E2EState()


# --- CLI Command Options ---


def pytest_addoption(parser):
    parser.addoption(
        "--run-destructive",
        action="store_true",
        default=False,
        help="Run destructive E2E tests",
    )


# --- Skip Logic ---


def _lightroom_reachable() -> bool:
    """Check if Lightroom is actually reachable by attempting TCP connections to both ports."""
    import socket
    port_file = get_port_file()
    if not port_file.exists():
        return False
    try:
        ports = port_file.read_text().strip().split(",")
        if len(ports) < 2:
            return False
        for port_str in ports:
            sock = socket.create_connection(("127.0.0.1", int(port_str)), timeout=2)
            sock.close()
        return True
    except (OSError, ValueError, IndexError):
        return False


def pytest_collection_modifyitems(config, items):
    """Auto-skip e2e tests when Lightroom is not running.
    Auto-skip destructive tests unless --run-destructive is passed.
    """
    skip_e2e = None
    if not _lightroom_reachable():
        skip_e2e = pytest.mark.skip(
            reason="Lightroom not reachable (port file missing or connection refused)"
        )

    skip_destructive = None
    if not config.getoption("--run-destructive"):
        skip_destructive = pytest.mark.skip(reason="Destructive test (use --run-destructive)")

    for item in items:
        if "e2e" in item.keywords:
            if skip_e2e:
                item.add_marker(skip_e2e)
            if "destructive" in item.keywords and skip_destructive:
                item.add_marker(skip_destructive)


# --- Fixtures ---


@pytest.fixture(scope="session")
def e2e_state():
    """Shared mutable state across the entire E2E session."""
    return _state


@pytest.fixture(scope="session")
def runner():
    """Click CliRunner for invoking CLI commands."""
    return CliRunner()


@pytest.fixture(scope="session")
def cli_app():
    """The CLI application."""
    from cli.main import cli
    return cli


def invoke(runner, cli_app, args: list[str], fmt: str = "json") -> dict:
    """Helper: invoke CLI command and return parsed result.

    Args:
        runner: CliRunner instance
        cli_app: Click CLI group
        args: Command arguments (e.g. ["system", "ping"])
        fmt: Output format ("json" for machine-parseable, "text" for display)

    Returns:
        dict with keys:
          - exit_code: int
          - output: str (raw output)
          - data: parsed JSON (if fmt="json") or None
    """
    full_args = ["-o", fmt] + args
    result = runner.invoke(cli_app, full_args)
    data = None
    if fmt == "json" and result.output.strip():
        try:
            data = json.loads(result.output)
        except json.JSONDecodeError:
            pass
    return {
        "exit_code": result.exit_code,
        "output": result.output,
        "data": data,
    }


@pytest.fixture(scope="session")
def run(runner, cli_app):
    """Convenience fixture: run("system", "ping") -> dict."""
    def _run(*args, fmt="json"):
        return invoke(runner, cli_app, list(args), fmt=fmt)
    return _run


# --- Session-level fallback cleanup ---


@pytest.fixture(scope="session", autouse=True)
def session_cleanup(run, e2e_state):
    """Final cleanup at end of E2E session."""
    yield
    # Emergency cleanup: reset develop to defaults
    run("develop", "reset")
    # Unflag
    run("selection", "unflag")
    # Reset rating
    run("selection", "set-rating", "0")
    # Reset color label
    run("selection", "color-label", "none")
    # Restore original selection if we have the photo_id
    if e2e_state.photo_id:
        run("catalog", "select", e2e_state.photo_id)
