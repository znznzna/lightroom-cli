"""system グループのスキーマ完全性テスト"""

from lightroom_sdk.schema import get_schemas_by_group


class TestSystemSchemaCompleteness:
    def test_system_group_has_4_commands(self):
        schemas = get_schemas_by_group("system")
        assert len(schemas) == 4, f"Expected 4, got {len(schemas)}: {list(schemas.keys())}"

    def test_reconnect_schema_exists(self):
        schemas = get_schemas_by_group("system")
        cli_paths = [s.cli_path for s in schemas.values()]
        assert "system.reconnect" in cli_paths

    def test_check_connection_schema_exists(self):
        schemas = get_schemas_by_group("system")
        cli_paths = [s.cli_path for s in schemas.values()]
        assert "system.check-connection" in cli_paths

    def test_reconnect_is_not_mutating(self):
        schemas = get_schemas_by_group("system")
        reconnect = next(s for s in schemas.values() if s.cli_path == "system.reconnect")
        assert reconnect.mutating is False

    def test_check_connection_has_port_file_param(self):
        schemas = get_schemas_by_group("system")
        check = next(s for s in schemas.values() if s.cli_path == "system.check-connection")
        param_names = [p.name for p in check.params]
        assert "portFile" in param_names
