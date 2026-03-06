"""instructions のテスト。"""


def test_instructions_is_non_empty_string():
    from mcp_server.instructions import INSTRUCTIONS

    assert isinstance(INSTRUCTIONS, str)
    assert len(INSTRUCTIONS) > 100


def test_instructions_contains_ping():
    """接続確認フローが含まれること"""
    from mcp_server.instructions import INSTRUCTIONS

    assert "lr_system_ping" in INSTRUCTIONS


def test_instructions_contains_error_recovery():
    """エラー回復パターンが含まれること"""
    from mcp_server.instructions import INSTRUCTIONS

    assert "CONNECTION_ERROR" in INSTRUCTIONS


def test_instructions_contains_workflow():
    """主要ワークフローが含まれること"""
    from mcp_server.instructions import INSTRUCTIONS

    assert "lr_catalog" in INSTRUCTIONS
    assert "lr_develop" in INSTRUCTIONS


def test_instructions_mentions_lr_prefix():
    """ツール名が lr_ prefix であることが記載されていること"""
    from mcp_server.instructions import INSTRUCTIONS

    assert "lr_" in INSTRUCTIONS


def test_instructions_mentions_dry_run():
    """dry_run の説明が含まれること"""
    from mcp_server.instructions import INSTRUCTIONS

    assert "dry_run" in INSTRUCTIONS
