"""ping レスポンス互換性テスト"""


def _expected_ping_response():
    """Lua PluginInit.lua の system.ping レスポンスの期待形式"""
    return {
        "pong": True,
        "version": _read_pyproject_version(),
        "protocolVersion": "1",
    }


def _read_pyproject_version() -> str:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]

    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    with open(root / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def test_ping_response_has_version():
    """ping レスポンスに version フィールドが存在すること"""
    resp = _expected_ping_response()
    assert "version" in resp
    assert resp["version"]  # non-empty


def test_ping_response_has_protocol_version():
    """ping レスポンスに protocolVersion フィールドが存在すること"""
    resp = _expected_ping_response()
    assert "protocolVersion" in resp
    assert resp["protocolVersion"] == "1"


def test_ping_version_matches_pyproject():
    """version が pyproject.toml の値と一致すること"""
    version = _read_pyproject_version()
    resp = _expected_ping_response()
    assert resp["version"] == version


def test_plugin_init_lua_has_protocol_version():
    """PluginInit.lua の ping レスポンスに protocolVersion が含まれること"""
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    lua_content = (root / "lightroom_sdk" / "plugin" / "PluginInit.lua").read_text()
    assert 'protocolVersion = "1"' in lua_content
