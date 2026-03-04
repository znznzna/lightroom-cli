-- PreviewModule.lua
-- Preview and thumbnail generation API wrapper for Phase 4

-- Lazy imports to avoid loading issues
local LrApplication = nil
local LrTasks = import 'LrTasks'
local LrProgressScope = nil
local LrStringUtils = nil

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
        CODES = { MISSING_PARAM = "MISSING_PARAM" }
    }
end

local ErrorUtils = getErrorUtils()

-- Lazy load Lightroom modules
local function ensureLrModules()
    if not LrApplication then
        LrApplication = import 'LrApplication'
    end
    if not LrProgressScope then
        LrProgressScope = import 'LrProgressScope'
    end
    if not LrStringUtils then
        LrStringUtils = import 'LrStringUtils'
    end
end

-- Get logger from global state (defensive)
local function getLogger()
    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.logger then
        return _G.LightroomPythonBridge.logger
    end
    local LrLogger = import 'LrLogger'
    local logger = LrLogger('PreviewModule')
    logger:enable("logfile")
    return logger
end

local PreviewModule = {}

-- Generate JPEG preview
function PreviewModule.generatePreview(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local photoId = params.photoId
    local size = params.size or "large"  -- small, medium, large, or custom number
    local quality = params.quality or 90
    local format = params.format or "jpeg"
    local base64Encode = params.base64 ~= false  -- default to true
    
    if not photoId then
        callback({
            error = {
                code = "MISSING_PHOTO_ID",
                message = "Photo ID is required"
            }
        })
        return
    end
    
    logger:debug("Generating preview for photo: " .. photoId .. " (size: " .. tostring(size) .. ")")
    
    LrTasks.startAsyncTask(function()
        local catalog = LrApplication.activeCatalog()
        
        catalog:withReadAccessDo(function()
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
        
            local progressScope = LrProgressScope({
            title = "Generating Preview",
            caption = "Preparing preview generation..."
        })
        
        progressScope:setPortionComplete(0.1)
            
            -- Determine pixel size
            local pixelSize
            if size == "small" then
                pixelSize = 240
            elseif size == "medium" then
                pixelSize = 640
            elseif size == "large" then
                pixelSize = 1024
            elseif tonumber(size) then
                pixelSize = tonumber(size)
            else
                callback({
                    error = {
                        code = "INVALID_SIZE",
                        message = "Size must be 'small', 'medium', 'large', or a number"
                    }
                })
                return
            end
            
            progressScope:setCaption("Generating " .. pixelSize .. "px preview...")
            progressScope:setPortionComplete(0.3)
            
            -- Generate preview
            local previewGenerated = false
            local previewError = nil
            local jpegData = nil
            
            photo:requestJpegThumbnail(pixelSize, pixelSize, function(jpg, errorMessage)
                if errorMessage then
                    logger:error("Preview generation error: " .. errorMessage)
                    previewError = errorMessage
                else
                    jpegData = jpg
                    logger:debug("Preview generated successfully, size: " .. string.len(jpg) .. " bytes")
                end
                previewGenerated = true
            end)
            
            -- Wait for async operation to complete
            while not previewGenerated do
                LrTasks.sleep(0.1)
                if progressScope:isCanceled() then
                    logger:info("Preview generation cancelled by user")
                    callback({
                        error = {
                            code = "CANCELLED",
                            message = "Preview generation cancelled by user"
                        }
                    })
                    return
                end
            end
            
            if previewError then
                callback({
                    error = {
                        code = "GENERATION_FAILED",
                        message = "Failed to generate preview: " .. previewError
                    }
                })
                return
            end
            
            if not jpegData then
                callback({
                    error = {
                        code = "NO_DATA",
                        message = "Preview generation returned no data"
                    }
                })
                return
            end
            
            progressScope:setCaption("Processing preview data...")
            progressScope:setPortionComplete(0.8)
            
            -- Check if data is too large for single JSON message (>10MB when base64 encoded)
            local base64Size = math.ceil(string.len(jpegData) * 4 / 3)  -- base64 is ~33% larger
            local useLargeDataTransfer = (base64Size > 10 * 1024 * 1024)  -- 10MB limit
            
            if useLargeDataTransfer then
                -- For large data: return metadata only, client will request chunks separately
                logger:info("Large preview detected (" .. base64Size .. " bytes base64), using chunked transfer")
                
                -- Store preview data globally for chunked retrieval
                if not _G.LightroomPythonBridge.previewCache then
                    _G.LightroomPythonBridge.previewCache = {}
                end
                
                local previewId = photoId .. "_" .. os.time()
                _G.LightroomPythonBridge.previewCache[previewId] = {
                    data = jpegData,
                    base64Encoded = base64Encode,
                    timestamp = os.time(),
                    size = string.len(jpegData)
                }
                
                progressScope:setCaption("Preview prepared for chunked transfer")
                progressScope:setPortionComplete(1.0)
                progressScope:done()
                
                callback({
                    result = {
                        preview = "CHUNKED_TRANSFER",
                        previewId = previewId,
                        chunkSize = 1024 * 1024,  -- 1MB chunks
                        info = {
                            photoId = photoId,
                            size = pixelSize,
                            format = "jpeg",
                            quality = quality,
                            dataSize = string.len(jpegData),
                            base64Encoded = base64Encode,
                            timestamp = os.time(),
                            transferMode = "chunked"
                        }
                    }
                })
            else
                -- Small data: return directly as before
                local previewData = jpegData
                if base64Encode then
                    previewData = LrStringUtils.encodeBase64(jpegData)
                end
                
                progressScope:setCaption("Preview generated successfully")
                progressScope:setPortionComplete(1.0)
                progressScope:done()
                
                logger:info("Generated " .. pixelSize .. "px preview (" .. string.len(jpegData) .. " bytes)")
                
                callback({
                    result = {
                        preview = previewData,
                        info = {
                            photoId = photoId,
                            size = pixelSize,
                            format = "jpeg",
                            quality = quality,
                            dataSize = string.len(jpegData),
                            base64Encoded = base64Encode,
                            timestamp = os.time(),
                            transferMode = "direct"
                        }
                    }
                })
            end
        end)
    end)
end

-- Generate multiple previews (batch operation)
function PreviewModule.generateBatchPreviews(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local photoIds = params.photoIds
    local size = params.size or "medium"
    local quality = params.quality or 90
    local base64Encode = params.base64 ~= false  -- default to true
    
    if not photoIds or type(photoIds) ~= "table" or #photoIds == 0 then
        callback({
            error = {
                code = "MISSING_PHOTO_IDS",
                message = "Photo IDs array is required"
            }
        })
        return
    end
    
    logger:info("Generating batch previews for " .. #photoIds .. " photos")
    
    LrTasks.startAsyncTask(function()
        local catalog = LrApplication.activeCatalog()
        
        catalog:withReadAccessDo(function()
            local results = {}
        
            -- Determine pixel size
        local pixelSize
        if size == "small" then
            pixelSize = 240
        elseif size == "medium" then
            pixelSize = 640
        elseif size == "large" then
            pixelSize = 1024
        elseif tonumber(size) then
            pixelSize = tonumber(size)
        else
            callback({
                error = {
                    code = "INVALID_SIZE",
                    message = "Size must be 'small', 'medium', 'large', or a number"
                }
            })
            return
        end
        
        local progressScope = LrProgressScope({
            title = "Batch Preview Generation",
            caption = "Preparing batch preview generation..."
        })
            
            for i, photoId in ipairs(photoIds) do
                if progressScope:isCanceled() then
                    logger:info("Batch preview generation cancelled by user")
                    break
                end
                
                progressScope:setCaption("Generating preview " .. i .. " of " .. #photoIds)
                progressScope:setPortionComplete(i / #photoIds)
                
                local photo = catalog:getPhotoByLocalId(tonumber(photoId))
                
                if not photo then
                    table.insert(results, {
                        photoId = photoId,
                        success = false,
                        error = "Photo not found"
                    })
                else
                    -- Generate preview for this photo
                    local previewGenerated = false
                    local previewError = nil
                    local jpegData = nil
                    
                    photo:requestJpegThumbnail(pixelSize, pixelSize, function(jpg, errorMessage)
                        if errorMessage then
                            previewError = errorMessage
                        else
                            jpegData = jpg
                        end
                        previewGenerated = true
                    end)
                    
                    -- Wait for async operation
                    while not previewGenerated do
                        LrTasks.sleep(0.1)
                    end
                    
                    if previewError or not jpegData then
                        table.insert(results, {
                            photoId = photoId,
                            success = false,
                            error = previewError or "No data returned"
                        })
                    else
                        local previewData = jpegData
                        if base64Encode then
                            previewData = LrStringUtils.encodeBase64(jpegData)
                        end
                        
                        table.insert(results, {
                            photoId = photoId,
                            success = true,
                            preview = previewData,
                            size = pixelSize,
                            dataSize = string.len(jpegData),
                            base64Encoded = base64Encode
                        })
                    end
                end
                
                LrTasks.yield()
            end
            
            progressScope:setCaption("Batch preview generation complete")
            progressScope:setPortionComplete(1.0)
        
        progressScope:done()
        
        local successCount = 0
        for _, result in ipairs(results) do
            if result.success then
                successCount = successCount + 1
            end
        end
        
        logger:info("Batch preview generation completed: " .. successCount .. "/" .. #results .. " successful")
        
        callback({
            result = {
                processed = #results,
                successful = successCount,
                results = results
            }
        })
        end)
    end)
end

-- Get preview info without generating
function PreviewModule.getPreviewInfo(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local photoId = params.photoId
    
    if not photoId then
        callback({
            error = {
                code = "MISSING_PHOTO_ID",
                message = "Photo ID is required"
            }
        })
        return
    end
    
    logger:debug("Getting preview info for photo: " .. photoId)
    
    LrTasks.startAsyncTask(function()
        local catalog = LrApplication.activeCatalog()
        
        catalog:withReadAccessDo(function()
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
            
            -- Get basic photo dimensions and format info
            local metadata = photo:getRawMetadata("dimensions")
            local fileFormat = photo:getRawMetadata("fileFormat")
            
            local previewInfo = {
                photoId = photoId,
                filename = photo:getFormattedMetadata("fileName"),
                fileFormat = fileFormat,
                dimensions = metadata,
                originalWidth = metadata and metadata.width or nil,
                originalHeight = metadata and metadata.height or nil,
                availableSizes = {
                    small = 240,
                    medium = 640,
                    large = 1024
                }
            }
            
            logger:debug("Retrieved preview info for: " .. previewInfo.filename)
            
            callback({
                result = previewInfo
            })
        end)
    end)
end

-- Get preview chunk for large data transfer
function PreviewModule.getPreviewChunk(params, callback)
    local logger = getLogger()
    local previewId = params.previewId
    local chunkIndex = params.chunkIndex or 0
    local chunkSize = params.chunkSize or (1024 * 1024)  -- 1MB default
    
    if not previewId then
        callback({
            error = {
                code = "MISSING_PREVIEW_ID",
                message = "Preview ID is required"
            }
        })
        return
    end
    
    if not _G.LightroomPythonBridge.previewCache then
        callback({
            error = {
                code = "NO_CACHE",
                message = "Preview cache not initialized"
            }
        })
        return
    end
    
    local cachedPreview = _G.LightroomPythonBridge.previewCache[previewId]
    if not cachedPreview then
        callback({
            error = {
                code = "PREVIEW_NOT_FOUND",
                message = "Preview with ID " .. previewId .. " not found in cache"
            }
        })
        return
    end
    
    logger:debug("Getting chunk " .. chunkIndex .. " for preview: " .. previewId)
    
    local data = cachedPreview.data
    if cachedPreview.base64Encoded then
        data = LrStringUtils.encodeBase64(data)
    end
    
    local startPos = (chunkIndex * chunkSize) + 1
    local endPos = math.min(startPos + chunkSize - 1, string.len(data))
    local chunk = string.sub(data, startPos, endPos)
    local isLastChunk = (endPos >= string.len(data))
    
    logger:debug("Chunk " .. chunkIndex .. ": " .. string.len(chunk) .. " bytes, last=" .. tostring(isLastChunk))
    
    callback({
        result = {
            chunk = chunk,
            chunkIndex = chunkIndex,
            isLastChunk = isLastChunk,
            totalSize = string.len(data),
            chunkSize = string.len(chunk)
        }
    })
    
    -- Clean up cache if this was the last chunk
    if isLastChunk then
        _G.LightroomPythonBridge.previewCache[previewId] = nil
        logger:debug("Cleaned up preview cache for: " .. previewId)
    end
end

return PreviewModule