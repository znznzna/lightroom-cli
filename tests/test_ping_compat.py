"""ping レスポンス互換性テスト"""

from pathlib import Path


def test_plugin_init_lua_has_protocol_version():
    """PluginInit.lua の ping レスポンスに protocolVersion が含まれること"""
    root = Path(__file__).resolve().parent.parent
    lua_content = (root / "lightroom_sdk" / "plugin" / "PluginInit.lua").read_text()
    assert 'protocolVersion = "1"' in lua_content
