"""catalog.getCollectionPhotos / catalog.getDevelopPresets のテスト"""

from click.testing import CliRunner

from cli.main import cli
from lightroom_sdk.schema import COMMAND_SCHEMAS


class TestGetCollectionPhotosSchema:
    """getCollectionPhotos スキーマテスト"""

    def test_schema_exists(self):
        assert "catalog.getCollectionPhotos" in COMMAND_SCHEMAS

    def test_schema_has_required_collection_id(self):
        schema = COMMAND_SCHEMAS["catalog.getCollectionPhotos"]
        param_names = {p.name for p in schema.params}
        assert "collectionId" in param_names
        cid_param = next(p for p in schema.params if p.name == "collectionId")
        assert cid_param.required is True

    def test_schema_has_pagination_params(self):
        schema = COMMAND_SCHEMAS["catalog.getCollectionPhotos"]
        param_names = {p.name for p in schema.params}
        assert "limit" in param_names
        assert "offset" in param_names

    def test_schema_timeout(self):
        schema = COMMAND_SCHEMAS["catalog.getCollectionPhotos"]
        assert schema.timeout == 60.0

    def test_schema_response_fields(self):
        schema = COMMAND_SCHEMAS["catalog.getCollectionPhotos"]
        assert "photos" in schema.response_fields
        assert "total" in schema.response_fields

    def test_schema_is_read_only(self):
        schema = COMMAND_SCHEMAS["catalog.getCollectionPhotos"]
        assert schema.mutating is False
        assert schema.risk_level == "read"


class TestGetDevelopPresetsSchema:
    """getDevelopPresets スキーマテスト"""

    def test_schema_exists(self):
        assert "catalog.getDevelopPresets" in COMMAND_SCHEMAS

    def test_schema_has_optional_query(self):
        schema = COMMAND_SCHEMAS["catalog.getDevelopPresets"]
        param_names = {p.name for p in schema.params}
        assert "query" in param_names
        q_param = next(p for p in schema.params if p.name == "query")
        assert q_param.required is False

    def test_schema_response_fields(self):
        schema = COMMAND_SCHEMAS["catalog.getDevelopPresets"]
        assert "presets" in schema.response_fields
        assert "count" in schema.response_fields

    def test_schema_is_read_only(self):
        schema = COMMAND_SCHEMAS["catalog.getDevelopPresets"]
        assert schema.mutating is False


class TestCollectionPhotosCLI:
    """collection-photos CLI コマンドテスト"""

    def test_cli_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["catalog", "collection-photos", "--help"])
        assert result.exit_code == 0
        assert "collection" in result.output.lower()

    def test_cli_requires_collection_id(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["catalog", "collection-photos"])
        assert result.exit_code != 0

    def test_cli_rejects_non_integer_id(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["catalog", "collection-photos", "abc"])
        assert result.exit_code != 0


class TestDevelopPresetsCLI:
    """develop-presets CLI コマンドテスト"""

    def test_cli_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["catalog", "develop-presets", "--help"])
        assert result.exit_code == 0
        assert "preset" in result.output.lower()

    def test_cli_no_args_is_valid(self):
        """引数なしでも実行可能（全プリセット一覧）"""
        runner = CliRunner()
        # Connection error expected, but no argument validation error
        result = runner.invoke(cli, ["catalog", "develop-presets", "--output", "json"])
        # Should fail due to connection, not argument validation
        assert "Missing" not in (result.output or "")
