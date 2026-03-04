from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, validator

class DevelopParameter(BaseModel):
    """Single develop parameter with validation"""
    name: str
    value: float
    min: float
    max: float

    @validator('value')
    def validate_range(cls, v, values):
        if 'min' in values and v < values['min']:
            raise ValueError(f"Value {v} below minimum {values['min']}")
        if 'max' in values and v > values['max']:
            raise ValueError(f"Value {v} above maximum {values['max']}")
        return v

class CurvePoint(BaseModel):
    """Point on a tone curve"""
    x: float = Field(ge=0, le=255)
    y: float = Field(ge=0, le=255)

class PointColorSwatch(BaseModel):
    """PointColors swatch definition"""
    SrcHue: float = Field(ge=0, le=6)
    SrcSat: float = Field(ge=0, le=1)
    SrcLum: float = Field(ge=0, le=1)
    HueShift: float = Field(ge=-1, le=1)
    SatScale: float = Field(ge=-1, le=1)
    LumScale: float = Field(ge=-1, le=1)
    RangeAmount: float = Field(default=1.0, ge=0, le=1)
    HueRange: Dict[str, float]
    SatRange: Dict[str, float]
    LumRange: Dict[str, float]

# Parameter ranges from API_DEVELOP_REFERENCE.md
DEVELOP_PARAMETER_RANGES = {
    # Basic Panel
    "Temperature": (2000, 50000),
    "Tint": (-150, 150),
    "Exposure": (-5, 5),
    "Contrast": (-100, 100),
    "Highlights": (-100, 100),
    "Shadows": (-100, 100),
    "Whites": (-100, 100),
    "Blacks": (-100, 100),
    "Brightness": (-150, 150),
    "Clarity": (-100, 100),
    "Vibrance": (-100, 100),
    "Saturation": (-100, 100),
    "Texture": (-100, 100),
    "Dehaze": (-100, 100),
    
    # Tone Curve
    "ParametricDarks": (-100, 100),
    "ParametricLights": (-100, 100),
    "ParametricShadows": (-100, 100),
    "ParametricHighlights": (-100, 100),
    "ParametricShadowSplit": (0, 100),
    "ParametricMidtoneSplit": (0, 100),
    "ParametricHighlightSplit": (0, 100),
    "CurveRefineSaturation": (-100, 100),
    
    # HSL/Color Adjustments
    "HueAdjustmentRed": (-100, 100),
    "HueAdjustmentOrange": (-100, 100),
    "HueAdjustmentYellow": (-100, 100),
    "HueAdjustmentGreen": (-100, 100),
    "HueAdjustmentAqua": (-100, 100),
    "HueAdjustmentBlue": (-100, 100),
    "HueAdjustmentPurple": (-100, 100),
    "HueAdjustmentMagenta": (-100, 100),
    
    "SaturationAdjustmentRed": (-100, 100),
    "SaturationAdjustmentOrange": (-100, 100),
    "SaturationAdjustmentYellow": (-100, 100),
    "SaturationAdjustmentGreen": (-100, 100),
    "SaturationAdjustmentAqua": (-100, 100),
    "SaturationAdjustmentBlue": (-100, 100),
    "SaturationAdjustmentPurple": (-100, 100),
    "SaturationAdjustmentMagenta": (-100, 100),
    
    "LuminanceAdjustmentRed": (-100, 100),
    "LuminanceAdjustmentOrange": (-100, 100),
    "LuminanceAdjustmentYellow": (-100, 100),
    "LuminanceAdjustmentGreen": (-100, 100),
    "LuminanceAdjustmentAqua": (-100, 100),
    "LuminanceAdjustmentBlue": (-100, 100),
    "LuminanceAdjustmentPurple": (-100, 100),
    "LuminanceAdjustmentMagenta": (-100, 100),
    
    # Detail
    "Sharpness": (0, 150),
    "SharpenRadius": (0.5, 3.0),
    "SharpenDetail": (0, 100),
    "SharpenEdgeMasking": (0, 100),
    "LuminanceSmoothing": (0, 100),
    "LuminanceNoiseReductionDetail": (0, 100),
    "ColorNoiseReduction": (0, 100),
    
    # Lens Corrections
    "LensProfileEnable": (0, 1),
    "AutoLateralCA": (0, 1),
    "PerspectiveVertical": (-100, 100),
    "PerspectiveHorizontal": (-100, 100),
    "PerspectiveRotate": (-10, 10),
    "PerspectiveScale": (50, 150),
    
    # Lens Blur (LR 14.4+)
    "LensBlurActive": (0, 1),
    "LensBlurAmount": (0, 100),
    "LensBlurCatEye": (0, 100),
    "LensBlurHighlightsBoost": (0, 100),
    
    # Effects
    "PostCropVignetteAmount": (-100, 100),
    "GrainAmount": (0, 100),
    "GrainSize": (0, 100),
    "GrainFrequency": (0, 100),
    
    # Calibration
    "ShadowTint": (-100, 100),
    "RedHue": (-100, 100),
    "RedSaturation": (-100, 100),
    "GreenHue": (-100, 100),
    "GreenSaturation": (-100, 100),
    "BlueHue": (-100, 100),
    "BlueSaturation": (-100, 100),
    
    # Split Toning / Color Grading
    "SplitToningShadowHue": (0, 360),
    "SplitToningShadowSaturation": (0, 100),
    "SplitToningHighlightHue": (0, 360),
    "SplitToningHighlightSaturation": (0, 100),
    "SplitToningBalance": (-100, 100),
    "ColorGradeShadowLum": (-100, 100),
    "ColorGradeHighlightLum": (-100, 100),
    "ColorGradeMidtoneHue": (0, 360),
    "ColorGradeGlobalSat": (-100, 100),
    
    # Advanced Detail
    "ColorNoiseReductionDetail": (0, 100),
    
    # Advanced Effects/Vignette
    "PostCropVignetteMidpoint": (0, 100),
    "PostCropVignetteFeather": (0, 100),
    "PostCropVignetteRoundness": (-100, 100),
    "PostCropVignetteStyle": (1, 3),
    "PostCropVignetteHighlightContrast": (0, 100),
    
    # Lens Corrections (Extended)
    "LensProfileDistortionScale": (0, 200),
    "LensProfileVignettingScale": (0, 200),
    "LensManualDistortion": (-100, 100),
    "DefringePurpleAmount": (0, 20),
    "DefringeGreenAmount": (0, 20),
    "VignetteAmount": (-100, 100),
    "VignetteMidpoint": (0, 100),
    "StraightenAngle": (-45, 45),
}