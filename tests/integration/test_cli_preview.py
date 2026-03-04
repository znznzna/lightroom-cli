import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.commands.preview.get_bridge")
def test_preview_generate_current(mock_get_bridge, runner):
    """lr preview generate-current が現在の写真のプレビューを生成する"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1", "success": True,
        "result": {"path": "/tmp/preview.jpg"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["preview", "generate-current"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "preview.generatePreview", {}, timeout=120.0
    )


@patch("cli.commands.preview.get_bridge")
def test_preview_generate_with_options(mock_get_bridge, runner):
    """lr preview generate --size 2048 --format png がオプションを渡す"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "2", "success": True,
        "result": {"path": "/tmp/preview.png"},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["preview", "generate", "--size", "2048", "--format", "png"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "preview.generatePreview", {"size": 2048, "format": "png"}, timeout=120.0
    )


@patch("cli.commands.preview.get_bridge")
def test_preview_generate_batch(mock_get_bridge, runner):
    """lr preview generate-batch がバッチプレビュー生成する（タイムアウト300秒）"""
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "3", "success": True,
        "result": {"count": 5},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(cli, ["preview", "generate-batch"])
    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "preview.generateBatchPreviews", {}, timeout=300.0
    )


def test_complete_develop_param():
    """タブ補完がパラメータ候補を返す"""
    from cli.completions import complete_develop_param
    completions = complete_develop_param(None, None, "Exp")
    names = [c.value if hasattr(c, "value") else c for c in completions]
    assert "Exposure" in names


def test_complete_develop_param_empty():
    """空文字列で全候補を返す"""
    from cli.completions import complete_develop_param
    completions = complete_develop_param(None, None, "")
    assert len(completions) > 10
