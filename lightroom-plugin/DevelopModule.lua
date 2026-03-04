-- DevelopModule.lua
-- Develop settings API wrapper for Phase 4
-- Enhanced with lightweight error handling

-- Lazy imports to avoid loading issues
local LrDevelopController = nil
local LrApplication = nil
local LrTasks = import 'LrTasks'
local LrProgressScope = nil
local LrUndo = nil

-- Get ErrorUtils from global state (created in PluginInit.lua)
local function getErrorUtils()
    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.ErrorUtils then
        return _G.LightroomPythonBridge.ErrorUtils
    end
    -- Minimal fallback if global not available
    return {
        safeCall = function(func, ...) return LrTasks.pcall(func, ...) end,
        createError = function(code, message) return { error = { code = code or "ERROR", message = message or "An error occurred", severity = "error" } } end,
        createSuccess = function(result) return { result = result or {} } end,
        wrapCallback = function(callback) return callback end,
        validateRequired = function() return true end,
        CODES = { MISSING_PARAM = "MISSING_PARAM", MISSING_PHOTO_ID = "MISSING_PHOTO_ID", INVALID_PARAM_VALUE = "INVALID_PARAM_VALUE", PHOTO_NOT_FOUND = "PHOTO_NOT_FOUND", INVALID_PHOTO_TYPE = "INVALID_PHOTO_TYPE", PHOTO_ACCESS_DENIED = "PHOTO_ACCESS_DENIED" }
    }
end

local ErrorUtils = getErrorUtils()

-- Lazy load Lightroom modules
local function ensureLrModules()
    if not LrDevelopController then
        LrDevelopController = import 'LrDevelopController'
    end
    if not LrApplication then
        LrApplication = import 'LrApplication'
    end
    if not LrProgressScope then
        LrProgressScope = import 'LrProgressScope'
    end
    if not LrUndo then
        local success, undo = ErrorUtils.safeCall(import, 'LrUndo')
        if success and undo and undo.performWithUndo then
            LrUndo = undo
        else
            -- Fallback - some versions of Lightroom might not have LrUndo or it's incomplete
            LrUndo = {
                performWithUndo = function(name, func)
                    return func()  -- Just execute without undo support
                end
            }
        end
    end
end

-- Get logger from global state (defensive)
local function getLogger()
    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.logger then
        return _G.LightroomPythonBridge.logger
    end
    local LrLogger = import 'LrLogger'
    local logger = LrLogger('DevelopModule')
    logger:enable("logfile")
    return logger
end

local DevelopModule = {}

-- Core develop settings (adjustPanel - most reliable)
local CORE_DEVELOP_SETTINGS = {
    -- adjustPanel - Basic Panel (most reliable)
    "Temperature", "Tint", "Exposure", "Contrast", "Highlights", "Shadows",
    "Whites", "Blacks", "Brightness", "Clarity", "Vibrance", "Saturation",
    "Texture", "Dehaze",

    -- tonePanel - Tone Curve (reliable)
    "ParametricDarks", "ParametricLights", "ParametricShadows", "ParametricHighlights",
    "ParametricShadowSplit", "ParametricMidtoneSplit", "ParametricHighlightSplit",

    -- colorGradingPanel - Split Toning
    "SplitToningShadowHue", "SplitToningShadowSaturation",
    "SplitToningHighlightHue", "SplitToningHighlightSaturation",
    "SplitToningBalance",

    -- effectsPanel - Effects
    "PostCropVignetteAmount", "PostCropVignetteMidpoint", "PostCropVignetteFeather",
    "PostCropVignetteRoundness", "PostCropVignetteStyle",
    "GrainAmount", "GrainSize", "GrainFrequency",

    -- lensCorrectionsPanel - Basic Lens Corrections
    "LensProfileEnable", "VignetteAmount", "VignetteMidpoint",
    "PerspectiveVertical", "PerspectiveHorizontal", "PerspectiveRotate",

    -- calibratePanel - Calibration (correct parameter names)
    "ShadowTint", "RedHue", "RedSaturation", "GreenHue", "GreenSaturation", 
    "BlueHue", "BlueSaturation"
}

-- HSL/Color/B&W controls (mixerPanel - these are the correct parameter names!)
local HSL_COLOR_SETTINGS = {
    -- HSL Hue adjustments
    "HueAdjustmentRed", "HueAdjustmentOrange", "HueAdjustmentYellow", "HueAdjustmentGreen",
    "HueAdjustmentAqua", "HueAdjustmentBlue", "HueAdjustmentPurple", "HueAdjustmentMagenta",
    
    -- HSL Saturation adjustments  
    "SaturationAdjustmentRed", "SaturationAdjustmentOrange", "SaturationAdjustmentYellow", "SaturationAdjustmentGreen",
    "SaturationAdjustmentAqua", "SaturationAdjustmentBlue", "SaturationAdjustmentPurple", "SaturationAdjustmentMagenta",
    
    -- HSL Luminance adjustments
    "LuminanceAdjustmentRed", "LuminanceAdjustmentOrange", "LuminanceAdjustmentYellow", "LuminanceAdjustmentGreen",
    "LuminanceAdjustmentAqua", "LuminanceAdjustmentBlue", "LuminanceAdjustmentPurple", "LuminanceAdjustmentMagenta",
    
    -- B&W Gray Mixer
    "GrayMixerRed", "GrayMixerOrange", "GrayMixerYellow", "GrayMixerGreen",
    "GrayMixerAqua", "GrayMixerBlue", "GrayMixerPurple", "GrayMixerMagenta",
    
    -- Point Color Selection (Lightroom Classic 13.0+)
    "PointColors"
}

-- Detail settings (detailPanel)
local DETAIL_SETTINGS = {
    "Sharpness", "SharpenRadius", "SharpenDetail", "SharpenEdgeMasking",
    "LuminanceSmoothing", "LuminanceNoiseReductionDetail", "LuminanceNoiseReductionContrast",
    "ColorNoiseReduction", "ColorNoiseReductionDetail", "ColorNoiseReductionSmoothness"
}

-- Detail and advanced settings (may not be available in all versions)
local ADVANCED_DEVELOP_SETTINGS = {
    -- detailPanel - Detail (correct parameter names)
    "Sharpness", "SharpenRadius", "SharpenDetail", "SharpenEdgeMasking",
    "LuminanceSmoothing", "LuminanceNoiseReductionDetail", "LuminanceNoiseReductionContrast",
    "ColorNoiseReduction", "ColorNoiseReductionDetail", "ColorNoiseReductionSmoothness",

    -- lensCorrectionsPanel - Advanced Lens Corrections
    "AutoLateralCA", "LensProfileDistortionScale", "LensProfileVignettingScale",
    "LensManualDistortionAmount", "DefringePurpleAmount", "DefringeGreenAmount",
    "PerspectiveScale", "PerspectiveAspect", "PerspectiveX", "PerspectiveY",

    -- colorGradingPanel - Advanced Color Grading
    "ColorGradeShadowLum", "ColorGradeHighlightLum", "ColorGradeMidtoneHue",
    "ColorGradeMidtoneSat", "ColorGradeMidtoneLum", "ColorGradeGlobalHue", 
    "ColorGradeGlobalSat", "ColorGradeGlobalLum", "ColorGradeBlending",

    -- effectsPanel - Advanced Effects
    "PostCropVignetteHighlightContrast",

    -- Crop
    "straightenAngle"
}

-- Tone Curve parameters (discovered format: [x1,y1, x2,y2, ...] coordinate pairs)
local TONE_CURVE_SETTINGS = {
    "ToneCurvePV2012",        -- Main luminance curve  
    "ToneCurvePV2012Red",     -- Red channel curve
    "ToneCurvePV2012Green",   -- Green channel curve
    "ToneCurvePV2012Blue",    -- Blue channel curve
    "CurveRefineSaturation"   -- Curve saturation refinement
}

-- LensBlur parameters (Lightroom Classic 13.3+, requires modern versions)
local LENS_BLUR_SETTINGS = {
    "LensBlurActive",         -- Enable/disable lens blur
    "LensBlurAmount",         -- Blur strength
    "LensBlurCatEye",         -- Cat eye bokeh effect
    "LensBlurHighlightsBoost", -- Highlight enhancement
    "LensBlurFocalRange"      -- Depth range control
}

-- Get current develop settings with lightweight error handling
function DevelopModule.getSettings(params, callback)
    ensureLrModules()
    local logger = getLogger()
    logger:debug("DevelopModule.getSettings called")
    
    -- Wrap callback for consistent error handling
    local wrappedCallback = ErrorUtils.wrapCallback(callback, "DevelopModule.getSettings")
    
    if not params then
        wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.MISSING_PARAM, "Parameters are required"))
        return
    end
    
    local photoId = params.photoId
    if not photoId then
        wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.MISSING_PHOTO_ID, "Photo ID is required"))
        return
    end
    
    -- Validate photoId is a valid number
    if not tonumber(photoId) or tonumber(photoId) <= 0 then
        wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.INVALID_PARAM_VALUE, 
            "Photo ID must be a positive number"))
        return
    end
    
    logger:debug("Getting develop settings for photo: " .. photoId)
    
    local catalog = LrApplication.activeCatalog()
    
    catalog:withReadAccessDo(function()
        -- Find photo by ID
        local photoSuccess, photo = ErrorUtils.safeCall(function()
            return catalog:getPhotoByLocalId(tonumber(photoId))
        end)
        
        if not photoSuccess or not photo then
            wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.PHOTO_NOT_FOUND, 
                "Photo with ID " .. photoId .. " not found"))
            return
        end
        
        -- Check if photo can be developed
        local metadataSuccess, fileFormat = ErrorUtils.safeCall(function()
            return photo:getRawMetadata("fileFormat")
        end)
        
        local isVirtualCopy = false
        ErrorUtils.safeCall(function()
            isVirtualCopy = photo:getRawMetadata("isVirtualCopy")
        end)
        
        if not metadataSuccess or not fileFormat or 
           (fileFormat ~= "RAW" and fileFormat ~= "DNG" and not isVirtualCopy) then
            wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.INVALID_PHOTO_TYPE, 
                "Photo cannot be developed (not a raw file or virtual copy)"))
            return
        end
        
        -- Switch to photo for develop context
        local switchSuccess = ErrorUtils.safeCall(function()
            catalog:setSelectedPhotos(photo, {})
            return true
        end)
        
        if not switchSuccess then
            wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.PHOTO_ACCESS_DENIED, 
                "Could not access photo for develop settings"))
            return
        end
        
        local settings = {}
        local errors = {}
        
        -- Read core develop settings
        for _, settingName in ipairs(CORE_DEVELOP_SETTINGS) do
            local success, value = ErrorUtils.safeCall(function()
                return LrDevelopController.getValue(settingName)
            end)
            
            if success and value ~= nil then
                settings[settingName] = value
            else
                errors[settingName] = "Unable to read value"
            end
        end
        
        -- Read HSL/Color settings
        for _, settingName in ipairs(HSL_COLOR_SETTINGS) do
            local success, value = ErrorUtils.safeCall(function()
                return LrDevelopController.getValue(settingName)
            end)
            
            if success and value ~= nil then
                settings[settingName] = value
            else
                errors[settingName] = "Unable to read value"
            end
        end
        
        -- Read Detail settings
        for _, settingName in ipairs(DETAIL_SETTINGS) do
            local success, value = ErrorUtils.safeCall(function()
                return LrDevelopController.getValue(settingName)
            end)
            
            if success and value ~= nil then
                settings[settingName] = value
            else
                errors[settingName] = "Unable to read value"
            end
        end
        
        -- Include error count for transparency
        local result = {
            settings = settings,
            photoId = photoId,
            settingsCount = 0,
            errorCount = 0
        }
        
        -- Count successful settings
        for k, v in pairs(settings) do
            result.settingsCount = result.settingsCount + 1
        end
        
        -- Count errors
        for k, v in pairs(errors) do
            result.errorCount = result.errorCount + 1
        end
        
        -- Include errors if any occurred (but don't fail the request)
        if result.errorCount > 0 then
            result.partialErrors = errors
        end
        
        logger:debug("Successfully read " .. result.settingsCount .. " settings with " .. result.errorCount .. " errors")
        wrappedCallback(ErrorUtils.createSuccess(result, "Develop settings retrieved successfully"))
    end)
