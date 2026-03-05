"""Command schema definitions -- Single Source of Truth for validation and introspection."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class ParamType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON_OBJECT = "json_object"
    JSON_ARRAY = "json_array"
    ENUM = "enum"


@dataclass
class ParamSchema:
    name: str
    type: ParamType
    required: bool = False
    description: str = ""
    default: object = None
    enum_values: list[str] | None = None


@dataclass
class CommandSchema:
    command: str
    cli_path: str
    description: str
    params: list[ParamSchema] = field(default_factory=list)
    mutating: bool = False
    timeout: float = 30.0
    response_fields: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# スキーマ定義
# ---------------------------------------------------------------------------

COMMAND_SCHEMAS: dict[str, CommandSchema] = {}


def _register(*schemas: CommandSchema) -> None:
    for s in schemas:
        COMMAND_SCHEMAS[s.command] = s


# --- system ---
_register(
    CommandSchema("system.ping", "system.ping", "Test connection", timeout=5.0),
    CommandSchema("system.status", "system.status", "Get bridge status", timeout=5.0),
)

# --- develop (主要) ---
_register(
    CommandSchema(
        "develop.getSettings", "develop.get-settings",
        "Get all current develop settings",
        response_fields=["Exposure", "Contrast", "Highlights", "Shadows",
                         "Whites", "Blacks", "Temperature", "Tint"],
    ),
    CommandSchema(
        "develop.setValue", "develop.set",
        "Set develop parameter(s)",
        params=[
            ParamSchema("parameter", ParamType.STRING, required=True,
                        description="Develop parameter name (e.g., Exposure, Contrast)"),
            ParamSchema("value", ParamType.FLOAT, required=True,
                        description="Parameter value"),
        ],
        mutating=True, timeout=10.0,
    ),
    CommandSchema(
        "develop.getValue", "develop.get",
        "Get a single develop parameter value",
        params=[
            ParamSchema("param", ParamType.STRING, required=True,
                        description="Parameter name"),
        ],
    ),
    CommandSchema(
        "develop.applySettings", "develop.apply",
        "Apply develop settings from JSON",
        params=[
            ParamSchema("settings", ParamType.JSON_OBJECT, required=True,
                        description="JSON object of settings to apply"),
        ],
        mutating=True,
    ),
    CommandSchema(
        "develop.batchApplySettings", "develop.batch-apply",
        "Batch apply develop settings (used internally by develop set with multiple pairs)",
        params=[
            ParamSchema("settings", ParamType.JSON_OBJECT, required=True,
                        description="JSON object of settings to apply"),
        ],
        mutating=True,
    ),
    CommandSchema(
        "develop.setAutoTone", "develop.auto-tone",
        "Apply auto tone adjustments",
        mutating=True,
    ),
    CommandSchema(
        "develop.setAutoWhiteBalance", "develop.auto-wb",
        "Apply auto white balance",
        mutating=True,
    ),
    CommandSchema(
        "develop.selectTool", "develop.tool",
        "Select a develop tool",
        params=[
            ParamSchema("tool", ParamType.ENUM, required=True,
                        description="Tool name",
                        enum_values=["loupe", "crop", "dust", "redeye",
                                     "gradient", "circularGradient",
                                     "localized", "upright"]),
        ],
    ),
    CommandSchema(
        "develop.resetAllDevelopAdjustments", "develop.reset",
        "Reset develop settings to defaults",
        mutating=True,
    ),
    CommandSchema(
        "develop.getRange", "develop.range",
        "Get min/max range for a develop parameter",
        params=[
            ParamSchema("param", ParamType.STRING, required=True,
                        description="Parameter name"),
        ],
    ),
    CommandSchema(
        "develop.resetToDefault", "develop.reset-param",
        "Reset a develop parameter to its default value",
        params=[
            ParamSchema("param", ParamType.STRING, required=True),
        ],
        mutating=True,
    ),
    CommandSchema(
        "develop.getProcessVersion", "develop.process-version",
        "Get the current process version",
    ),
    CommandSchema(
        "develop.setProcessVersion", "develop.set-process-version",
        "Set the process version",
        params=[
            ParamSchema("version", ParamType.STRING, required=True),
        ],
        mutating=True,
    ),
)

# --- develop.curve ---
_register(
    CommandSchema(
        "develop.getCurvePoints", "develop.curve.get",
        "Get tone curve points",
        params=[
            ParamSchema("param", ParamType.STRING, required=True,
                        description="Curve parameter name"),
        ],
    ),
    CommandSchema(
        "develop.setCurvePoints", "develop.curve.set",
        "Set tone curve points",
        params=[
            ParamSchema("param", ParamType.STRING, required=True),
            ParamSchema("points", ParamType.JSON_ARRAY, required=True,
                        description="Array of {x, y} points"),
        ],
        mutating=True,
    ),
    CommandSchema(
        "develop.setCurveLinear", "develop.curve.linear",
        "Reset curve to linear",
        params=[ParamSchema("param", ParamType.STRING, required=True)],
        mutating=True,
    ),
    CommandSchema(
        "develop.setCurveSCurve", "develop.curve.s-curve",
        "Apply S-curve preset",
        params=[ParamSchema("param", ParamType.STRING, required=True)],
        mutating=True,
    ),
    CommandSchema(
        "develop.addCurvePoint", "develop.curve.add-point",
        "Add a point to the tone curve",
        params=[
            ParamSchema("param", ParamType.STRING, required=True),
            ParamSchema("x", ParamType.FLOAT, required=True),
            ParamSchema("y", ParamType.FLOAT, required=True),
        ],
        mutating=True,
    ),
    CommandSchema(
        "develop.removeCurvePoint", "develop.curve.remove-point",
        "Remove a point from the tone curve",
        params=[
            ParamSchema("param", ParamType.STRING, required=True),
            ParamSchema("index", ParamType.INTEGER, required=True),
        ],
        mutating=True,
    ),
)

# --- develop.mask ---
_register(
    CommandSchema("develop.getAllMasks", "develop.mask.list", "List all masks"),
    CommandSchema("develop.getSelectedMask", "develop.mask.selected", "Get selected mask"),
    CommandSchema("develop.goToMasking", "develop.mask.go-to", "Go to masking view"),
    CommandSchema("develop.toggleOverlay", "develop.mask.toggle-overlay", "Toggle mask overlay"),
)

# --- develop.local ---
_register(
    CommandSchema(
        "develop.getLocalValue", "develop.local.get",
        "Get a local adjustment parameter value",
        params=[ParamSchema("parameter", ParamType.STRING, required=True)],
    ),
    CommandSchema(
        "develop.setLocalValue", "develop.local.set",
        "Set a local adjustment parameter value",
        params=[
            ParamSchema("parameter", ParamType.STRING, required=True),
            ParamSchema("value", ParamType.FLOAT, required=True),
        ],
        mutating=True,
    ),
    CommandSchema(
        "develop.applyLocalSettings", "develop.local.apply",
        "Apply multiple local adjustment settings",
        params=[
            ParamSchema("settings", ParamType.JSON_OBJECT, required=True),
        ],
        mutating=True,
    ),
    CommandSchema(
        "develop.getAvailableLocalParameters", "develop.local.params",
        "List available local adjustment parameters",
    ),
    CommandSchema(
        "develop.createMaskWithLocalAdjustments", "develop.local.create-mask",
        "Create mask with local adjustments",
        params=[
            ParamSchema("maskType", ParamType.ENUM,
                        enum_values=["brush", "gradient", "radial"]),
            ParamSchema("localSettings", ParamType.JSON_OBJECT),
        ],
        mutating=True,
    ),
)

# --- develop.filter ---
_register(
    CommandSchema("develop.createGraduatedFilter", "develop.filter.graduated",
                  "Create a graduated filter", mutating=True),
    CommandSchema("develop.createRadialFilter", "develop.filter.radial",
                  "Create a radial filter", mutating=True),
    CommandSchema("develop.createAdjustmentBrush", "develop.filter.brush",
                  "Create an adjustment brush", mutating=True),
    CommandSchema(
        "develop.createRangeMask", "develop.filter.range",
        "Create a range mask",
        params=[
            ParamSchema("rangeType", ParamType.ENUM,
                        enum_values=["luminance", "color", "depth"]),
        ],
        mutating=True,
    ),
)

# --- develop reset commands ---
_register(
    CommandSchema("develop.resetGradient", "develop.reset-gradient",
                  "Reset gradient filter", mutating=True),
    CommandSchema("develop.resetCircularGradient", "develop.reset-circular",
                  "Reset circular gradient filter", mutating=True),
    CommandSchema("develop.resetBrushing", "develop.reset-brush",
                  "Reset adjustment brush", mutating=True),
    CommandSchema("develop.resetMasking", "develop.reset-masking",
                  "Reset masking", mutating=True),
    CommandSchema("develop.resetCrop", "develop.reset-crop",
                  "Reset crop", mutating=True),
    CommandSchema("develop.resetTransforms", "develop.reset-transforms",
                  "Reset transforms", mutating=True),
    CommandSchema("develop.resetSpotRemoval", "develop.reset-spot",
                  "Reset spot removal", mutating=True),
    CommandSchema("develop.resetRedeye", "develop.reset-redeye",
                  "Reset red eye removal", mutating=True),
    CommandSchema("develop.resetHealing", "develop.reset-healing",
                  "Reset healing", mutating=True),
)

# --- develop other ---
_register(
    CommandSchema("develop.editInPhotoshop", "develop.edit-in-photoshop",
                  "Open current photo in Photoshop", mutating=True),
    CommandSchema("catalog.applyDevelopPreset", "develop.preset",
                  "Apply a develop preset by name",
                  params=[ParamSchema("presetName", ParamType.STRING, required=True)],
                  mutating=True),
    CommandSchema("catalog.createDevelopSnapshot", "develop.snapshot",
                  "Create a develop snapshot",
                  params=[ParamSchema("name", ParamType.STRING, required=True)],
                  mutating=True),
    CommandSchema("catalog.copySettings", "develop.copy-settings",
                  "Copy develop settings from selected photo"),
    CommandSchema("catalog.pasteSettings", "develop.paste-settings",
                  "Paste develop settings to selected photo", mutating=True),
)

# --- develop.debug ---
_register(
    CommandSchema("develop.dumpLrDevelopController", "develop.debug.dump",
                  "Dump LrDevelopController info"),
    CommandSchema("develop.discoverGradientParameters", "develop.debug.gradient-params",
                  "Discover gradient parameters"),
    CommandSchema("develop.monitorParameterChanges", "develop.debug.monitor",
                  "Monitor parameter changes",
                  params=[ParamSchema("duration", ParamType.INTEGER, default=10)]),
    CommandSchema("develop.probeAllDevelopParameters", "develop.debug.probe",
                  "Probe all develop parameters"),
)

# --- develop.color ---
_register(
    CommandSchema("develop.createGreenSwatch", "develop.color.green-swatch",
                  "Create green color swatch", mutating=True),
    CommandSchema("develop.createCyanSwatch", "develop.color.cyan-swatch",
                  "Create cyan color swatch", mutating=True),
    CommandSchema("develop.enhanceColors", "develop.color.enhance",
                  "Enhance colors",
                  params=[ParamSchema("preset", ParamType.ENUM,
                                      enum_values=["natural", "vivid", "muted"])],
                  mutating=True),
)

# --- develop.ai ---
_register(
    CommandSchema(
        "develop.createAIMaskWithAdjustments", "develop.ai.<type>",
        "Create AI mask with optional adjustments",
        params=[
            ParamSchema("selectionType", ParamType.ENUM, required=True,
                        enum_values=["subject", "sky", "background",
                                     "objects", "people", "landscape"]),
            ParamSchema("adjustments", ParamType.JSON_OBJECT,
                        description="Optional adjustment settings"),
        ],
        mutating=True, timeout=60.0,
    ),
    CommandSchema(
        "develop.batchAIMask", "develop.ai.batch",
        "Apply AI mask to multiple photos",
        params=[
            ParamSchema("selectionType", ParamType.ENUM, required=True,
                        enum_values=["subject", "sky", "background",
                                     "objects", "people", "landscape"]),
            ParamSchema("photoIds", ParamType.JSON_ARRAY),
            ParamSchema("allSelected", ParamType.BOOLEAN, default=False),
            ParamSchema("adjustments", ParamType.JSON_OBJECT),
            ParamSchema("continueOnError", ParamType.BOOLEAN, default=False),
        ],
        mutating=True, timeout=300.0,
    ),
)

# --- catalog ---
_register(
    CommandSchema("catalog.getSelectedPhotos", "catalog.get-selected",
                  "Get currently selected photos"),
    CommandSchema(
        "catalog.getAllPhotos", "catalog.list",
        "List photos in catalog",
        params=[
            ParamSchema("limit", ParamType.INTEGER, default=50),
            ParamSchema("offset", ParamType.INTEGER, default=0),
        ],
        timeout=60.0,
    ),
    CommandSchema(
        "catalog.searchPhotos", "catalog.search",
        "Search photos by keyword",
        params=[
            ParamSchema("query", ParamType.STRING, required=True),
            ParamSchema("limit", ParamType.INTEGER, default=50),
        ],
        timeout=60.0,
    ),
    CommandSchema(
        "catalog.getPhotoMetadata", "catalog.get-info",
        "Get detailed info for a photo",
        params=[ParamSchema("photoId", ParamType.STRING, required=True)],
    ),
    CommandSchema(
        "catalog.setRating", "catalog.set-rating",
        "Set photo star rating",
        params=[
            ParamSchema("photoId", ParamType.STRING, required=True),
            ParamSchema("rating", ParamType.INTEGER, required=True,
                        description="Star rating (0-5)"),
        ],
        mutating=True,
    ),
    CommandSchema(
        "catalog.addKeywords", "catalog.add-keywords",
        "Add keywords to a photo",
        params=[
            ParamSchema("photoId", ParamType.STRING, required=True),
            ParamSchema("keywords", ParamType.JSON_ARRAY, required=True),
        ],
        mutating=True,
    ),
    CommandSchema(
        "catalog.setFlag", "catalog.set-flag",
        "Set photo flag (pick/reject/none)",
        params=[
            ParamSchema("photoId", ParamType.STRING, required=True),
            ParamSchema("flag", ParamType.INTEGER, required=True,
                        description="Flag value (1=pick, -1=reject, 0=none)"),
        ],
        mutating=True,
    ),
    CommandSchema(
        "catalog.getFlag", "catalog.get-flag",
        "Get photo flag status",
        params=[ParamSchema("photoId", ParamType.STRING, required=True)],
    ),
    CommandSchema(
        "catalog.findPhotos", "catalog.find",
        "Find photos by structured criteria",
        params=[
            ParamSchema("searchDesc", ParamType.JSON_OBJECT, required=True),
            ParamSchema("limit", ParamType.INTEGER, default=50),
            ParamSchema("offset", ParamType.INTEGER, default=0),
        ],
    ),
    CommandSchema(
        "catalog.setSelectedPhotos", "catalog.select",
        "Select photos by ID",
        params=[
            ParamSchema("photoIds", ParamType.JSON_ARRAY, required=True),
        ],
        mutating=True,
    ),
    CommandSchema(
        "catalog.findPhotoByPath", "catalog.find-by-path",
        "Find photo by file path",
        params=[ParamSchema("path", ParamType.STRING, required=True)],
    ),
    CommandSchema("catalog.getCollections", "catalog.collections",
                  "List collections in catalog"),
    CommandSchema("catalog.getKeywords", "catalog.keywords",
                  "List keywords in catalog"),
    CommandSchema(
        "catalog.getFolders", "catalog.folders",
        "List folders in catalog",
        params=[ParamSchema("includeSubfolders", ParamType.BOOLEAN, default=False)],
    ),
    CommandSchema(
        "catalog.setTitle", "catalog.set-title",
        "Set photo title",
        params=[
            ParamSchema("photoId", ParamType.STRING, required=True),
            ParamSchema("title", ParamType.STRING, required=True),
        ],
        mutating=True,
    ),
    CommandSchema(
        "catalog.setCaption", "catalog.set-caption",
        "Set photo caption",
        params=[
            ParamSchema("photoId", ParamType.STRING, required=True),
            ParamSchema("caption", ParamType.STRING, required=True),
        ],
        mutating=True,
    ),
    CommandSchema(
        "catalog.setColorLabel", "catalog.set-color-label",
        "Set photo color label",
        params=[
            ParamSchema("photoId", ParamType.STRING, required=True),
            ParamSchema("label", ParamType.ENUM, required=True,
                        enum_values=["red", "yellow", "green", "blue", "purple", "none"]),
        ],
        mutating=True,
    ),
    CommandSchema(
        "catalog.batchGetFormattedMetadata", "catalog.batch-metadata",
        "Get formatted metadata for multiple photos",
        params=[
            ParamSchema("photoIds", ParamType.JSON_ARRAY, required=True),
            ParamSchema("keys", ParamType.JSON_ARRAY, required=True),
        ],
    ),
    CommandSchema("catalog.rotateLeft", "catalog.rotate-left",
                  "Rotate selected photo left", mutating=True),
    CommandSchema("catalog.rotateRight", "catalog.rotate-right",
                  "Rotate selected photo right", mutating=True),
    CommandSchema("catalog.createVirtualCopy", "catalog.create-virtual-copy",
                  "Create virtual copy of selected photo", mutating=True),
    CommandSchema(
        "catalog.setMetadata", "catalog.set-metadata",
        "Set arbitrary metadata key/value",
        params=[
            ParamSchema("photoId", ParamType.STRING, required=True),
            ParamSchema("key", ParamType.STRING, required=True),
            ParamSchema("value", ParamType.STRING, required=True),
        ],
        mutating=True,
    ),
    CommandSchema(
        "catalog.createCollection", "catalog.create-collection",
        "Create a new collection",
        params=[ParamSchema("name", ParamType.STRING, required=True)],
        mutating=True,
    ),
    CommandSchema(
        "catalog.createSmartCollection", "catalog.create-smart-collection",
        "Create a smart collection",
        params=[
            ParamSchema("name", ParamType.STRING, required=True),
            ParamSchema("searchDesc", ParamType.JSON_OBJECT),
        ],
        mutating=True,
    ),
    CommandSchema(
        "catalog.createCollectionSet", "catalog.create-collection-set",
        "Create a collection set",
        params=[ParamSchema("name", ParamType.STRING, required=True)],
        mutating=True,
    ),
    CommandSchema(
        "catalog.createKeyword", "catalog.create-keyword",
        "Create a keyword in catalog",
        params=[ParamSchema("keyword", ParamType.STRING, required=True)],
        mutating=True,
    ),
    CommandSchema(
        "catalog.removeKeyword", "catalog.remove-keyword",
        "Remove keyword from a photo",
        params=[
            ParamSchema("photoId", ParamType.STRING, required=True),
            ParamSchema("keyword", ParamType.STRING, required=True),
        ],
        mutating=True,
    ),
    CommandSchema(
        "catalog.setViewFilter", "catalog.set-view-filter",
        "Set view filter",
        params=[ParamSchema("filter", ParamType.JSON_OBJECT, required=True)],
        mutating=True,
    ),
    CommandSchema("catalog.getCurrentViewFilter", "catalog.get-view-filter",
                  "Get current view filter"),
    CommandSchema(
        "catalog.removeFromCatalog", "catalog.remove-from-catalog",
        "Remove photo from catalog",
        params=[ParamSchema("photoId", ParamType.STRING, required=True)],
        mutating=True,
    ),
)

# --- selection ---
_register(
    CommandSchema("selection.flagAsPick", "selection.flag",
                  "Flag selected photo(s) as Pick", mutating=True),
    CommandSchema("selection.flagAsReject", "selection.reject",
                  "Flag selected photo(s) as Reject", mutating=True),
    CommandSchema("selection.removeFlag", "selection.unflag",
                  "Remove flag from selected photo(s)", mutating=True),
    CommandSchema("selection.nextPhoto", "selection.next",
                  "Move to next photo"),
    CommandSchema("selection.previousPhoto", "selection.previous",
                  "Move to previous photo"),
    CommandSchema(
        "selection.setColorLabel", "selection.color-label",
        "Set color label for selected photo(s)",
        params=[
            ParamSchema("label", ParamType.ENUM, required=True,
                        enum_values=["red", "yellow", "green", "blue", "purple", "none"]),
        ],
        mutating=True,
    ),
    CommandSchema("selection.selectAll", "selection.select-all",
                  "Select all photos", mutating=True),
    CommandSchema("selection.selectNone", "selection.select-none",
                  "Deselect all photos", mutating=True),
    CommandSchema("selection.selectInverse", "selection.select-inverse",
                  "Invert the current selection", mutating=True),
    CommandSchema("selection.increaseRating", "selection.increase-rating",
                  "Increase rating by 1", mutating=True),
    CommandSchema("selection.decreaseRating", "selection.decrease-rating",
                  "Decrease rating by 1", mutating=True),
    CommandSchema(
        "selection.toggleColorLabel", "selection.toggle-label",
        "Toggle color label for selected photo(s)",
        params=[
            ParamSchema("color", ParamType.ENUM, required=True,
                        enum_values=["red", "yellow", "green", "blue", "purple"]),
        ],
        mutating=True,
    ),
    CommandSchema(
        "selection.extendSelection", "selection.extend",
        "Extend selection in a direction",
        params=[
            ParamSchema("direction", ParamType.ENUM, default="right",
                        enum_values=["left", "right"]),
            ParamSchema("amount", ParamType.INTEGER, default=1),
        ],
        mutating=True,
    ),
    CommandSchema("selection.deselectActive", "selection.deselect-active",
                  "Deselect the active photo", mutating=True),
    CommandSchema("selection.deselectOthers", "selection.deselect-others",
                  "Deselect all except active photo", mutating=True),
    CommandSchema("selection.getFlag", "selection.get-flag",
                  "Get flag status of selected photo"),
    CommandSchema("selection.getRating", "selection.get-rating",
                  "Get rating of selected photo"),
    CommandSchema(
        "selection.setRating", "selection.set-rating",
        "Set rating for selected photo (0-5)",
        params=[
            ParamSchema("rating", ParamType.INTEGER, required=True,
                        description="Rating 0-5"),
        ],
        mutating=True,
    ),
    CommandSchema("selection.getColorLabel", "selection.get-color-label",
                  "Get color label of selected photo"),
)

# --- preview ---
_register(
    CommandSchema("preview.generatePreview", "preview.generate",
                  "Generate preview with specified size and format",
                  params=[
                      ParamSchema("size", ParamType.INTEGER, default=1024),
                      ParamSchema("format", ParamType.ENUM, default="jpeg",
                                  enum_values=["jpeg", "png"]),
                  ],
                  timeout=120.0),
    CommandSchema("preview.generateBatchPreviews", "preview.generate-batch",
                  "Generate batch previews", timeout=300.0),
    CommandSchema("preview.getPreviewInfo", "preview.info",
                  "Get preview info for a photo",
                  params=[ParamSchema("photoId", ParamType.STRING, required=True)]),
)


# ---------------------------------------------------------------------------
# Lookup functions
# ---------------------------------------------------------------------------

def get_schema(command: str) -> CommandSchema | None:
    return COMMAND_SCHEMAS.get(command)


def get_schemas_by_group(group: str) -> dict[str, CommandSchema]:
    """グループ名でフィルタ（cli_pathベース。bridge commandが異なるグループでも正しく分類）"""
    return {k: v for k, v in COMMAND_SCHEMAS.items() if v.cli_path.startswith(f"{group}.")}


def get_all_schemas() -> dict[str, CommandSchema]:
    return COMMAND_SCHEMAS
