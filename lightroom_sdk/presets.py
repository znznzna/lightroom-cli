"""AI Mask adjustment presets."""

from typing import Dict, Optional

AI_MASK_PRESETS: Dict[str, Dict[str, float]] = {
    "darken-sky": {"Exposure": -0.7, "Highlights": -30, "Saturation": 15},
    "brighten-subject": {"Exposure": 0.5, "Shadows": 20, "Clarity": 10},
    "blur-background": {"Sharpness": -80, "Clarity": -40},
    "warm-skin": {"Temp": 500, "Tint": 5, "Saturation": -10},
    "enhance-landscape": {"Clarity": 30, "Vibrance": 25, "Dehaze": 15},
}


def get_preset(name: str) -> Optional[Dict[str, float]]:
    """プリセット名から調整パラメータのコピーを返す。存在しなければ None。"""
    preset = AI_MASK_PRESETS.get(name)
    if preset is None:
        return None
    return dict(preset)


def list_presets() -> list[str]:
    """利用可能なプリセット名の一覧を返す。"""
    return list(AI_MASK_PRESETS.keys())