end

-- Apply develop settings with undo support
function DevelopModule.applySettings(params, callback)
    -- Add logging to trace the issue
    local logger = getLogger()
    logger:info("TRACE: DevelopModule.applySettings called")
    
    local photoId = params.photoId
    if not tonumber(photoId) or tonumber(photoId) <= 0 then
        wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.INVALID_PARAM_VALUE, 
            "Photo ID must be a positive number"))
        return
    end
    
    -- Ensure modules are loaded
    local moduleSuccess, moduleError = ErrorUtils.safeCall(ensureLrModules)
    if not moduleSuccess then
        wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.RESOURCE_UNAVAILABLE, 
            "Failed to load Lightroom modules: " .. tostring(moduleError)))
        return
    end
    
    local logger = getLogger()
    logger:debug("Getting develop settings for photo: " .. photoId)
    
    local catalog = LrApplication.activeCatalog()
    
    catalog:withReadAccessDo(function()
        -- Find photo by ID
        local photoSuccess, photo = ErrorUtils.safeCall(function()
            return catalog:getPhotoByLocalId(tonumber(photoId))
        end)
        
        if not photoSuccess or not photo then
            wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.PHOTO_NOT_FOUND, 
                "Photo with ID " .. photoId .. " not found"))
            return
        end
        
        -- Check if photo can be developed
        local metadataSuccess, fileFormat = ErrorUtils.safeCall(function()
            return photo:getRawMetadata("fileFormat")
        end)
        
        local isVirtualCopy = false
        ErrorUtils.safeCall(function()
            isVirtualCopy = photo:getRawMetadata("isVirtualCopy")
        end)
        
        if not metadataSuccess or not fileFormat or 
           (fileFormat ~= "RAW" and fileFormat ~= "DNG" and not isVirtualCopy) then
            wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.INVALID_PHOTO_TYPE, 
                "Photo cannot be developed (not a raw file or virtual copy)"))
            return
        end
        
        local settings = {}
        local errors = {}
        
        -- Read core develop settings
        for _, settingName in ipairs(CORE_DEVELOP_SETTINGS) do
            local success, value = ErrorUtils.safeCall(function()
                return LrDevelopController.getValue(settingName)
            end)
            
            if success and value ~= nil then
                settings[settingName] = value
            else
                errors[settingName] = "Unable to read value"
            end
        end
        
        -- Read HSL/Color settings
        for _, settingName in ipairs(HSL_COLOR_SETTINGS) do
            local success, value = ErrorUtils.safeCall(function()
                return LrDevelopController.getValue(settingName)
            end)
            
            if success and value ~= nil then
                settings[settingName] = value
            end
        end
        
        -- Try advanced settings (don't fail if unavailable)
        for _, settingName in ipairs(ADVANCED_DEVELOP_SETTINGS) do
            local success, value = ErrorUtils.safeCall(function()
                return LrDevelopController.getValue(settingName)
            end)
            
            if success and value ~= nil then
                settings[settingName] = value
            end
        end
        
        -- Get photo metadata
        local metadata = {
            photoId = photo.localIdentifier,
            fileFormat = fileFormat,
            isVirtualCopy = isVirtualCopy
        }
        
        -- Safely get filename
        ErrorUtils.safeCall(function()
            metadata.filename = photo:getFormattedMetadata("fileName")
        end)
        
        local settingsCount = 0
        for _ in pairs(settings) do settingsCount = settingsCount + 1 end
        
        logger:info("Retrieved " .. settingsCount .. " develop settings for photo " .. photoId)
        
        wrappedCallback(ErrorUtils.createSuccess({
            settings = settings,
            metadata = metadata,
            errors = next(errors) and errors or nil
        }, "Develop settings retrieved successfully"))
    end)
end

