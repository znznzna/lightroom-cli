"""response_fields が充実しているかのテスト"""
from lightroom_sdk.schema import get_all_schemas


def test_no_empty_response_fields_for_read_commands():
    """読み取り専用コマンドには response_fields が設定されている"""
    schemas = get_all_schemas()
    read_commands_without_fields = []
    for name, schema in schemas.items():
        # mutating, debug, reset, internal bridge commands はスキップ
        if schema.mutating:
            continue
        if "debug" in schema.cli_path:
            continue
        if "_bridge" in schema.cli_path:
            continue
        if "toggle" in schema.cli_path:
            continue
        if not schema.response_fields:
            read_commands_without_fields.append(schema.cli_path)

    # 全ての読み取りコマンドに response_fields があるべき
    assert read_commands_without_fields == [], (
        f"Read commands missing response_fields: {read_commands_without_fields}"
    )
