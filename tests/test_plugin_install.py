"""lr plugin install / status / uninstall on a temporary Modules directory.

Filesystem only, no Lightroom: these used to sit under tests/e2e and were never run, because
the e2e suite is excluded from CI and skipped without a reachable Lightroom (codex-tests #9).
"""

import os

import pytest
from click.testing import CliRunner

from cli.main import cli
from lightroom_sdk.paths import PLUGIN_NAME, get_plugin_source_dir


@pytest.fixture
def modules_dir(tmp_path, monkeypatch):
    directory = tmp_path / "Modules"
    monkeypatch.setenv("LR_PLUGIN_DIR", str(directory))
    return directory


@pytest.fixture
def cli_runner():
    return CliRunner()


def _can_symlink(tmp_path) -> bool:
    """Windows without Developer Mode or admin rights cannot create symlinks"""
    probe = tmp_path / "symlink-probe"
    try:
        os.symlink(tmp_path, probe, target_is_directory=True)
    except OSError:
        return False
    probe.unlink()
    return True


def test_full_lifecycle(modules_dir, cli_runner):
    """install -> status -> uninstall -> status"""
    dest = modules_dir / PLUGIN_NAME

    result = cli_runner.invoke(cli, ["plugin", "install"])
    assert result.exit_code == 0
    assert "installed" in result.output.lower()
    assert dest.is_dir() and not dest.is_symlink()
    assert (dest / "Info.lua").read_bytes() == (get_plugin_source_dir() / "Info.lua").read_bytes()

    result = cli_runner.invoke(cli, ["plugin", "status"])
    assert result.exit_code == 0
    assert "copy" in result.output.lower()

    result = cli_runner.invoke(cli, ["plugin", "uninstall"])
    assert result.exit_code == 0
    assert "uninstalled" in result.output.lower()
    assert not dest.exists()

    result = cli_runner.invoke(cli, ["plugin", "status"])
    assert result.exit_code == 0
    assert "not installed" in result.output.lower()


def test_dev_mode_lifecycle(modules_dir, cli_runner, tmp_path):
    """install --dev -> status -> uninstall; a copy is the documented fallback without symlink rights"""
    dest = modules_dir / PLUGIN_NAME
    source = get_plugin_source_dir()

    result = cli_runner.invoke(cli, ["plugin", "install", "--dev"])
    assert result.exit_code == 0
    if _can_symlink(tmp_path):
        assert dest.is_symlink()
        assert dest.resolve() == source.resolve()
        assert "symlink" in result.output.lower()
        expected_status = "symlink"
    else:
        assert dest.is_dir() and not dest.is_symlink()
        assert "copy fallback" in result.output.lower()
        expected_status = "copy"

    result = cli_runner.invoke(cli, ["plugin", "status"])
    assert result.exit_code == 0
    assert expected_status in result.output.lower()

    result = cli_runner.invoke(cli, ["plugin", "uninstall"])
    assert result.exit_code == 0
    assert not dest.exists() and not dest.is_symlink()
    assert source.is_dir(), "uninstalling a dev install must not delete the plugin source"


def test_reinstall_replaces_previous_install(modules_dir, cli_runner):
    dest = modules_dir / PLUGIN_NAME
    assert cli_runner.invoke(cli, ["plugin", "install"]).exit_code == 0
    (dest / "stale.lua").write_text("-- left over from an old version")
    assert cli_runner.invoke(cli, ["plugin", "install"]).exit_code == 0
    assert not (dest / "stale.lua").exists()