-- Apply develop settings with undo support
function DevelopModule.applySettings(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    -- Ensure LrUndo is available
    if not LrUndo or not LrUndo.performWithUndo then
        logger:debug("LrUndo not available, creating fallback")
        LrUndo = {
            performWithUndo = function(name, func)
                logger:debug("Executing without undo support: " .. name)
                return func()
            end
        }
    end
    
    if not params then
        callback({
            error = {
                code = "MISSING_PARAMS",
                message = "Parameters are required",
                severity = "error"
            }
        })
        return
    end
    
    local photoId = params.photoId
    local settings = params.settings

    if not photoId then
        callback({
            error = {
                code = "MISSING_PHOTO_ID",
                message = "Photo ID is required",
                severity = "error"
            }
        })
        return
    end

    if not settings or type(settings) ~= "table" then
        callback({
            error = {
                code = "INVALID_SETTINGS",
                message = "Settings must be provided as a table",
                severity = "error"
            }
        })
        return
    end

    logger:debug("Applying develop settings to photo: " .. photoId)

    local catalog = LrApplication.activeCatalog()

    catalog:withWriteAccessDo("Apply Develop Settings", function()
        local photo = catalog:getPhotoByLocalId(tonumber(photoId))

        if not photo then
            callback({
                error = {
                    code = "PHOTO_NOT_FOUND",
                    message = "Photo with ID " .. photoId .. " not found"
                }
            })
            return
        end

        -- Validate settings before applying
        local validSettings = {}
        local invalidSettings = {}

        for settingName, value in pairs(settings) do
            local isValid = false

            -- Check if setting name is in our supported lists
            for _, validName in ipairs(CORE_DEVELOP_SETTINGS) do
                if validName == settingName then
                    isValid = true
                    break
                end
            end
            
            if not isValid then
                for _, validName in ipairs(HSL_COLOR_SETTINGS) do
                    if validName == settingName then
                        isValid = true
                        break
                    end
                end
            end
            
            if not isValid then
                for _, validName in ipairs(ADVANCED_DEVELOP_SETTINGS) do
                    if validName == settingName then
                        isValid = true
                        break
                    end
                end
            end
            
            if not isValid then
                for _, validName in ipairs(TONE_CURVE_SETTINGS) do
                    if validName == settingName then
                        isValid = true
                        break
                    end
                end
            end
            
            if not isValid then
                for _, validName in ipairs(LENS_BLUR_SETTINGS) do
                    if validName == settingName then
                        isValid = true
                        break
                    end
                end
            end

            if isValid then
                validSettings[settingName] = value
            else
                invalidSettings[settingName] = "Unknown setting name"
            end
        end

        local validCount = 0
        for _ in pairs(validSettings) do validCount = validCount + 1 end

        if validCount == 0 then
            callback({
                error = {
                    code = "NO_VALID_SETTINGS",
                    message = "No valid settings provided",
                    details = { invalidSettings = invalidSettings }
                }
            })
            return
        end

        -- Apply settings with undo support
        logger:debug("About to use LrUndo.performWithUndo - LrUndo is: " .. tostring(LrUndo))
        logger:debug("LrUndo.performWithUndo is: " .. tostring(LrUndo and LrUndo.performWithUndo))
        
        local success, error = ErrorUtils.safeCall(function()
            LrUndo.performWithUndo("Apply Develop Settings", function()
                local appliedCount = 0

                for settingName, value in pairs(validSettings) do
                    local applySuccess, applyError = ErrorUtils.safeCall(function()
                        LrDevelopController.setValue(settingName, value)
                    end)

                    if applySuccess then
                        appliedCount = appliedCount + 1
                        logger:debug("Applied setting: " .. settingName .. " = " .. tostring(value))
                    else
                        logger:error("Failed to apply setting " .. settingName .. ": " .. tostring(applyError))
                        invalidSettings[settingName] = tostring(applyError)
                    end
                end
            end)
        end)

        if success then
            logger:info("Successfully applied develop settings")
            callback({
                result = {
                    applied = validCount,
                    invalid = next(invalidSettings) and invalidSettings or nil
                }
            })
        else
            logger:error("Failed to apply develop settings: " .. tostring(error))
            callback({
                error = {
                    code = "APPLICATION_FAILED",
                    message = "Failed to apply settings: " .. tostring(error)
                }
            })
        end
    end)
end

-- Batch apply settings to multiple photos
function DevelopModule.batchApplySettings(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    -- Ensure LrUndo is available
    if not LrUndo or not LrUndo.performWithUndo then
        logger:debug("LrUndo not available for batch, creating fallback")
        LrUndo = {
            performWithUndo = function(name, func)
                logger:debug("Executing batch without undo support: " .. name)
                return func()
            end
        }
    end
    
    if not params then
        callback({
            error = {
                code = "MISSING_PARAMS",
                message = "Parameters are required",
                severity = "error"
            }
        })
        return
    end
    
    local photoIds = params.photoIds
    local settings = params.settings

    if not photoIds or type(photoIds) ~= "table" or #photoIds == 0 then
        callback({
            error = {
                code = "MISSING_PHOTO_IDS",
                message = "Photo IDs array is required",
                severity = "error"
            }
        })
        return
    end

    if not settings or type(settings) ~= "table" then
        callback({
            error = {
                code = "INVALID_SETTINGS",
                message = "Settings must be provided as a table",
                severity = "error"
            }
        })
        return
    end

    logger:info("Batch applying settings to " .. #photoIds .. " photos")

    local catalog = LrApplication.activeCatalog()

    catalog:withWriteAccessDo("Batch Apply Develop Settings", function()
        local results = {}

        logger:debug("Batch: About to use LrUndo.performWithUndo - LrUndo is: " .. tostring(LrUndo))
        logger:debug("Batch: LrUndo.performWithUndo is: " .. tostring(LrUndo and LrUndo.performWithUndo))
        
        LrUndo.performWithUndo("Batch Apply Develop Settings", function()
            for i, photoId in ipairs(photoIds) do
                local photo = catalog:getPhotoByLocalId(tonumber(photoId))

                if not photo then
                    table.insert(results, {
                        photoId = photoId,
                        success = false,
                        error = "Photo not found"
                    })
                else
                    -- Apply settings to this photo
                    local appliedCount = 0
                    local errors = {}

                    for settingName, value in pairs(settings) do
                        local success, error = ErrorUtils.safeCall(function()
                            LrDevelopController.setValue(settingName, value)
                        end)

                        if success then
                            appliedCount = appliedCount + 1
                        else
                            errors[settingName] = tostring(error)
                        end
                    end

                    table.insert(results, {
                        photoId = photoId,
                        success = appliedCount > 0,
                        applied = appliedCount,
                        errors = next(errors) and errors or nil
                    })
                end
            end
        end)

        callback({
            result = {
                processed = #results,
                results = results
            }
        })
    end)
end

-- Get value of a single develop parameter
function DevelopModule.getValue(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local param = params and params.param
    if not param then
        callback({
            error = {
                code = "MISSING_PARAM",
                message = "Parameter name is required"
            }
        })
        return
    end
    
    logger:debug("Getting develop parameter: " .. param)
    
    local catalog = LrApplication.activeCatalog()
    
    catalog:withReadAccessDo(function()
        -- Check if any photos are selected
        local photos = catalog:getTargetPhotos()
        if not photos or #photos == 0 then
            callback({
                error = {
                    code = "NO_PHOTO_SELECTED",
                    message = "Parameter '" .. param .. "' is available, but no photo is currently selected. Please select a photo to access develop parameters."
                }
            })
            return
        end
        
        -- Try to get the value with selected photo
        local success, value = ErrorUtils.safeCall(function()
            return LrDevelopController.getValue(param)
        end)
        
        if success and value ~= nil then
            callback({
                result = {
                    param = param,
                    value = value
                }
            })
        else
            callback({
                error = {
                    code = "INVALID_PARAM",
                    message = "Parameter '" .. param .. "' is not available or not supported for the selected photo"
                }
            })
        end
    end)
end

-- Set value of a single develop parameter
function DevelopModule.setValue(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local param = params and params.param
    local value = params and params.value
    
    if not param then
        callback({
            error = {
                code = "MISSING_PARAM",
                message = "Parameter name is required"
            }
        })
        return
    end
    
    if value == nil then
        callback({
            error = {
                code = "MISSING_VALUE",
                message = "Parameter value is required"
            }
        })
        return
    end
    
    -- Define parameters that require numeric values with their valid ranges
    local parameterSpecs = {
        Exposure = { type = "number", min = -5.0, max = 5.0 },
        Highlights = { type = "number", min = -100, max = 100 },
        Shadows = { type = "number", min = -100, max = 100 },
        Whites = { type = "number", min = -100, max = 100 },
        Blacks = { type = "number", min = -100, max = 100 },
        Contrast = { type = "number", min = -100, max = 100 },
        Brightness = { type = "number", min = -100, max = 100 },
        Vibrance = { type = "number", min = -100, max = 100 },
        Saturation = { type = "number", min = -100, max = 100 },
        Temperature = { type = "number", min = 2000, max = 50000 },
        Tint = { type = "number", min = -150, max = 150 },
        Clarity = { type = "number", min = -100, max = 100 },
        Dehaze = { type = "number", min = -100, max = 100 },
        Texture = { type = "number", min = -100, max = 100 },
        VignetteAmount = { type = "number", min = -100, max = 100 },
        VignetteMidpoint = { type = "number", min = 0, max = 100 }
    }
    
    local paramSpec = parameterSpecs[param]
    
    -- Validate parameter type
    if paramSpec and paramSpec.type == "number" and type(value) ~= "number" then
        -- Try to convert string to number
        local numValue = tonumber(value)
        if not numValue then
            callback({
                error = {
                    code = "INVALID_PARAM_TYPE",
                    message = "Parameter '" .. param .. "' requires a numeric value, got " .. type(value)
                }
            })
            return
        end
        value = numValue -- Use converted value
    end
    
    -- Validate parameter range
    if paramSpec and paramSpec.type == "number" and type(value) == "number" then
        if value < paramSpec.min or value > paramSpec.max then
            callback({
                error = {
                    code = "INVALID_PARAM_VALUE",
                    message = "Parameter '" .. param .. "' value " .. tostring(value) .. " is out of range (" .. 
                             paramSpec.min .. " to " .. paramSpec.max .. ")"
                }
            })
            return
        end
    end
    
    logger:debug("Setting develop parameter: " .. param .. " = " .. tostring(value))
    
    local catalog = LrApplication.activeCatalog()
    
    -- Use withWriteAccessDo with timeout to prevent blocking
    local writeSuccess, writeError = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Set Develop Parameter", function()
            LrDevelopController.setValue(param, value)
        end, { timeout = 10 })  -- 10 second timeout
    end)
    
    if writeSuccess then
        callback({
            result = {
                param = param,
                value = value,
                applied = true
            }
        })
    else
        logger:error("Failed to set parameter " .. param .. " (write access): " .. tostring(writeError))
        callback({
            error = {
                code = "WRITE_ACCESS_BLOCKED",
                message = "Failed to set parameter (write access blocked): " .. tostring(writeError)
            }
        })
    end
end

-- Get the valid range for a develop parameter
function DevelopModule.getRange(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local param = params and params.param
    if not param then
        callback({
            error = {
                code = "MISSING_PARAM",
                message = "Parameter name is required"
            }
        })
        return
    end
    
    logger:debug("Getting range for develop parameter: " .. param)
    
    local success, range = ErrorUtils.safeCall(function()
        return LrDevelopController.getRange(param)
    end)
    
    if success and range then
        logger:debug("Range returned: " .. tostring(range) .. " (type: " .. type(range) .. ")")
        
        -- Handle different return types from LrDevelopController.getRange
        if type(range) == "table" and range.min and range.max then
            -- Standard range table
            callback({
                result = {
                    param = param,
                    min = range.min,
                    max = range.max
                }
            })
        elseif type(range) == "number" then
            -- Some parameters may return a single number (like maximum value)
            -- Provide a sensible default range
            local min_val = -range
            local max_val = range
            
            -- Special cases for known parameters
            if param == "Temperature" then
                min_val = 2000
                max_val = 50000
            elseif param == "Tint" then
                min_val = -150
                max_val = 150
            else
                -- For most develop parameters, range is typically -100 to +100 or similar
                min_val = -range
                max_val = range
            end
            
            callback({
                result = {
                    param = param,
                    min = min_val,
                    max = max_val,
                    note = "Range estimated from single value: " .. tostring(range)
                }
            })
        else
            -- Fallback for unknown range format
            local min_val, max_val = -100, 100
            
            -- Special cases for known parameters
            if param == "Temperature" then
                min_val, max_val = 2000, 50000
            elseif param == "Tint" then
                min_val, max_val = -150, 150
            elseif param == "Exposure" then
                min_val, max_val = -5, 5
            end
            
            callback({
                result = {
                    param = param,
                    min = min_val,
                    max = max_val,
                    note = "Default range used (unknown format: " .. type(range) .. ")"
                }
            })
        end
    else
        callback({
            error = {
                code = "INVALID_PARAM",
                message = "Unable to get range for parameter: " .. param
            }
        })
    end
end

-- Reset a single develop parameter to default with comprehensive error handling
function DevelopModule.resetToDefault(params, callback)
    local wrappedCallback = ErrorUtils.wrapCallback(callback, "resetToDefault")
    
    -- Basic parameter validation
    local isValid, errorMsg = ErrorUtils.validateRequired(params, {"param"})
    if not isValid then
        wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.MISSING_PARAM, errorMsg))
        return
    end
    
    -- Ensure modules are loaded
    local moduleSuccess, moduleError = ErrorUtils.safeCall(ensureLrModules)
    if not moduleSuccess then
        wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.RESOURCE_UNAVAILABLE, 
            "Failed to load Lightroom modules: " .. tostring(moduleError)))
        return
    end
    
    local logger = getLogger()
    local param = params.param
    
    logger:debug("Resetting develop parameter to default: " .. param)
    
    local catalog = LrApplication.activeCatalog()
    catalog:withWriteAccessDo("Reset Develop Parameter", function()
        local success, error = ErrorUtils.safeCall(function()
            LrDevelopController.resetToDefault(param)
        end)
        
        if success then
            -- Get the new value after reset
            local newValue = nil
            ErrorUtils.safeCall(function()
                newValue = LrDevelopController.getValue(param)
            end)
            
            wrappedCallback(ErrorUtils.createSuccess({
                param = param,
                reset = true,
                newValue = newValue
            }, "Parameter reset to default successfully"))
        else
            logger:error("Failed to reset parameter " .. param .. ": " .. tostring(error))
            wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.OPERATION_FAILED, 
                "Failed to reset parameter: " .. tostring(error)))
        end
    end)
end

-- Apply Auto Tone to current photo
function DevelopModule.setAutoTone(params, callback)
    local wrappedCallback = ErrorUtils.wrapCallback(callback, "setAutoTone")
    
    -- Ensure modules are loaded
    local moduleSuccess, moduleError = ErrorUtils.safeCall(ensureLrModules)
    if not moduleSuccess then
        wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.RESOURCE_UNAVAILABLE, 
            "Failed to load Lightroom modules: " .. tostring(moduleError)))
        return
    end
    
    local logger = getLogger()
    logger:debug("Applying Auto Tone")
    
    local catalog = LrApplication.activeCatalog()
    catalog:withWriteAccessDo("Auto Tone", function()
        local success, error = ErrorUtils.safeCall(function()
            LrDevelopController.setAutoTone()
        end)
        
        if success then
            wrappedCallback(ErrorUtils.createSuccess({
                autoTone = true,
                applied = true
            }, "Auto Tone applied successfully"))
        else
            logger:error("Failed to apply Auto Tone: " .. tostring(error))
            wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.OPERATION_FAILED, 
                "Failed to apply Auto Tone: " .. tostring(error)))
        end
    end)
end

