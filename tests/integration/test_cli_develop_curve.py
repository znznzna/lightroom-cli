import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.helpers.get_bridge")
def test_develop_curve_get(mock_get_bridge, runner):
    """lr develop curve get がカーブポイントを取得する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"points": [[0, 0], [128, 128], [255, 255]]},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "curve", "get"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.getCurvePoints", {"param": "ToneCurvePV2012"}, timeout=30.0
    )


@patch("cli.helpers.get_bridge")
def test_develop_curve_set(mock_get_bridge, runner):
    """lr develop curve set がカーブポイントを設定する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "2", "success": True,
        "result": {"applied": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "curve", "set", "--points", "[[0,0],[128,140],[255,255]]"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.setCurvePoints", {"param": "ToneCurvePV2012", "points": [{"x": 0, "y": 0}, {"x": 128, "y": 140}, {"x": 255, "y": 255}]}, timeout=30.0
    )


@patch("cli.helpers.get_bridge")
def test_develop_curve_linear(mock_get_bridge, runner):
    """lr develop curve linear がリニアカーブをセットする"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "3", "success": True,
        "result": {"applied": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "curve", "linear"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.setCurveLinear", {"param": "ToneCurvePV2012"}, timeout=30.0
    )


@patch("cli.helpers.get_bridge")
def test_develop_curve_s_curve(mock_get_bridge, runner):
    """lr develop curve s-curve がSカーブをセットする"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "4", "success": True,
        "result": {"applied": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "curve", "s-curve"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.setCurveSCurve", {"param": "ToneCurvePV2012"}, timeout=30.0
    )


@patch("cli.helpers.get_bridge")
def test_develop_curve_add_point(mock_get_bridge, runner):
    """lr develop curve add-point がカーブにポイントを追加する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "5", "success": True,
        "result": {"added": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "curve", "add-point", "128", "140"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.addCurvePoint", {"param": "ToneCurvePV2012", "x": 128.0, "y": 140.0}, timeout=30.0
    )


@patch("cli.helpers.get_bridge")
def test_develop_curve_remove_point(mock_get_bridge, runner):
    """lr develop curve remove-point がカーブからポイントを削除する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "6", "success": True,
        "result": {"removed": True},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["develop", "curve", "remove-point", "1"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "develop.removeCurvePoint", {"param": "ToneCurvePV2012", "index": 1}, timeout=30.0
    )
