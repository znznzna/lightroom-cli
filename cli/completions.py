from click.shell_completion import CompletionItem

DEVELOP_PARAMETER_RANGES = {
    "Exposure": (-5.0, 5.0),
    "Contrast": (-100, 100),
    "Highlights": (-100, 100),
    "Shadows": (-100, 100),
    "Whites": (-100, 100),
    "Blacks": (-100, 100),
    "Clarity": (-100, 100),
    "Dehaze": (-100, 100),
    "Vibrance": (-100, 100),
    "Saturation": (-100, 100),
    "Temperature": (2000, 50000),
    "Tint": (-150, 150),
    "Texture": (-100, 100),
    "Sharpness": (0, 150),
    "LuminanceSmoothing": (0, 100),
    "ColorNoiseReduction": (0, 100),
    "PostCropVignetteAmount": (-100, 100),
    "GrainAmount": (0, 100),
    "ShadowTint": (-100, 100),
    "ParametricShadows": (-100, 100),
    "ParametricDarks": (-100, 100),
    "ParametricLights": (-100, 100),
    "ParametricHighlights": (-100, 100),
}


def complete_develop_param(ctx, param, incomplete: str) -> list:
    """develop set コマンド用のタブ補完"""
    return [
        CompletionItem(name) for name in DEVELOP_PARAMETER_RANGES.keys() if name.lower().startswith(incomplete.lower())
    ]
