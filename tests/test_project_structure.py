from pathlib import Path
import tomllib

PROJECT_ROOT = Path(__file__).parent.parent


def test_mcp_server_dir_removed():
    """mcp_server/ディレクトリが存在しないことを検証"""
    assert not (PROJECT_ROOT / "mcp_server").exists()


def test_pyproject_has_cli_entry_point():
    """pyproject.tomlに lr コマンドが定義されていることを検証"""
    pyproject = PROJECT_ROOT / "pyproject.toml"
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)
    scripts = data.get("project", {}).get("scripts", {})
    assert "lr" in scripts
    assert scripts["lr"] == "cli.main:cli"


def test_pyproject_no_fastmcp_dependency():
    """fastmcp依存が削除されていることを検証"""
    pyproject = PROJECT_ROOT / "pyproject.toml"
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)
    deps = data.get("project", {}).get("dependencies", [])
    assert not any("fastmcp" in d for d in deps)


def test_pyproject_has_click_dependency():
    """click依存が追加されていることを検証"""
    pyproject = PROJECT_ROOT / "pyproject.toml"
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)
    deps = data.get("project", {}).get("dependencies", [])
    assert any("click" in d for d in deps)
