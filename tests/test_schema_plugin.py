"""plugin グループが schema introspection に現れるかのテスト"""
from lightroom_sdk.schema import get_schema, get_schemas_by_group


def test_plugin_schemas_registered():
    """plugin.install, plugin.uninstall, plugin.status がスキーマに存在する"""
    assert get_schema("plugin.install") is not None
    assert get_schema("plugin.uninstall") is not None
    assert get_schema("plugin.status") is not None


def test_plugin_group_lookup():
    """get_schemas_by_group('plugin') で全 plugin コマンドが返る"""
    group = get_schemas_by_group("plugin")
    assert len(group) == 3
    cli_paths = {s.cli_path for s in group.values()}
    assert cli_paths == {"plugin.install", "plugin.uninstall", "plugin.status"}


def test_plugin_install_has_dev_param():
    """plugin.install に dev パラメータがある"""
    schema = get_schema("plugin.install")
    param_names = [p.name for p in schema.params]
    assert "dev" in param_names


def test_plugin_status_response_fields():
    """plugin.status に response_fields がある"""
    schema = get_schema("plugin.status")
    assert "source" in schema.response_fields
    assert "status" in schema.response_fields
