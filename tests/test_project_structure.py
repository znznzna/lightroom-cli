from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def test_mcp_server_dir_removed():
    """mcp_server/ディレクトリが存在しないことを検証"""
    assert not (PROJECT_ROOT / "mcp_server").exists()


def _read_pyproject():
    """pyproject.tomlをパースする（Python 3.10互換）"""
    pyproject = PROJECT_ROOT / "pyproject.toml"
    text = pyproject.read_text()
    # Simple parsing for the fields we need
    return text


def test_pyproject_has_cli_entry_point():
    """pyproject.tomlに lr コマンドが定義されていることを検証"""
    text = _read_pyproject()
    assert 'lr = "cli.main:cli"' in text


def test_pyproject_no_fastmcp_dependency():
    """fastmcp依存が削除されていることを検証"""
    text = _read_pyproject()
    assert "fastmcp" not in text


def test_pyproject_has_click_dependency():
    """click依存が追加されていることを検証"""
    text = _read_pyproject()
    assert "click" in text
