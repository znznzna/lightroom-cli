import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.commands.catalog.get_bridge")
def test_catalog_create_collection(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "1", "success": True, "result": {"name": "My Collection"}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["catalog", "create-collection", "My Collection"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("catalog.createCollection", {"name": "My Collection"}, timeout=30.0)


@patch("cli.commands.catalog.get_bridge")
def test_catalog_create_smart_collection(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "2", "success": True, "result": {"name": "Smart"}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["catalog", "create-smart-collection", "Smart"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("catalog.createSmartCollection", {"name": "Smart"}, timeout=30.0)


@patch("cli.commands.catalog.get_bridge")
def test_catalog_create_collection_set(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "3", "success": True, "result": {"name": "Set"}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["catalog", "create-collection-set", "Set"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("catalog.createCollectionSet", {"name": "Set"}, timeout=30.0)


@patch("cli.commands.catalog.get_bridge")
def test_catalog_create_keyword(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "4", "success": True, "result": {"keyword": "sunset"}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["catalog", "create-keyword", "sunset"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("catalog.createKeyword", {"keyword": "sunset"}, timeout=30.0)


@patch("cli.commands.catalog.get_bridge")
def test_catalog_remove_keyword(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "5", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["catalog", "remove-keyword", "123", "sunset"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("catalog.removeKeyword", {"photoId": "123", "keyword": "sunset"}, timeout=30.0)


@patch("cli.commands.catalog.get_bridge")
def test_catalog_set_view_filter(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "6", "success": True, "result": {}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["catalog", "set-view-filter", "--filter", '{"rating": 3}'])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("catalog.setViewFilter", {"filter": {"rating": 3}}, timeout=30.0)


@patch("cli.commands.catalog.get_bridge")
def test_catalog_get_view_filter(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "7", "success": True, "result": {"filter": {}}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["catalog", "get-view-filter"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("catalog.getCurrentViewFilter", {}, timeout=30.0)


@patch("cli.commands.catalog.get_bridge")
def test_catalog_remove_from_catalog(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {"id": "8", "success": True, "result": {"message": "Removed"}}
    mock_get_bridge.return_value = mock_bridge
    result = runner.invoke(cli, ["catalog", "remove-from-catalog", "123"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with("catalog.removeFromCatalog", {"photoId": "123"}, timeout=30.0)
