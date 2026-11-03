"""CLI と MCP でバリデーション結果が一致することを確認。"""

import pytest

from lightroom_sdk.validation import ValidationError, validate_params


class TestValidationEquivalence:
    """CLI と MCP は同一の validate_params を使うため、結果は同一であること。"""

    def test_valid_params_pass(self):
        """正常パラメータが通ること"""
        result = validate_params("catalog.setRating", {"photoId": "1", "rating": 3})
        assert result["photoId"] == "1"
        assert result["rating"] == 3

    def test_unknown_param_raises(self):
        """不明パラメータでエラー"""
        with pytest.raises(ValidationError) as exc_info:
            validate_params("catalog.setRating", {"photoId": "1", "rating": 3, "bad": "x"})
        assert "bad" in str(exc_info.value)

    def test_missing_required_raises(self):
        """必須パラメータ欠落でエラー"""
        with pytest.raises(ValidationError):
            validate_params("catalog.setRating", {"photoId": "1"})

    def test_type_coercion(self):
        """文字列 -> 数値の型変換"""
        result = validate_params("catalog.setRating", {"photoId": "1", "rating": "3"})
        assert result["rating"] == 3

    def test_range_validation(self):
        """範囲外でエラー"""
        with pytest.raises(ValidationError):
            validate_params("catalog.setRating", {"photoId": "1", "rating": 10})

    def test_enum_validation(self):
        """ENUM のバリデーション"""
        result = validate_params("catalog.setColorLabel", {"photoId": "1", "label": "red"})
        assert result["label"] == "red"

        with pytest.raises(ValidationError):
            validate_params("catalog.setColorLabel", {"photoId": "1", "label": "orange"})

    def test_unknown_command_passes_through(self):
        """スキーマ未定義のコマンドはバリデーションスキップ"""
        result = validate_params("unknown.command", {"any": "param"})
        assert result == {"any": "param"}


def _cli(args: list[str]):
    """Run the real CLI entry point (it owns its event loop, so call it from a worker thread)"""
    from click.testing import CliRunner

    from cli.main import cli

    return CliRunner().invoke(cli, ["-o", "json", *args])


def _cli_error(result) -> dict:
    import json

    lines = [line for line in (result.stderr or result.output).splitlines() if line.strip().startswith("{")]
    assert lines, f"no JSON error in CLI output: {result.output!r}"
    return json.loads(lines[-1])


class TestSameInputSameOutcome:
    """The same parameters through the CLI and through MCP give the same result (codex-tests #11).

    Replaces a check that both imported the same validate_params: that stayed green even if an
    entry point stopped calling it.
    """

    @pytest.mark.parametrize(
        "command, cli_path, params",
        [
            ("catalog.setRating", ["catalog", "set-rating", "1", "0"], {"photoId": "1", "rating": 10}),
            ("catalog.setRating", ["catalog", "set-rating", "1", "0"], {"photoId": "1"}),
            ("catalog.setRating", ["catalog", "set-rating", "1", "0"], {"photoId": "1", "rating": 3, "bad": "x"}),
            ("catalog.setColorLabel", ["catalog", "set-color-label", "1", "red"], {"photoId": "1", "label": "orange"}),
        ],
        ids=["out-of-range", "missing-required", "unknown-param", "bad-enum"],
    )
    async def test_invalid_input_is_rejected_the_same_way(self, command, cli_path, params, tmp_path, monkeypatch):
        import asyncio
        import json

        from mcp_server.connection import ConnectionManager

        # Neither entry point may get as far as connecting: no Lightroom is listening here
        monkeypatch.setenv("LR_PORT_FILE", str(tmp_path / "no-lightroom.txt"))
        cli_result = await asyncio.to_thread(_cli, [*cli_path, "--json", json.dumps(params)])
        mcp_result = await ConnectionManager(port_file=str(tmp_path / "no-lightroom.txt")).execute(
            command, params, timeout=5, mutating=True
        )

        assert cli_result.exit_code == 2
        cli_error = _cli_error(cli_result)["error"]
        assert cli_error["code"] == mcp_result["code"] == "VALIDATION_ERROR"
        assert cli_error["message"] == mcp_result["message"]

    async def test_valid_input_reaches_lightroom_identically(self, mock_lr_server, monkeypatch):
        """Including the coercion of "3" to 3: both send exactly the same params"""
        import asyncio
        import json

        from mcp_server.connection import ConnectionManager

        mock_lr_server.register_response("catalog.setRating", {"ok": True})
        monkeypatch.setenv("LR_PORT_FILE", str(mock_lr_server.port_file))
        params = {"photoId": "1", "rating": "3"}

        cli_result = await asyncio.to_thread(_cli, ["catalog", "set-rating", "1", "0", "--json", json.dumps(params)])
        assert cli_result.exit_code == 0, cli_result.output
        manager = ConnectionManager(port_file=str(mock_lr_server.port_file))
        try:
            mcp_result = await manager.execute("catalog.setRating", params, timeout=5, mutating=True)
        finally:
            await manager.shutdown()

        assert mcp_result == {"result": {"ok": True}}
        sent = [r["params"] for r in mock_lr_server.requests if r["command"] == "catalog.setRating"]
        assert sent == [{"photoId": "1", "rating": 3}, {"photoId": "1", "rating": 3}]
