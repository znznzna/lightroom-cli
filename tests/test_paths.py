from pathlib import Path
from unittest.mock import patch

import pytest

import lightroom_sdk.paths


class TestGetPortFile:
    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("LR_PORT_FILE", "/custom/path.txt")
        from lightroom_sdk.paths import get_port_file

        assert get_port_file() == Path("/custom/path.txt")

    def test_default_uses_tmp_on_macos(self, monkeypatch):
        monkeypatch.delenv("LR_PORT_FILE", raising=False)
        with patch("sys.platform", "darwin"):
            result = lightroom_sdk.paths.get_port_file()
        # macOS/Linux では /tmp を使用（Lightroom SDK と一致）
        assert result == Path("/tmp") / "lightroom_ports.txt"

    def test_env_override_takes_priority(self, monkeypatch):
        monkeypatch.setenv("LR_PORT_FILE", "/override/ports.txt")
        result = lightroom_sdk.paths.get_port_file()
        assert result == Path("/override/ports.txt")


class TestGetLightroomModulesDir:
    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("LR_PLUGIN_DIR", "/custom/modules")
        from lightroom_sdk.paths import get_lightroom_modules_dir

        assert get_lightroom_modules_dir() == Path("/custom/modules")

    def test_macos_default(self, monkeypatch):
        monkeypatch.delenv("LR_PLUGIN_DIR", raising=False)
        with patch("sys.platform", "darwin"):
            result = lightroom_sdk.paths.get_lightroom_modules_dir()
            assert "Library/Application Support/Adobe/Lightroom/Modules" in str(result)

    def test_linux_raises(self, monkeypatch):
        monkeypatch.delenv("LR_PLUGIN_DIR", raising=False)
        with patch("sys.platform", "linux"):
            with pytest.raises(RuntimeError, match="Unsupported platform"):
                lightroom_sdk.paths.get_lightroom_modules_dir()

    def test_env_override_bypasses_platform_check(self, monkeypatch):
        monkeypatch.setenv("LR_PLUGIN_DIR", "/custom/lr/modules")
        with patch("sys.platform", "linux"):
            result = lightroom_sdk.paths.get_lightroom_modules_dir()
            assert result == Path("/custom/lr/modules")


class TestGetPluginSourceDir:
    def test_returns_existing_plugin_dir(self):
        from lightroom_sdk.paths import get_plugin_source_dir

        result = get_plugin_source_dir()
        assert result.name == "plugin"
        assert result.exists()

    def test_contains_info_lua(self):
        from lightroom_sdk.paths import get_plugin_source_dir

        result = get_plugin_source_dir()
        assert (result / "Info.lua").exists()


class TestConstants:
    def test_plugin_name(self):
        from lightroom_sdk.paths import PLUGIN_NAME

        assert PLUGIN_NAME == "lightroom-cli-bridge.lrplugin"


class TestSocketBridgeUsesPathsModule:
    def test_default_port_file_matches_paths(self):
        from lightroom_sdk.paths import get_port_file
        from lightroom_sdk.socket_bridge import SocketBridge

        bridge = SocketBridge()
        assert bridge.port_file == get_port_file()


class TestResilientBridgeUsesPathsModule:
    def test_default_port_file_matches_paths(self):
        from lightroom_sdk.paths import get_port_file
        from lightroom_sdk.resilient_bridge import ResilientSocketBridge

        bridge = ResilientSocketBridge()
        assert bridge._port_file == str(get_port_file())


class TestSystemCommandUsesPathsModule:
    def test_get_bridge_default_uses_paths(self):
        import inspect

        from cli.helpers import get_bridge

        sig = inspect.signature(get_bridge)
        default = sig.parameters["port_file"].default
        assert default is None


import tempfile
from unittest.mock import patch as stdlib_patch


def test_get_port_file_macos_uses_tmp():
    """macOS では /tmp を使用すること（Lightroom SDK と一致）"""
    from lightroom_sdk.paths import get_port_file
    import os

    with patch.dict("os.environ", {}, clear=True):
        os.environ.pop("LR_PORT_FILE", None)
        with stdlib_patch("lightroom_sdk.paths.sys") as mock_sys:
            mock_sys.platform = "darwin"
            result = get_port_file()
        assert result == Path("/tmp") / "lightroom_ports.txt"


def test_get_port_file_windows_uses_tempfile():
    """Windows では tempfile.gettempdir() を使用すること"""
    from lightroom_sdk.paths import get_port_file
    import os

    with patch.dict("os.environ", {}, clear=True):
        os.environ.pop("LR_PORT_FILE", None)
        with stdlib_patch("lightroom_sdk.paths.sys") as mock_sys:
            mock_sys.platform = "win32"
            result = get_port_file()
        assert result == Path(tempfile.gettempdir()) / "lightroom_ports.txt"


class TestWindowsPaths:
    def test_get_port_file_windows(self):
        """Windows でも tempfile.gettempdir() が使われること"""
        import os
        import tempfile
        from unittest.mock import patch as stdlib_patch

        with patch.dict("os.environ", {}, clear=True):
            os.environ.pop("LR_PORT_FILE", None)
            with stdlib_patch("lightroom_sdk.paths.sys") as mock_sys:
                mock_sys.platform = "win32"
                result = lightroom_sdk.paths.get_port_file()
            assert result == Path(tempfile.gettempdir()) / "lightroom_ports.txt"

    def test_get_lightroom_modules_dir_windows(self):
        """Windows で APPDATA ベースのパスが返ること"""
        import os
        from unittest.mock import patch as stdlib_patch

        with (
            stdlib_patch("lightroom_sdk.paths.sys") as mock_sys,
            patch.dict("os.environ", {"APPDATA": r"C:\Users\test\AppData\Roaming"}, clear=False),
        ):
            mock_sys.platform = "win32"
            os.environ.pop("LR_PLUGIN_DIR", None)
            result = lightroom_sdk.paths.get_lightroom_modules_dir()
            assert "Adobe" in str(result)
            assert "Lightroom" in str(result)
            assert "Modules" in str(result)

    def test_get_port_file_env_override(self):
        """LR_PORT_FILE 環境変数が優先されること"""
        with patch.dict("os.environ", {"LR_PORT_FILE": "/custom/ports.txt"}):
            from lightroom_sdk.paths import get_port_file
            result = get_port_file()
            assert result == Path("/custom/ports.txt")
