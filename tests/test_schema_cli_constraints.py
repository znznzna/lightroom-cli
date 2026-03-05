"""Tests for cli_constraints fields on CommandSchema."""

from lightroom_sdk.schema import get_all_schemas, get_schema


class TestCliConstraints:
    def test_read_command_risk_level(self):
        schema = get_schema("develop.getSettings")
        assert schema.risk_level == "read"
        assert schema.supports_dry_run is False
        assert schema.requires_confirm is False

    def test_write_command_risk_level(self):
        schema = get_schema("develop.setValue")
        assert schema.risk_level == "write"
        assert schema.supports_dry_run is True

    def test_destructive_command_risk_level(self):
        schema = get_schema("catalog.removeFromCatalog")
        assert schema.risk_level == "destructive"
        assert schema.requires_confirm is True
        assert schema.supports_dry_run is True

    def test_ai_reset_requires_confirm(self):
        schema = get_schema("develop.ai.reset")
        assert schema.requires_confirm is True
        assert schema.risk_level == "destructive"

    def test_all_mutating_with_dry_run_are_marked(self):
        """全ての mutating=True かつ dry-run対応コマンドが supports_dry_run=True"""
        all_schemas = get_all_schemas()
        for name, s in all_schemas.items():
            if s.mutating and s.supports_dry_run:
                assert s.risk_level in ("write", "destructive"), f"{name} has wrong risk_level"

    def test_non_mutating_never_supports_dry_run(self):
        """読み取り専用コマンドは supports_dry_run=False"""
        all_schemas = get_all_schemas()
        for name, s in all_schemas.items():
            if not s.mutating:
                assert not s.supports_dry_run, f"{name} is read-only but supports_dry_run=True"
