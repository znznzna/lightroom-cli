import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.commands.catalog.get_bridge")
def test_catalog_get_info_includes_pick_status(mock_get_bridge, runner):
    """lr catalog get-info がpickStatusを含むメタデータを返す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1",
        "success": True,
        "result": {
            "id": 12345,
            "filename": "IMG_001.jpg",
            "rating": 3,
            "pickStatus": 1,
            "colorLabel": "red",
        },
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["catalog", "get-info", "12345"])
    assert result.exit_code == 0
    assert "pickStatus" in result.output
