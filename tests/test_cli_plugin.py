import pytest
from click.testing import CliRunner

from cli.main import cli
from lightroom_sdk.paths import PLUGIN_NAME


@pytest.fixture
def runner():
    return CliRunner()


class TestPluginInstall:
    def test_install_copy(self, tmp_path, monkeypatch, runner):
        modules_dir = tmp_path / "Modules"
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))
        result = runner.invoke(cli, ["plugin", "install"])
        assert result.exit_code == 0
        assert "installed" in result.output.lower() or "Plugin installed" in result.output
        dest = modules_dir / PLUGIN_NAME
        assert dest.exists()
        assert not dest.is_symlink()
        assert (dest / "Info.lua").exists()

    def test_install_dev_symlink(self, tmp_path, monkeypatch, runner):
        modules_dir = tmp_path / "Modules"
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))
        result = runner.invoke(cli, ["plugin", "install", "--dev"])
        assert result.exit_code == 0
        assert "symlink" in result.output.lower()
        dest = modules_dir / PLUGIN_NAME
        assert dest.is_symlink()

    def test_install_overwrites_existing(self, tmp_path, monkeypatch, runner):
        modules_dir = tmp_path / "Modules"
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))
        runner.invoke(cli, ["plugin", "install"])
        result = runner.invoke(cli, ["plugin", "install"])
        assert result.exit_code == 0

    def test_install_quiet(self, tmp_path, monkeypatch, runner):
        modules_dir = tmp_path / "Modules"
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))
        result = runner.invoke(cli, ["plugin", "install", "--quiet"])
        assert result.exit_code == 0
        assert result.output.strip() == ""


class TestPluginUninstall:
    def test_uninstall_copy(self, tmp_path, monkeypatch, runner):
        modules_dir = tmp_path / "Modules"
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))
        runner.invoke(cli, ["plugin", "install"])
        result = runner.invoke(cli, ["plugin", "uninstall"])
        assert result.exit_code == 0
        assert "uninstalled" in result.output.lower()
        dest = modules_dir / PLUGIN_NAME
        assert not dest.exists()

    def test_uninstall_symlink(self, tmp_path, monkeypatch, runner):
        modules_dir = tmp_path / "Modules"
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))
        runner.invoke(cli, ["plugin", "install", "--dev"])
        result = runner.invoke(cli, ["plugin", "uninstall"])
        assert result.exit_code == 0
        dest = modules_dir / PLUGIN_NAME
        assert not dest.exists()

    def test_uninstall_not_installed(self, tmp_path, monkeypatch, runner):
        modules_dir = tmp_path / "Modules"
        modules_dir.mkdir(parents=True)
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))
        result = runner.invoke(cli, ["plugin", "uninstall"])
        assert result.exit_code == 0
        assert "not installed" in result.output.lower()


class TestPluginStatus:
    def test_status_not_installed(self, tmp_path, monkeypatch, runner):
        modules_dir = tmp_path / "Modules"
        modules_dir.mkdir(parents=True)
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))
        result = runner.invoke(cli, ["plugin", "status"])
        assert result.exit_code == 0
        assert "not installed" in result.output.lower()

    def test_status_installed_copy(self, tmp_path, monkeypatch, runner):
        modules_dir = tmp_path / "Modules"
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))
        runner.invoke(cli, ["plugin", "install"])
        result = runner.invoke(cli, ["plugin", "status"])
        assert result.exit_code == 0
        assert "copy" in result.output.lower()

    def test_status_installed_symlink(self, tmp_path, monkeypatch, runner):
        modules_dir = tmp_path / "Modules"
        monkeypatch.setenv("LR_PLUGIN_DIR", str(modules_dir))
        runner.invoke(cli, ["plugin", "install", "--dev"])
        result = runner.invoke(cli, ["plugin", "status"])
        assert result.exit_code == 0
        assert "symlink" in result.output.lower()
