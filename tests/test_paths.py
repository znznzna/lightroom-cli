import pytest
from unittest.mock import patch
from pathlib import Path

import lightroom_sdk.paths


class TestGetPortFile:
    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("LR_PORT_FILE", "/custom/path.txt")
        from lightroom_sdk.paths import get_port_file
        assert get_port_file() == Path("/custom/path.txt")

    def test_macos_default(self, monkeypatch):
        monkeypatch.delenv("LR_PORT_FILE", raising=False)
        with patch.object(lightroom_sdk.paths.sys, "platform", "darwin"):
            result = lightroom_sdk.paths.get_port_file()
            assert result == Path("/tmp/lightroom_ports.txt")

    def test_linux_default(self, monkeypatch):
        monkeypatch.delenv("LR_PORT_FILE", raising=False)
        with patch.object(lightroom_sdk.paths.sys, "platform", "linux"):
            result = lightroom_sdk.paths.get_port_file()
            assert result == Path("/tmp/lightroom_ports.txt")

    def test_env_override_takes_priority(self, monkeypatch):
        monkeypatch.setenv("LR_PORT_FILE", "/override/ports.txt")
        with patch.object(lightroom_sdk.paths.sys, "platform", "darwin"):
            result = lightroom_sdk.paths.get_port_file()
            assert result == Path("/override/ports.txt")


class TestGetLightroomModulesDir:
    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("LR_PLUGIN_DIR", "/custom/modules")
        from lightroom_sdk.paths import get_lightroom_modules_dir
        assert get_lightroom_modules_dir() == Path("/custom/modules")

    def test_macos_default(self, monkeypatch):
        monkeypatch.delenv("LR_PLUGIN_DIR", raising=False)
        with patch.object(lightroom_sdk.paths.sys, "platform", "darwin"):
            result = lightroom_sdk.paths.get_lightroom_modules_dir()
            assert "Library/Application Support/Adobe/Lightroom/Modules" in str(result)

    def test_linux_raises(self, monkeypatch):
        monkeypatch.delenv("LR_PLUGIN_DIR", raising=False)
        with patch.object(lightroom_sdk.paths.sys, "platform", "linux"):
            with pytest.raises(RuntimeError, match="Unsupported platform"):
                lightroom_sdk.paths.get_lightroom_modules_dir()

    def test_env_override_bypasses_platform_check(self, monkeypatch):
        monkeypatch.setenv("LR_PLUGIN_DIR", "/custom/lr/modules")
        with patch.object(lightroom_sdk.paths.sys, "platform", "linux"):
            result = lightroom_sdk.paths.get_lightroom_modules_dir()
            assert result == Path("/custom/lr/modules")


class TestGetPluginSourceDir:
    def test_returns_existing_plugin_dir(self):
        from lightroom_sdk.paths import get_plugin_source_dir
        result = get_plugin_source_dir()
        assert result.name == "lightroom-plugin"
        assert result.exists()

    def test_contains_info_lua(self):
        from lightroom_sdk.paths import get_plugin_source_dir
        result = get_plugin_source_dir()
        assert (result / "Info.lua").exists()


class TestConstants:
    def test_plugin_name(self):
        from lightroom_sdk.paths import PLUGIN_NAME
        assert PLUGIN_NAME == "lightroom-python-bridge.lrdevplugin"