-- Apply Auto White Balance to current photo
function DevelopModule.setAutoWhiteBalance(params, callback)
    local wrappedCallback = ErrorUtils.wrapCallback(callback, "setAutoWhiteBalance")
    
    -- Ensure modules are loaded
    local moduleSuccess, moduleError = ErrorUtils.safeCall(ensureLrModules)
    if not moduleSuccess then
        wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.RESOURCE_UNAVAILABLE, 
            "Failed to load Lightroom modules: " .. tostring(moduleError)))
        return
    end
    
    local logger = getLogger()
    logger:debug("Applying Auto White Balance")
    
    local catalog = LrApplication.activeCatalog()
    catalog:withWriteAccessDo("Auto White Balance", function()
        local success, error = ErrorUtils.safeCall(function()
            LrDevelopController.setAutoWhiteBalance()
        end)
        
        if success then
            wrappedCallback(ErrorUtils.createSuccess({
                autoWhiteBalance = true,
                applied = true
            }, "Auto White Balance applied successfully"))
        else
            logger:error("Failed to apply Auto White Balance: " .. tostring(error))
            wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.OPERATION_FAILED, 
                "Failed to apply Auto White Balance: " .. tostring(error)))
        end
    end)
end

-- Get current process version
function DevelopModule.getProcessVersion(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    logger:debug("Getting process version")
    
    local success, version = ErrorUtils.safeCall(function()
        return LrDevelopController.getProcessVersion()
    end)
    
    if success and version then
        callback({
            result = {
                processVersion = version
            }
        })
    else
        callback({
            error = {
                code = "VERSION_FAILED",
                message = "Failed to get process version"
            }
        })
    end
end

-- Set process version
function DevelopModule.setProcessVersion(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local version = params and params.version
    if not version then
        callback({
            error = {
                code = "MISSING_VERSION",
                message = "Process version is required (Version 1, Version 2, Version 3, Version 4, Version 5, or Version 6)"
            }
        })
        return
    end
    
    logger:debug("Setting process version: " .. version)
    
    local catalog = LrApplication.activeCatalog()
    catalog:withWriteAccessDo("Set Process Version", function()
        local success, error = ErrorUtils.safeCall(function()
            LrDevelopController.setProcessVersion(version)
        end)
        
        if success then
            callback({
                result = {
                    processVersion = version,
                    applied = true
                }
            })
        else
            logger:error("Failed to set process version: " .. tostring(error))
            callback({
                error = {
                    code = "VERSION_SET_FAILED",
                    message = "Failed to set process version: " .. tostring(error)
                }
            })
        end
    end)
end

-- Reset all develop adjustments
function DevelopModule.resetAllDevelopAdjustments(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    logger:debug("Resetting all develop adjustments")
    
    local catalog = LrApplication.activeCatalog()
    catalog:withWriteAccessDo("Reset All Develop Adjustments", function()
        local success, error = ErrorUtils.safeCall(function()
            LrDevelopController.resetAllDevelopAdjustments()
        end)
        
        if success then
            callback({
                result = {
                    resetAll = true,
                    applied = true
                }
            })
        else
            logger:error("Failed to reset all adjustments: " .. tostring(error))
            callback({
                error = {
                    code = "RESET_ALL_FAILED",
                    message = "Failed to reset all adjustments: " .. tostring(error)
                }
            })
        end
    end)
end

-- Subscribe to develop changes with proper cleanup
function DevelopModule.watchChanges(callback)
    ensureLrModules()
    local logger = getLogger()

    logger:info("DevelopModule.watchChanges called - NEW VERSION with fixed callback order")

    if type(callback) ~= "function" then
        logger:error("DevelopModule.watchChanges requires a callback function")
        return nil
    end

    logger:info("Setting up develop change observer with corrected parameter order")

    local observer = {}
    local isActive = true

    -- Set up develop controller observer
    LrDevelopController.addAdjustmentChangeObserver(function()
        if not isActive then return end

        local photo = LrApplication.activeCatalog():getTargetPhoto()
        if not photo then return end

        -- Get changed settings (focus on core settings for performance)
        local changes = {}
        for _, settingName in ipairs(CORE_DEVELOP_SETTINGS) do
            local success, value = ErrorUtils.safeCall(function()
                return LrDevelopController.getValue(settingName)
            end)
            if success and value ~= nil then
                changes[settingName] = value
            end
        end

        -- Call user callback
        local success, error = ErrorUtils.safeCall(callback, photo, changes)
        if not success then
            logger:error("Develop change callback error: " .. tostring(error))
        end
    end, observer)

    -- Set up active photo observer
    LrApplication.addActivePhotoChangeObserver(function()
        if not isActive then return end

        local photo = LrApplication.activeCatalog():getTargetPhoto()
        if photo then
            logger:debug("Active photo changed: " .. photo:getFormattedMetadata("fileName"))

            -- Notify of photo change
            local success, error = ErrorUtils.safeCall(callback, photo, nil)  -- nil indicates photo change, not setting change
            if not success then
                logger:error("Photo change callback error: " .. tostring(error))
            end
        end
    end, observer)

    -- Return unsubscribe function
    return function()
        isActive = false
        LrDevelopController.removeAdjustmentChangeObserver(observer)
        LrApplication.removeActivePhotoChangeObserver(observer)
        logger:info("Develop change observer removed")
    end
end

-- ToneCurve Manipulation Functions (Based on reverse-engineered format)

-- Helper function to parse curve array into coordinate points
local function parseCurvePoints(curveArray)
    if not curveArray or type(curveArray) ~= "table" or #curveArray % 2 ~= 0 then
        return {}
    end
    
    local points = {}
    for i = 1, #curveArray, 2 do
        table.insert(points, {x = curveArray[i], y = curveArray[i + 1]})
    end
    return points
end

-- Helper function to convert points back to curve array
local function pointsToCurveArray(points)
    if not points or type(points) ~= "table" then
        return {}
    end
    
    local result = {}
    for _, point in ipairs(points) do
        if type(point) == "table" and point.x and point.y then
            table.insert(result, point.x)
            table.insert(result, point.y)
        end
    end
    return result
end

-- Get curve as coordinate points for easier manipulation
function DevelopModule.getCurvePoints(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local param = params and params.param
    if not param then
        callback({
            error = {
                code = "MISSING_PARAM",
                message = "Parameter name is required"
            }
        })
        return
    end
    
    -- Validate curve parameter
    local isValidCurve = false
    for _, curveName in ipairs(TONE_CURVE_SETTINGS) do
        if curveName == param then
            isValidCurve = true
            break
        end
    end
    
    if not isValidCurve then
        callback({
            error = {
                code = "INVALID_CURVE_PARAM",
                message = "Parameter must be a tone curve parameter: " .. table.concat(TONE_CURVE_SETTINGS, ", ")
            }
        })
        return
    end
    
    logger:debug("Getting curve points for: " .. param)
    
    local success, curveArray = ErrorUtils.safeCall(function()
        return LrDevelopController.getValue(param)
    end)
    
    if success and curveArray then
        local points = parseCurvePoints(curveArray)
        callback({
            result = {
                param = param,
                points = points,
                pointCount = #points,
                rawArray = curveArray
            }
        })
    else
        callback({
            error = {
                code = "CURVE_READ_FAILED",
                message = "Unable to read curve data for parameter: " .. param
            }
        })
    end
end

-- Set curve from coordinate points
function DevelopModule.setCurvePoints(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local param = params and params.param
    local points = params and params.points
    
    if not param then
        callback({
            error = {
                code = "MISSING_PARAM",
                message = "Parameter name is required"
            }
        })
        return
    end
    
    if not points or type(points) ~= "table" then
        callback({
            error = {
                code = "MISSING_POINTS",
                message = "Points array is required"
            }
        })
        return
    end
    
    -- Validate curve parameter
    local isValidCurve = false
    for _, curveName in ipairs(TONE_CURVE_SETTINGS) do
        if curveName == param then
            isValidCurve = true
            break
        end
    end
    
    if not isValidCurve then
        callback({
            error = {
                code = "INVALID_CURVE_PARAM",
                message = "Parameter must be a tone curve parameter: " .. table.concat(TONE_CURVE_SETTINGS, ", ")
            }
        })
        return
    end
    
    -- Convert points to curve array
    local curveArray = pointsToCurveArray(points)
    if #curveArray == 0 then
        callback({
            error = {
                code = "INVALID_POINTS",
                message = "Points must be array of {x, y} coordinate objects"
            }
        })
        return
    end
    
    logger:debug("Setting curve points for " .. param .. ": " .. #points .. " points")
    
    local catalog = LrApplication.activeCatalog()
    catalog:withWriteAccessDo("Set Curve Points", function()
        local success, error = ErrorUtils.safeCall(function()
            LrDevelopController.setValue(param, curveArray)
        end)
        
        if success then
            callback({
                result = {
                    param = param,
                    pointsSet = #points,
                    applied = true
                }
            })
        else
            logger:error("Failed to set curve points for " .. param .. ": " .. tostring(error))
            callback({
                error = {
                    code = "CURVE_SET_FAILED",
                    message = "Failed to set curve points: " .. tostring(error)
                }
            })
        end
    end)
end

-- Set a linear curve (straight line from 0,0 to 255,255)
function DevelopModule.setCurveLinear(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local param = params and params.param
    if not param then
        callback({
            error = {
                code = "MISSING_PARAM",
                message = "Parameter name is required"
            }
        })
        return
    end
    
    logger:debug("Setting linear curve for: " .. param)
    
    -- Linear curve: start and end points only
    local linearPoints = {{x = 0, y = 0}, {x = 255, y = 255}}
    
    -- Call setCurvePoints with linear points
    DevelopModule.setCurvePoints({
        param = param,
        points = linearPoints
    }, callback)
end

-- Create an S-curve for contrast enhancement
function DevelopModule.setCurveSCurve(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local param = params and params.param
    local strength = params and params.strength or 25  -- Default strength
    
    if not param then
        callback({
            error = {
                code = "MISSING_PARAM",
                message = "Parameter name is required"
            }
        })
        return
    end
    
    if type(strength) ~= "number" or strength < 0 or strength > 100 then
        callback({
            error = {
                code = "INVALID_STRENGTH",
                message = "Strength must be a number between 0 and 100"
            }
        })
        return
    end
    
    logger:debug("Setting S-curve for " .. param .. " with strength: " .. strength)
    
    -- Calculate S-curve points based on strength
    local offset = math.floor(strength * 0.4)  -- Scale strength to reasonable offset
    
    local sCurvePoints = {
        {x = 0, y = 0},                           -- Black point
        {x = 64, y = 64 - offset},               -- Darken shadows
        {x = 128, y = 128},                      -- Midpoint unchanged
        {x = 192, y = 192 + offset},             -- Brighten highlights  
        {x = 255, y = 255}                       -- White point
    }
    
    -- Call setCurvePoints with S-curve points
    DevelopModule.setCurvePoints({
        param = param,
        points = sCurvePoints
    }, callback)
end

-- Add a single point to an existing curve
function DevelopModule.addCurvePoint(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local param = params and params.param
    local x = params and params.x
    local y = params and params.y
    
    if not param then
        callback({
            error = {
                code = "MISSING_PARAM",
                message = "Parameter name is required"
            }
        })
        return
    end
    
    if not x or not y then
        callback({
            error = {
                code = "MISSING_COORDINATES",
                message = "Both x and y coordinates are required"
            }
        })
        return
    end
    
    if type(x) ~= "number" or type(y) ~= "number" then
        callback({
            error = {
                code = "INVALID_COORDINATES", 
                message = "x and y must be numbers"
            }
        })
        return
    end
    
    if x < 0 or x > 255 or y < 0 or y > 255 then
        callback({
            error = {
                code = "COORDINATES_OUT_OF_RANGE",
                message = "x and y must be between 0 and 255"
            }
        })
        return
    end
    
    logger:debug("Adding curve point to " .. param .. ": (" .. x .. ", " .. y .. ")")
    
    -- First get current curve points
    DevelopModule.getCurvePoints({param = param}, function(result)
        if result.error then
            callback(result)
            return
        end
        
        local currentPoints = result.result.points
        local newPoint = {x = x, y = y}
        
        -- Insert new point in correct position (sorted by x coordinate)
        local insertIndex = #currentPoints + 1
        for i, point in ipairs(currentPoints) do
            if point.x > x then
                insertIndex = i
                break
            elseif point.x == x then
                -- Replace existing point at same x coordinate
                currentPoints[i] = newPoint
                insertIndex = -1  -- Signal that we replaced, not inserted
                break
            end
        end
        
        if insertIndex > 0 then
            table.insert(currentPoints, insertIndex, newPoint)
        end
        
        -- Set the modified curve
        DevelopModule.setCurvePoints({
            param = param,
            points = currentPoints
        }, callback)
    end)
end

-- Remove a curve point by index
function DevelopModule.removeCurvePoint(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local param = params and params.param
    local index = params and params.index
    
    if not param then
        callback({
            error = {
                code = "MISSING_PARAM",
                message = "Parameter name is required"
            }
        })
        return
    end
    
    if not index then
        callback({
            error = {
                code = "MISSING_INDEX",
                message = "Point index is required"
            }
        })
        return
    end
    
    if type(index) ~= "number" or index < 1 then
        callback({
            error = {
                code = "INVALID_INDEX",
                message = "Index must be a positive number starting from 1"
            }
        })
        return
    end
    
    logger:debug("Removing curve point from " .. param .. " at index: " .. index)
    
    -- Get current curve points
    DevelopModule.getCurvePoints({param = param}, function(result)
        if result.error then
            callback(result)
            return
        end
        
        local currentPoints = result.result.points
        
        if index > #currentPoints then
            callback({
                error = {
                    code = "INDEX_OUT_OF_RANGE",
                    message = "Index " .. index .. " exceeds curve point count (" .. #currentPoints .. ")"
                }
            })
            return
        end
        
        -- Don't allow removing endpoints for safety
        if index == 1 or index == #currentPoints then
            callback({
                error = {
                    code = "CANNOT_REMOVE_ENDPOINT",
                    message = "Cannot remove curve endpoints (first or last point)"
                }
            })
            return
        end
        
        -- Remove the point
        table.remove(currentPoints, index)
        
        -- Set the modified curve
        DevelopModule.setCurvePoints({
            param = param,
            points = currentPoints
        }, callback)
    end)
end

-- PointColors Helper APIs --

-- Create a green color enhancement swatch (validated working pattern)
function DevelopModule.createGreenSwatch(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    -- Parse parameters with defaults
    local saturationBoost = (params and params.saturationBoost) or 0
    local luminanceAdjust = (params and params.luminanceAdjust) or 0
    local hueShift = (params and params.hueShift) or -0.1  -- Default slight blue-green shift
    local rangeWidth = (params and params.rangeWidth) or "normal"
    
    logger:debug("Creating green enhancement swatch with satBoost: " .. saturationBoost .. ", lumAdjust: " .. luminanceAdjust)
    
    -- Range width presets - using validated patterns that work
    local satRange, lumRange
    if rangeWidth == "tight" then
        satRange = {LowerNone = 0.3, LowerFull = 0.35, UpperFull = 0.65, UpperNone = 0.7}
        -- For SrcLum = 0.6, UpperFull must be >= 0.798, so use 0.85 to be safe
        lumRange = {LowerNone = 0.35, LowerFull = 0.4, UpperFull = 0.85, UpperNone = 0.9}
    elseif rangeWidth == "wide" then
        satRange = {LowerNone = 0.1, LowerFull = 0.2, UpperFull = 0.8, UpperNone = 0.9}
        lumRange = {LowerNone = 0.3, LowerFull = 0.35, UpperFull = 0.9, UpperNone = 1.0}
    else -- normal - use the exact working pattern from our tests
        satRange = {LowerNone = 0.2, LowerFull = 0.3, UpperFull = 0.7, UpperNone = 0.8}
        lumRange = {LowerNone = 0.35, LowerFull = 0.35, UpperFull = 0.85, UpperNone = 0.85}
    end
    
    -- Create green swatch with validated working pattern
    local greenSwatch = {
        SrcHue = 2.0,      -- Green on 0-6 scale
        SrcSat = 0.5,      -- Medium saturation
        SrcLum = 0.6,      -- Bright
        HueShift = hueShift,
        SatScale = saturationBoost,
        LumScale = luminanceAdjust,
        RangeAmount = 1.0,
        HueRange = {
            LowerNone = 0.0,
            LowerFull = 0.0,
            UpperFull = 0.75,
            UpperNone = 1.0
        },
        SatRange = satRange,
        LumRange = lumRange
    }
    
    -- Get current PointColors and append
    local success, currentValue = ErrorUtils.safeCall(function()
        return LrDevelopController.getValue("PointColors")
    end)
    
    local swatches = {}
    if success and type(currentValue) == "table" then
        swatches = currentValue
    end
    
    -- Add our green swatch
    table.insert(swatches, greenSwatch)
    
    -- Apply the updated swatches
    local setSuccess, setError = ErrorUtils.safeCall(function()
        LrDevelopController.setValue("PointColors", swatches)
    end)
    
    if setSuccess then
        callback({
            success = true,
            result = {
                message = "Green enhancement swatch created",
                swatchCount = #swatches,
                swatch = greenSwatch
            }
        })
    else
        callback({
            error = {
                code = "SWATCH_CREATION_FAILED",
                message = "Failed to create green swatch: " .. tostring(setError)
            }
        })
    end
end

-- Create a cyan color correction swatch (validated working pattern)
function DevelopModule.createCyanSwatch(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    -- Parse parameters with defaults
    local saturationBoost = (params and params.saturationBoost) or 0.2  -- Default boost
    local luminanceAdjust = (params and params.luminanceAdjust) or 0
    local hueShift = (params and params.hueShift) or 0
    local rangeWidth = (params and params.rangeWidth) or "normal"
    
    logger:debug("Creating cyan correction swatch with satBoost: " .. saturationBoost)
    
    -- Range width presets for cyan
    local satRange, lumRange
    if rangeWidth == "tight" then
        satRange = {LowerNone = 0.25, LowerFull = 0.3, UpperFull = 0.5, UpperNone = 0.55}
        lumRange = {LowerNone = 0.0, LowerFull = 0.0, UpperFull = 0.75, UpperNone = 0.85}
    elseif rangeWidth == "wide" then
        satRange = {LowerNone = 0.05, LowerFull = 0.1, UpperFull = 0.7, UpperNone = 0.8}
        lumRange = {LowerNone = 0.0, LowerFull = 0.0, UpperFull = 0.9, UpperNone = 1.0}
    else -- normal
        satRange = {LowerNone = 0.1, LowerFull = 0.2, UpperFull = 0.6, UpperNone = 0.7}
        lumRange = {LowerNone = 0.0, LowerFull = 0.0, UpperFull = 0.85, UpperNone = 1.0}
    end
    
    -- Create cyan swatch with validated working pattern
    local cyanSwatch = {
        SrcHue = 3.0,      -- Cyan on 0-6 scale
        SrcSat = 0.4,      -- Medium-low saturation
        SrcLum = 0.5,      -- Mid luminance
        HueShift = hueShift,
        SatScale = saturationBoost,
        LumScale = luminanceAdjust,
        RangeAmount = 1.0,
        HueRange = {
            LowerNone = 0.3,
            LowerFull = 0.4,
            UpperFull = 0.6,
            UpperNone = 0.7
        },
        SatRange = satRange,
        LumRange = lumRange
    }
    
    -- Get current PointColors and append
    local success, currentValue = ErrorUtils.safeCall(function()
        return LrDevelopController.getValue("PointColors")
    end)
    
    local swatches = {}
    if success and type(currentValue) == "table" then
        swatches = currentValue
    end
    
    -- Add our cyan swatch
    table.insert(swatches, cyanSwatch)
    
    -- Apply the updated swatches
    local setSuccess, setError = ErrorUtils.safeCall(function()
        LrDevelopController.setValue("PointColors", swatches)
    end)
    
    if setSuccess then
        callback({
            success = true,
            result = {
                message = "Cyan correction swatch created",
                swatchCount = #swatches,
                swatch = cyanSwatch
            }
        })
    else
        callback({
            error = {
                code = "SWATCH_CREATION_FAILED",
                message = "Failed to create cyan swatch: " .. tostring(setError)
            }
        })
    end
end

-- Apply color enhancement presets
function DevelopModule.enhanceColors(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local preset = (params and params.preset) or "natural"
    local preserveExisting = (params and params.preserveExisting) == true
    
    logger:debug("Applying color enhancement preset: " .. preset)
    
    -- Get current PointColors if preserving
    local existingSwatches = {}
    if preserveExisting then
        local success, currentValue = ErrorUtils.safeCall(function()
            return LrDevelopController.getValue("PointColors")
        end)
        if success and type(currentValue) == "table" then
            existingSwatches = currentValue
        end
    end
    
    local swatches = {}
    
    -- Define preset patterns
    if preset == "vibrant" then
        -- Enhance greens and blues for landscape
        swatches = {
            -- Vibrant greens
            {
                SrcHue = 2.0, SrcSat = 0.5, SrcLum = 0.6,
                HueShift = -0.15, SatScale = 0.3, LumScale = 0.1,
                RangeAmount = 1.0,
                HueRange = {LowerNone = 0.0, LowerFull = 0.0, UpperFull = 0.75, UpperNone = 1.0},
                SatRange = {LowerNone = 0.2, LowerFull = 0.3, UpperFull = 0.7, UpperNone = 0.8},
                LumRange = {LowerNone = 0.35, LowerFull = 0.35, UpperFull = 0.85, UpperNone = 0.85}
            },
            -- Enhanced cyan/blues
            {
                SrcHue = 3.0, SrcSat = 0.4, SrcLum = 0.5,
                HueShift = 0.0, SatScale = 0.25, LumScale = 0.05,
                RangeAmount = 1.0,
                HueRange = {LowerNone = 0.3, LowerFull = 0.4, UpperFull = 0.6, UpperNone = 0.7},
                SatRange = {LowerNone = 0.1, LowerFull = 0.2, UpperFull = 0.6, UpperNone = 0.7},
                LumRange = {LowerNone = 0.0, LowerFull = 0.0, UpperFull = 0.85, UpperNone = 1.0}
            }
        }
    elseif preset == "muted" then
        -- Desaturate for film look
        swatches = {
            -- Muted greens
            {
                SrcHue = 2.0, SrcSat = 0.5, SrcLum = 0.6,
                HueShift = 0.1, SatScale = -0.2, LumScale = -0.05,
                RangeAmount = 0.8,
                HueRange = {LowerNone = 0.0, LowerFull = 0.0, UpperFull = 0.75, UpperNone = 1.0},
                SatRange = {LowerNone = 0.15, LowerFull = 0.25, UpperFull = 0.75, UpperNone = 0.85},
                LumRange = {LowerNone = 0.35, LowerFull = 0.4, UpperFull = 0.85, UpperNone = 0.9}
            }
        }
    elseif preset == "autumn" then
        -- Warm up greens to golden
        swatches = {
            -- Warmer greens
            {
                SrcHue = 2.0, SrcSat = 0.5, SrcLum = 0.6,
                HueShift = 0.3, SatScale = 0.1, LumScale = 0.05,
                RangeAmount = 1.0,
                HueRange = {LowerNone = 0.0, LowerFull = 0.0, UpperFull = 0.75, UpperNone = 1.0},
                SatRange = {LowerNone = 0.2, LowerFull = 0.3, UpperFull = 0.7, UpperNone = 0.8},
                LumRange = {LowerNone = 0.35, LowerFull = 0.35, UpperFull = 0.85, UpperNone = 0.85}
            }
        }
    else -- natural (default)
        -- Subtle enhancements using validated ranges
        swatches = {
            -- Natural greens
            {
                SrcHue = 2.0, SrcSat = 0.5, SrcLum = 0.6,
                HueShift = -0.05, SatScale = 0.05, LumScale = 0.0,
                RangeAmount = 0.7,
                HueRange = {LowerNone = 0.0, LowerFull = 0.0, UpperFull = 0.75, UpperNone = 1.0},
                SatRange = {LowerNone = 0.25, LowerFull = 0.35, UpperFull = 0.65, UpperNone = 0.75},
                LumRange = {LowerNone = 0.35, LowerFull = 0.35, UpperFull = 0.85, UpperNone = 0.85}
            }
        }
    end
    
    -- Combine with existing if preserving
    if preserveExisting then
        for _, existingSwatch in ipairs(existingSwatches) do
            table.insert(swatches, existingSwatch)
        end
    end
    
    -- Apply the swatches
    local setSuccess, setError = ErrorUtils.safeCall(function()
        LrDevelopController.setValue("PointColors", swatches)
    end)
    
    if setSuccess then
        callback({
            success = true,
            result = {
                message = "Color enhancement preset '" .. preset .. "' applied",
                preset = preset,
                swatchCount = #swatches,
                preservedExisting = preserveExisting
            }
        })
    else
        callback({
            error = {
                code = "PRESET_APPLICATION_FAILED",
                message = "Failed to apply color preset: " .. tostring(setError)
            }
        })
    end
end

-- ========================================
-- MASKING FUNCTIONS (Phase 4 Implementation)
-- ========================================

-- Core masking navigation and state
function DevelopModule.goToMasking(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local success, result = ErrorUtils.safeCall(function()
        LrDevelopController.goToMasking()
        return {
            message = "Masking panel opened",
            success = true
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "MASKING_NAVIGATION_FAILED",
                message = "Failed to open masking panel: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.toggleOverlay(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local success, result = ErrorUtils.safeCall(function()
        LrDevelopController.toggleOverlay()
        return {
            message = "Mask overlay toggled",
            success = true
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "OVERLAY_TOGGLE_FAILED",
                message = "Failed to toggle mask overlay: " .. tostring(result)
            }
        })
    end
end

-- Tool selection functions
function DevelopModule.selectTool(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local tool = params.tool
    
    if not tool then
        callback({
            error = {
                code = "MISSING_TOOL_PARAMETER",
                message = "Tool parameter is required"
            }
        })
        return
    end
    
    local success, result = ErrorUtils.safeCall(function()
        LrDevelopController.selectTool(tool)
        return {
            message = "Tool '" .. tool .. "' selected",
            tool = tool,
            success = true
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "TOOL_SELECTION_FAILED",
                message = "Failed to select tool '" .. tostring(tool) .. "': " .. tostring(result)
            }
        })
    end
end

-- Mask management functions
function DevelopModule.getAllMasks(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local success, result = ErrorUtils.safeCall(function()
        local masks = LrDevelopController.getAllMasks()
        return {
            masks = masks or {},
            count = masks and #masks or 0,
            message = "Retrieved all masks"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "GET_MASKS_FAILED",
                message = "Failed to get masks: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.getSelectedMask(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local success, result = ErrorUtils.safeCall(function()
        local selectedMask = LrDevelopController.getSelectedMask()
        return {
            selectedMask = selectedMask,
            message = "Retrieved selected mask"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "GET_SELECTED_MASK_FAILED",
                message = "Failed to get selected mask: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.createNewMask(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local maskType = params.maskType or "brush"
    local maskSubtype = params.maskSubtype
    
    local success, result = ErrorUtils.safeCall(function()
        local maskId
        if maskSubtype then
            maskId = LrDevelopController.createNewMask(maskType, maskSubtype)
        else
            maskId = LrDevelopController.createNewMask(maskType)
        end
        
        return {
            maskId = maskId,
            maskType = maskType,
            maskSubtype = maskSubtype,
            message = "Created new mask of type '" .. maskType .. "'"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "CREATE_MASK_FAILED",
                message = "Failed to create mask: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.selectMask(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local maskId = params.maskId
    local param = params.param
    
    if not maskId then
        callback({
            error = {
                code = "MISSING_MASK_ID",
                message = "Mask ID is required"
            }
        })
        return
    end
    
    local success, result = ErrorUtils.safeCall(function()
        if param then
            LrDevelopController.selectMask(maskId, param)
        else
            LrDevelopController.selectMask(maskId)
        end
        
        return {
            maskId = maskId,
            param = param,
            message = "Selected mask " .. tostring(maskId)
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "SELECT_MASK_FAILED",
                message = "Failed to select mask: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.deleteMask(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local maskId = params.maskId
    local param = params.param
    
    if not maskId then
        callback({
            error = {
                code = "MISSING_MASK_ID",
                message = "Mask ID is required"
            }
        })
        return
    end
    
    local success, result = ErrorUtils.safeCall(function()
        if param then
            LrDevelopController.deleteMask(maskId, param)
        else
            LrDevelopController.deleteMask(maskId)
        end
        
        return {
            maskId = maskId,
            param = param,
            message = "Deleted mask " .. tostring(maskId)
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "DELETE_MASK_FAILED",
                message = "Failed to delete mask: " .. tostring(result)
            }
        })
    end
end

-- Mask tool management
function DevelopModule.getSelectedMaskTool(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local success, result = ErrorUtils.safeCall(function()
        local selectedTool = LrDevelopController.getSelectedMaskTool()
        return {
            selectedTool = selectedTool,
            message = "Retrieved selected mask tool"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "GET_SELECTED_TOOL_FAILED",
                message = "Failed to get selected mask tool: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.selectMaskTool(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local toolId = params.toolId
    local param = params.param
    
    if not toolId then
        callback({
            error = {
                code = "MISSING_TOOL_ID",
                message = "Tool ID is required"
            }
        })
        return
    end
    
    local success, result = ErrorUtils.safeCall(function()
        if param then
            LrDevelopController.selectMaskTool(toolId, param)
        else
            LrDevelopController.selectMaskTool(toolId)
        end
        
        return {
            toolId = toolId,
            param = param,
            message = "Selected mask tool " .. tostring(toolId)
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "SELECT_MASK_TOOL_FAILED",
                message = "Failed to select mask tool: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.deleteMaskTool(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local toolId = params.toolId
    local param = params.param
    
    if not toolId then
        callback({
            error = {
                code = "MISSING_TOOL_ID",
                message = "Tool ID is required"
            }
        })
        return
    end
    
    local success, result = ErrorUtils.safeCall(function()
        if param then
            LrDevelopController.deleteMaskTool(toolId, param)
        else
            LrDevelopController.deleteMaskTool(toolId)
        end
        
        return {
            toolId = toolId,
            param = param,
            message = "Deleted mask tool " .. tostring(toolId)
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "DELETE_MASK_TOOL_FAILED",
                message = "Failed to delete mask tool: " .. tostring(result)
            }
        })
    end
end

-- Mask operations and boolean logic
function DevelopModule.addToCurrentMask(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local maskType = params.maskType or "brush"
    local maskSubtype = params.maskSubtype
    
    local success, result = ErrorUtils.safeCall(function()
        local toolId
        if maskSubtype then
            toolId = LrDevelopController.addToCurrentMask(maskType, maskSubtype)
        else
            toolId = LrDevelopController.addToCurrentMask(maskType)
        end
        
        return {
            toolId = toolId,
            maskType = maskType,
            maskSubtype = maskSubtype,
            operation = "add",
            message = "Added " .. maskType .. " to current mask"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "ADD_TO_MASK_FAILED",
                message = "Failed to add to current mask: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.intersectWithCurrentMask(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local maskType = params.maskType or "brush"
    local maskSubtype = params.maskSubtype
    
    local success, result = ErrorUtils.safeCall(function()
        local toolId
        if maskSubtype then
            toolId = LrDevelopController.intersectWithCurrentMask(maskType, maskSubtype)
        else
            toolId = LrDevelopController.intersectWithCurrentMask(maskType)
        end
        
        return {
            toolId = toolId,
            maskType = maskType,
            maskSubtype = maskSubtype,
            operation = "intersect",
            message = "Intersected " .. maskType .. " with current mask"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "INTERSECT_MASK_FAILED",
                message = "Failed to intersect with current mask: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.subtractFromCurrentMask(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local maskType = params.maskType or "brush"
    local maskSubtype = params.maskSubtype
    
    local success, result = ErrorUtils.safeCall(function()
        local toolId
        if maskSubtype then
            toolId = LrDevelopController.subtractFromCurrentMask(maskType, maskSubtype)
        else
            toolId = LrDevelopController.subtractFromCurrentMask(maskType)
        end
        
        return {
            toolId = toolId,
            maskType = maskType,
            maskSubtype = maskSubtype,
            operation = "subtract",
            message = "Subtracted " .. maskType .. " from current mask"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "SUBTRACT_FROM_MASK_FAILED",
                message = "Failed to subtract from current mask: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.invertMask(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local maskId = params.maskId
    local param = params.param
    
    if not maskId then
        callback({
            error = {
                code = "MISSING_MASK_ID",
                message = "Mask ID is required"
            }
        })
        return
    end
    
    local success, result = ErrorUtils.safeCall(function()
        if param then
            LrDevelopController.invertMask(maskId, param)
        else
            LrDevelopController.invertMask(maskId)
        end
        
        return {
            maskId = maskId,
            param = param,
            message = "Inverted mask " .. tostring(maskId)
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "INVERT_MASK_FAILED",
                message = "Failed to invert mask: " .. tostring(result)
            }
        })
    end
end

-- Legacy tool reset functions (for backward compatibility)
function DevelopModule.resetGradient(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local success, result = ErrorUtils.safeCall(function()
        LrDevelopController.resetGradient()
        return {
            message = "Reset all gradient filters",
            tool = "gradient"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "RESET_GRADIENT_FAILED",
                message = "Failed to reset gradient filters: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.resetCircularGradient(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local success, result = ErrorUtils.safeCall(function()
        LrDevelopController.resetCircularGradient()
        return {
            message = "Reset all radial filters",
            tool = "circularGradient"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "RESET_RADIAL_FAILED",
                message = "Failed to reset radial filters: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.resetBrushing(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local success, result = ErrorUtils.safeCall(function()
        LrDevelopController.resetBrushing()
        return {
            message = "Reset all brush adjustments",
            tool = "localized"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "RESET_BRUSHING_FAILED",
                message = "Failed to reset brush adjustments: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.resetMasking(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local success, result = ErrorUtils.safeCall(function()
        LrDevelopController.resetMasking()
        return {
            message = "Reset all masks from current photo"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "RESET_MASKING_FAILED",
                message = "Failed to reset masking: " .. tostring(result)
            }
        })
    end
end

-- ========================================
-- HELPER FUNCTIONS FOR COMMON MASKING WORKFLOWS
-- ========================================

function DevelopModule.createGraduatedFilter(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local success, result = ErrorUtils.safeCall(function()
        -- Create a new graduated filter mask
        local maskId = LrDevelopController.createNewMask("gradient")
        
        return {
            maskId = maskId,
            maskType = "gradient",
            message = "Created graduated filter mask"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "CREATE_GRADIENT_FAILED",
                message = "Failed to create graduated filter: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.createRadialFilter(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local success, result = ErrorUtils.safeCall(function()
        -- Create a new radial filter mask
        local maskId = LrDevelopController.createNewMask("radialGradient")
        
        return {
            maskId = maskId,
            maskType = "radialGradient",
            message = "Created radial filter mask"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "CREATE_RADIAL_FAILED",
                message = "Failed to create radial filter: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.createAdjustmentBrush(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local success, result = ErrorUtils.safeCall(function()
        -- Create a new adjustment brush mask
        local maskId = LrDevelopController.createNewMask("brush")
        
        return {
            maskId = maskId,
            maskType = "brush",
            message = "Created adjustment brush mask"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "CREATE_BRUSH_FAILED",
                message = "Failed to create adjustment brush: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.createAISelectionMask(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local selectionType = params.selectionType or "subject"
    
    -- Validate selection type
    local validTypes = {"subject", "sky", "background", "objects", "people", "landscape"}
    local isValid = false
    for _, validType in ipairs(validTypes) do
        if selectionType == validType then
            isValid = true
            break
        end
    end
    
    if not isValid then
        callback({
            error = {
                code = "INVALID_SELECTION_TYPE",
                message = "Selection type must be one of: " .. table.concat(validTypes, ", ")
            }
        })
        return
    end
    
    local success, result = ErrorUtils.safeCall(function()
        -- Create a new AI selection mask
        local maskId = LrDevelopController.createNewMask("aiSelection", selectionType)
        
        return {
            maskId = maskId,
            maskType = "aiSelection",
            maskSubtype = selectionType,
            message = "Created AI selection mask for " .. selectionType
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "CREATE_AI_SELECTION_FAILED",
                message = "Failed to create AI selection mask: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.createRangeMask(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local rangeType = params.rangeType or "luminance"
    
    -- Validate range type
    local validTypes = {"luminance", "color", "depth"}
    local isValid = false
    for _, validType in ipairs(validTypes) do
        if rangeType == validType then
            isValid = true
            break
        end
    end
    
    if not isValid then
        callback({
            error = {
                code = "INVALID_RANGE_TYPE",
                message = "Range type must be one of: " .. table.concat(validTypes, ", ")
            }
        })
        return
    end
    
    local success, result = ErrorUtils.safeCall(function()
        -- Create a new range mask
        local maskId = LrDevelopController.createNewMask("rangeMask", rangeType)
        
        return {
            maskId = maskId,
            maskType = "rangeMask",
            maskSubtype = rangeType,
            message = "Created range mask for " .. rangeType .. " selection"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "CREATE_RANGE_MASK_FAILED",
                message = "Failed to create range mask: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.createComplexMask(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local workflow = params.workflow or "subject_with_luminance"
    
    local success, result = ErrorUtils.safeCall(function()
        local maskIds = {}
        local operations = {}
        
        if workflow == "subject_with_luminance" then
            -- Create AI subject selection
            local subjectMaskId = LrDevelopController.createNewMask("aiSelection", "subject")
            table.insert(maskIds, subjectMaskId)
            table.insert(operations, "Created AI subject selection")
            
            -- Add luminance range to refine the selection
            local luminanceMaskId = LrDevelopController.addToCurrentMask("rangeMask", "luminance")
            table.insert(maskIds, luminanceMaskId)
            table.insert(operations, "Added luminance range refinement")
            
        elseif workflow == "sky_with_color" then
            -- Create AI sky selection
            local skyMaskId = LrDevelopController.createNewMask("aiSelection", "sky")
            table.insert(maskIds, skyMaskId)
            table.insert(operations, "Created AI sky selection")
            
            -- Intersect with color range for specific sky colors
            local colorMaskId = LrDevelopController.intersectWithCurrentMask("rangeMask", "color")
            table.insert(maskIds, colorMaskId)
            table.insert(operations, "Intersected with color range")
            
        elseif workflow == "foreground_background_separation" then
            -- Create subject mask
            local subjectMaskId = LrDevelopController.createNewMask("aiSelection", "subject")
            table.insert(maskIds, subjectMaskId)
            table.insert(operations, "Created subject mask")
            
            -- Create inverted background mask
            local backgroundMaskId = LrDevelopController.createNewMask("aiSelection", "background")
            table.insert(maskIds, backgroundMaskId)
            table.insert(operations, "Created background mask")
            
        else
            return {
                error = "Unknown workflow: " .. workflow
            }
        end
        
        return {
            workflow = workflow,
            maskIds = maskIds,
            operations = operations,
            message = "Created complex mask using workflow: " .. workflow
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "CREATE_COMPLEX_MASK_FAILED",
                message = "Failed to create complex mask: " .. tostring(result)
            }
        })
    end
end

-- ========================================
-- LOCAL ADJUSTMENT PARAMETER FUNCTIONS
-- ========================================

function DevelopModule.activateMaskingMode(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local success, result = ErrorUtils.safeCall(function()
        -- Switch to masking tool to enable local parameter access
        LrDevelopController.selectTool("masking")
        
        return {
            message = "Masking mode activated - local parameters now accessible",
            tool = "masking"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "MASKING_MODE_FAILED",
                message = "Failed to activate masking mode: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.getLocalValue(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local param = params.param
    local maskId = params.maskId
    
    if not param then
        callback({
            error = {
                code = "MISSING_PARAMETER",
                message = "Parameter name is required"
            }
        })
        return
    end
    
    local success, result = ErrorUtils.safeCall(function()
        -- Ensure masking tool is active
        LrDevelopController.selectTool("masking")
        
        -- Select specific mask if provided
        if maskId then
            LrDevelopController.selectMask(maskId)
        end
        
        -- Get the parameter value
        local value = LrDevelopController.getValue(param)
        local min, max = LrDevelopController.getRange(param)
        
        return {
            param = param,
            value = value,
            min = min,
            max = max,
            maskId = maskId,
            message = "Retrieved local parameter value"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "GET_LOCAL_VALUE_FAILED",
                message = "Failed to get local parameter value: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.setLocalValue(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local param = params.param
    local value = params.value
    local maskId = params.maskId
    
    if not param then
        callback({
            error = {
                code = "MISSING_PARAMETER",
                message = "Parameter name is required"
            }
        })
        return
    end
    
    if value == nil then
        callback({
            error = {
                code = "MISSING_VALUE",
                message = "Parameter value is required"
            }
        })
        return
    end
    
    local success, result = ErrorUtils.safeCall(function()
        -- Ensure masking tool is active
        LrDevelopController.selectTool("masking")
        
        -- Select specific mask if provided
        if maskId then
            LrDevelopController.selectMask(maskId)
        end
        
        -- Set the parameter value
        LrDevelopController.setValue(param, value)
        
        return {
            param = param,
            value = value,
            maskId = maskId,
            message = "Set local parameter value"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "SET_LOCAL_VALUE_FAILED",
                message = "Failed to set local parameter value: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.applyLocalSettings(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local settings = params.settings
    local maskId = params.maskId
    
    if not settings or type(settings) ~= "table" then
        callback({
            error = {
                code = "MISSING_SETTINGS",
                message = "Settings table is required"
            }
        })
        return
    end
    
    local success, result = ErrorUtils.safeCall(function()
        -- Ensure masking tool is active
        LrDevelopController.selectTool("masking")
        
        -- Select specific mask if provided
        if maskId then
            LrDevelopController.selectMask(maskId)
        end
        
        -- Apply each setting
        local appliedSettings = {}
        local errors = {}
        
        for param, value in pairs(settings) do
            local settingSuccess, settingError = ErrorUtils.safeCall(function()
                LrDevelopController.setValue(param, value)
            end)
            
            if settingSuccess then
                appliedSettings[param] = value
            else
                errors[param] = tostring(settingError)
            end
        end
        
        return {
            appliedSettings = appliedSettings,
            errors = next(errors) and errors or nil,
            maskId = maskId,
            settingCount = #appliedSettings,
            message = "Applied " .. #appliedSettings .. " local settings"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "APPLY_LOCAL_SETTINGS_FAILED",
                message = "Failed to apply local settings: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.getAvailableLocalParameters(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local success, result = ErrorUtils.safeCall(function()
        -- Ensure masking tool is active
        LrDevelopController.selectTool("masking")
        
        -- List of potential local parameters to test
        local potentialParams = {
            -- Basic adjustments
            "local_Temperature", "local_Tint",
            "local_Exposure", "local_Contrast",
            "local_Highlights", "local_Shadows",
            "local_Whites", "local_Blacks",
            
            -- Creative adjustments
            "local_Clarity", "local_Texture", "local_Dehaze",
            "local_Saturation", "local_Vibrance",
            "local_Hue", "local_Amount",
            
            -- Detail & noise
            "local_Sharpness", "local_LuminanceNoise",
            "local_Moire", "local_Defringe",
            
            -- Color grading
            "local_ToningHue", "local_ToningSaturation",
            "local_PointColors",
            
            -- Curves
            "local_Maincurve", "local_Redcurve",
            "local_Greencurve", "local_Bluecurve",
            "local_RefineSaturation",
            
            -- Effects
            "local_Grain"
        }
        
        local availableParams = {}
        local unavailableParams = {}
        
        for _, param in ipairs(potentialParams) do
            local paramSuccess, paramResult = ErrorUtils.safeCall(function()
                local min, max = LrDevelopController.getRange(param)
                return min ~= nil and max ~= nil
            end)
            
            if paramSuccess and paramResult then
                local min, max = LrDevelopController.getRange(param)
                table.insert(availableParams, {
                    param = param,
                    min = min,
                    max = max
                })
            else
                table.insert(unavailableParams, param)
            end
        end
        
        return {
            availableParameters = availableParams,
            unavailableParameters = unavailableParams,
            availableCount = #availableParams,
            totalTested = #potentialParams,
            message = "Found " .. #availableParams .. " available local parameters"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "GET_AVAILABLE_PARAMS_FAILED",
                message = "Failed to get available local parameters: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.createMaskWithLocalAdjustments(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local maskType = params.maskType or "brush"
    local maskSubtype = params.maskSubtype
    local localSettings = params.localSettings or {}
    
    local success, result = ErrorUtils.safeCall(function()
        -- Ensure masking tool is active
        LrDevelopController.selectTool("masking")
        
        -- Create the mask
        local maskId
        if maskSubtype then
            maskId = LrDevelopController.createNewMask(maskType, maskSubtype)
        else
            maskId = LrDevelopController.createNewMask(maskType)
        end
        
        -- Select the newly created mask
        if maskId then
            LrDevelopController.selectMask(maskId)
        end
        
        -- Apply local settings to the mask
        local appliedSettings = {}
        local errors = {}
        
        for param, value in pairs(localSettings) do
            local settingSuccess, settingError = ErrorUtils.safeCall(function()
                LrDevelopController.setValue(param, value)
            end)
            
            if settingSuccess then
                appliedSettings[param] = value
            else
                errors[param] = tostring(settingError)
            end
        end
        
        return {
            maskId = maskId,
            maskType = maskType,
            maskSubtype = maskSubtype,
            appliedSettings = appliedSettings,
            errors = next(errors) and errors or nil,
            settingCount = #appliedSettings,
            message = "Created mask with " .. #appliedSettings .. " local adjustments"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "CREATE_MASK_WITH_LOCALS_FAILED",
                message = "Failed to create mask with local adjustments: " .. tostring(result)
            }
        })
    end
end

-- ========================================
-- REVERSE ENGINEERING / INTROSPECTION FUNCTIONS
-- ========================================

function DevelopModule.dumpLrDevelopController(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local success, result = ErrorUtils.safeCall(function()
        local functions = {}
        local properties = {}
        local unknownItems = {}
        
        -- Iterate through all items in LrDevelopController
        for key, value in pairs(LrDevelopController) do
            local valueType = type(value)
            
            if valueType == "function" then
                -- Try to get function info
                local funcInfo = ""
                local debugSuccess, debugInfo = ErrorUtils.safeCall(debug.getinfo, value)
                if debugSuccess and debugInfo then
                    funcInfo = string.format("(%s:%d)", debugInfo.source or "unknown", debugInfo.linedefined or 0)
                end
                
                table.insert(functions, {
                    name = key,
                    type = "function",
                    info = funcInfo,
                    string = tostring(value)
                })
            elseif valueType == "table" then
                table.insert(properties, {
                    name = key,
                    type = "table",
                    string = tostring(value)
                })
            else
                table.insert(unknownItems, {
                    name = key,
                    type = valueType,
                    value = value,
                    string = tostring(value)
                })
            end
        end
        
        -- Sort for easier reading
        table.sort(functions, function(a, b) return a.name < b.name end)
        table.sort(properties, function(a, b) return a.name < b.name end)
        table.sort(unknownItems, function(a, b) return a.name < b.name end)
        
        return {
            functions = functions,
            properties = properties,
            unknownItems = unknownItems,
            functionCount = #functions,
            propertyCount = #properties,
            unknownCount = #unknownItems,
            message = "Dumped LrDevelopController: " .. #functions .. " functions, " .. #properties .. " properties"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "DUMP_CONTROLLER_FAILED",
                message = "Failed to dump LrDevelopController: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.discoverGradientParameters(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local success, result = ErrorUtils.safeCall(function()
        -- List of potential gradient-related parameter names to test
        local gradientParams = {
            -- Position parameters
            "gradientStartX", "gradientStartY", "gradientEndX", "gradientEndY",
            "gradientCenterX", "gradientCenterY", "gradientAngle", "gradientRotation",
            "gradientLength", "gradientWidth", "gradientRadius",
            
            -- Gradient tool parameters  
            "GradientStartX", "GradientStartY", "GradientEndX", "GradientEndY",
            "GradientAngle", "GradientLength", "GradientFeather", "GradientCenter",
            
            -- Alternative naming patterns
            "linearGradientStart", "linearGradientEnd", "linearGradientAngle",
            "maskGradientX1", "maskGradientY1", "maskGradientX2", "maskGradientY2",
            
            -- Tool-specific parameters
            "tool_gradient_start", "tool_gradient_end", "tool_gradient_angle",
            "local_gradient_x", "local_gradient_y", "local_gradient_rotation",
            
            -- Legacy gradient parameters
            "GraduatedFilterAngle", "GraduatedFilterStart", "GraduatedFilterEnd",
            "gradFilter_angle", "gradFilter_startX", "gradFilter_startY",
            "gradFilter_endX", "gradFilter_endY",
            
            -- Geometric transform parameters
            "transformX", "transformY", "transformAngle", "transformScale",
            "maskTransformX", "maskTransformY", "maskTransformAngle"
        }
        
        local availableParams = {}
        local unavailableParams = {}
        
        for _, param in ipairs(gradientParams) do
            local paramSuccess, paramValue = ErrorUtils.safeCall(function()
                local min, max = LrDevelopController.getRange(param)
                if min ~= nil and max ~= nil then
                    local value = LrDevelopController.getValue(param)
                    return {
                        hasRange = true,
                        min = min,
                        max = max,
                        value = value
                    }
                else
                    return nil
                end
            end)
            
            if paramSuccess and paramValue then
                table.insert(availableParams, {
                    param = param,
                    min = paramValue.min,
                    max = paramValue.max,
                    value = paramValue.value
                })
            else
                table.insert(unavailableParams, param)
            end
        end
        
        return {
            availableParameters = availableParams,
            unavailableParameters = unavailableParams,
            availableCount = #availableParams,
            totalTested = #gradientParams,
            message = "Discovered " .. #availableParams .. " potential gradient parameters"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "DISCOVER_GRADIENT_PARAMS_FAILED",
                message = "Failed to discover gradient parameters: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.monitorParameterChanges(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local duration = params.duration or 10  -- Monitor for 10 seconds by default
    
    local success, result = ErrorUtils.safeCall(function()
        -- Get baseline parameter values
        local baselineParams = {}
        local testParams = {
            -- Global parameters that might change during gradient manipulation
            "Exposure", "Temperature", "Tint", "Contrast", "Highlights", "Shadows",
            
            -- Local parameters
            "local_Exposure", "local_Temperature", "local_Contrast",
            
            -- Potential gradient parameters (expanded list)
            "gradientAngle", "gradientStartX", "gradientStartY", "gradientEndX", "gradientEndY",
            "GradientAngle", "gradientLength", "gradientFeather", "gradientCenter",
            "transformX", "transformY", "transformAngle", "maskTransformX", "maskTransformY"
        }
        
        -- Record baseline values
        for _, param in ipairs(testParams) do
            local paramSuccess, value = ErrorUtils.safeCall(function()
                return LrDevelopController.getValue(param)
            end)
            if paramSuccess and value ~= nil then
                baselineParams[param] = value
            end
        end
        
        return {
            monitoringStarted = true,
            duration = duration,
            baselineParams = baselineParams,
            baselineCount = #baselineParams,
            message = "Started monitoring " .. #baselineParams .. " parameters for " .. duration .. " seconds"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "MONITOR_PARAMS_FAILED",
                message = "Failed to start parameter monitoring: " .. tostring(result)
            }
        })
    end
end

function DevelopModule.probeAllDevelopParameters(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local success, result = ErrorUtils.safeCall(function()
        local allParams = {}
        local errorParams = {}
        
        -- Generate comprehensive list of parameter patterns to test
        local parameterPatterns = {}
        
        -- Basic parameter variations
        local baseNames = {"gradient", "Gradient", "linear", "Linear", "mask", "Mask", "tool", "Tool"}
        local properties = {"X", "Y", "StartX", "StartY", "EndX", "EndY", "Angle", "Length", "Width", "Center", "Feather", "Radius"}
        
        for _, base in ipairs(baseNames) do
            for _, prop in ipairs(properties) do
                table.insert(parameterPatterns, base .. prop)
                table.insert(parameterPatterns, base .. "_" .. prop)
                table.insert(parameterPatterns, base .. prop:lower())
            end
        end
        
        -- Test each pattern
        for _, param in ipairs(parameterPatterns) do
            local paramSuccess, paramInfo = ErrorUtils.safeCall(function()
                local min, max = LrDevelopController.getRange(param)
                if min ~= nil and max ~= nil then
                    local value = LrDevelopController.getValue(param)
                    return {
                        param = param,
                        min = min,
                        max = max,
                        value = value,
                        found = true
                    }
                end
                return nil
            end)
            
            if paramSuccess and paramInfo then
                table.insert(allParams, paramInfo)
            else
                table.insert(errorParams, param)
            end
        end
        
        return {
            foundParameters = allParams,
            testedParameters = parameterPatterns,
            foundCount = #allParams,
            totalTested = #parameterPatterns,
            message = "Probed " .. #parameterPatterns .. " parameters, found " .. #allParams .. " valid ones"
        }
    end)
    
    if success then
        callback({
            success = true,
            result = result
        })
    else
        callback({
            error = {
                code = "PROBE_PARAMS_FAILED",
                message = "Failed to probe parameters: " .. tostring(result)
            }
        })
    end
end

return DevelopModule