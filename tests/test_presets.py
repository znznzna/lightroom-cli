# tests/test_presets.py
from lightroom_sdk.presets import AI_MASK_PRESETS, get_preset, list_presets


def test_ai_mask_presets_has_five_entries():
    assert len(AI_MASK_PRESETS) == 5


def test_darken_sky_preset_keys():
    preset = AI_MASK_PRESETS["darken-sky"]
    assert preset == {"Exposure": -0.7, "Highlights": -30, "Saturation": 15}


def test_brighten_subject_preset():
    preset = AI_MASK_PRESETS["brighten-subject"]
    assert preset == {"Exposure": 0.5, "Shadows": 20, "Clarity": 10}


def test_blur_background_preset():
    preset = AI_MASK_PRESETS["blur-background"]
    assert preset == {"Sharpness": -80, "Clarity": -40}


def test_warm_skin_preset():
    preset = AI_MASK_PRESETS["warm-skin"]
    assert preset == {"Temp": 500, "Tint": 5, "Saturation": -10}


def test_enhance_landscape_preset():
    preset = AI_MASK_PRESETS["enhance-landscape"]
    assert preset == {"Clarity": 30, "Vibrance": 25, "Dehaze": 15}


def test_get_preset_returns_copy():
    """get_preset は元データを変更されないようコピーを返す"""
    preset = get_preset("darken-sky")
    preset["Exposure"] = 999
    assert AI_MASK_PRESETS["darken-sky"]["Exposure"] == -0.7


def test_get_preset_unknown_returns_none():
    assert get_preset("nonexistent") is None


def test_list_presets_returns_all_names():
    names = list_presets()
    assert set(names) == {
        "darken-sky",
        "brighten-subject",
        "blur-background",
        "warm-skin",
        "enhance-landscape",
    }
