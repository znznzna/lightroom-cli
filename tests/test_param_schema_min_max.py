"""ParamSchema min/max フィールドのテスト"""

from lightroom_sdk.schema import get_schema


def test_rating_param_has_min_max():
    """catalog.setRating の rating パラメータに min=0, max=5 がある"""
    schema = get_schema("catalog.setRating")
    rating_param = next(p for p in schema.params if p.name == "rating")
    assert rating_param.min == 0
    assert rating_param.max == 5


def test_selection_rating_has_min_max():
    """selection.setRating の rating パラメータに min=0, max=5 がある"""
    schema = get_schema("selection.setRating")
    rating_param = next(p for p in schema.params if p.name == "rating")
    assert rating_param.min == 0
    assert rating_param.max == 5


def test_param_without_min_max():
    """min/max 未指定のパラメータは None"""
    schema = get_schema("catalog.getPhotoMetadata")
    photo_id_param = next(p for p in schema.params if p.name == "photoId")
    assert photo_id_param.min is None
    assert photo_id_param.max is None
