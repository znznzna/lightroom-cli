# tests/e2e/test_plugin_workflow.py
"""E2E tests for lr plugin commands.

Does NOT require Lightroom — filesystem only.
"""
import pytest
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.mark.e2e
class TestPluginWorkflow:
    """Full plugin lifecycle: install -> status -> uninstall -> status"""

    def test_full_lifecycle(self, tmp_path, monkeypatch, cli_runner):
        """install -> status -> uninstall -> status"""
        modules_dir = tmp_path / "Modules"
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))

        # Install
        result = cli_runner.invoke(cli, ["plugin", "install"])
        assert result.exit_code == 0
        assert "installed" in result.output.lower()

        # Status (installed)
        result = cli_runner.invoke(cli, ["plugin", "status"])
        assert result.exit_code == 0
        assert "copy" in result.output.lower()

        # Uninstall
        result = cli_runner.invoke(cli, ["plugin", "uninstall"])
        assert result.exit_code == 0
        assert "uninstalled" in result.output.lower()

        # Status (not installed)
        result = cli_runner.invoke(cli, ["plugin", "status"])
        assert result.exit_code == 0
        assert "not installed" in result.output.lower()

    def test_dev_mode_lifecycle(self, tmp_path, monkeypatch, cli_runner):
        """install --dev -> status -> uninstall"""
        modules_dir = tmp_path / "Modules"
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))

        # Install (dev)
        result = cli_runner.invoke(cli, ["plugin", "install", "--dev"])
        assert result.exit_code == 0
        assert "symlink" in result.output.lower()

        # Status
        result = cli_runner.invoke(cli, ["plugin", "status"])
        assert result.exit_code == 0
        assert "symlink" in result.output.lower()

        # Uninstall
        result = cli_runner.invoke(cli, ["plugin", "uninstall"])
        assert result.exit_code == 0
