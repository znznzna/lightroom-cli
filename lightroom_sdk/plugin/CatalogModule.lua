-- CatalogModule.lua
-- Catalog operations API wrapper for Phase 4
-- Enhanced with lightweight error handling

-- Lazy imports to avoid loading issues
local LrApplication = nil
local LrTasks = import 'LrTasks'
local LrDate = nil
local LrProgressScope = nil

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
        CODES = { MISSING_PARAM = "MISSING_PARAM", CATALOG_ACCESS_FAILED = "CATALOG_ACCESS_FAILED" }
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
    if not LrDate then
        local success, dateModule = ErrorUtils.safeCall(import, 'LrDate')
        if success and dateModule then
            LrDate = dateModule
        end
    end
end

-- Get logger from global state (defensive)
local function getLogger()
    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.logger then
        return _G.LightroomPythonBridge.logger
    end
    local LrLogger = import 'LrLogger'
    local logger = LrLogger('CatalogModule')
    logger:enable("logfile")
    return logger
end

local CatalogModule = {}

-- Search photos (deprecated: delegates to findPhotos)
function CatalogModule.searchPhotos(params, callback)
    local logger = getLogger()
    logger:warn("deprecated: searchPhotos は findPhotos に統合されました。次バージョンで削除予定。")

    -- Convert criteria to searchDesc format
    local criteria = (params and params.criteria) or {}
    local searchDesc = {}
    for k, v in pairs(criteria) do
        searchDesc[k] = v
    end

    local findParams = {
        searchDesc = searchDesc,
        limit = (params and params.limit) or 100,
        offset = (params and params.offset) or 0,
    }

    CatalogModule.findPhotos(findParams, function(response)
        -- Add legacy hasMore field for backward compatibility
        local r = response and response.result
        if r and r.photos then
            local total = r.total or 0
            local off = r.offset or 0
            local returned = r.returned or #r.photos
            r.hasMore = (off + returned) < total
        end
        callback(response)
    end)
end

-- Get photo metadata
function CatalogModule.getPhotoMetadata(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    local photoId = nil
    
    -- Safe parameter extraction with error handling
    local success, result = ErrorUtils.safeCall(function()
        logger:debug("getPhotoMetadata called with params: " .. tostring(params))
        
        if params then
            logger:debug("params is a table with type: " .. type(params))
            local count = 0
            for k, v in pairs(params) do
                logger:debug("  param[" .. tostring(k) .. "] = " .. tostring(v) .. " (type: " .. type(v) .. ")")
                count = count + 1
            end
            logger:debug("Total params count: " .. count)
            
            photoId = params.photoId
        else
            logger:error("params is nil!")
        end
        
        logger:debug("Extracted photoId: " .. tostring(photoId))
        return photoId
    end)
    
    if not success then
        logger:error("Error in parameter extraction: " .. tostring(result))
    else
        photoId = result
    end
    
    if not photoId then
        callback({
            error = {
                code = "MISSING_PHOTO_ID",
                message = "Photo ID is required"
            }
        })
        return
    end
    
    logger:debug("Getting metadata for photo: " .. photoId)
    
    local catalog = LrApplication.activeCatalog()
    
    catalog:withReadAccessDo(function()
        -- Find photo by localIdentifier
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
        
        -- Collect comprehensive metadata
        local rawRating = photo:getRawMetadata("rating")
        logger:debug("Raw rating value: " .. tostring(rawRating) .. " (type: " .. type(rawRating) .. ")")
        
        local metadata = {
            -- Basic info
            id = photo.localIdentifier,
            filename = photo:getFormattedMetadata("fileName"),
            folderPath = photo:getFormattedMetadata("folderName"),
            filepath = photo:getRawMetadata("path"),
            fileSize = photo:getFormattedMetadata("fileSize"),
            fileFormat = photo:getRawMetadata("fileFormat"),
            
            -- Capture info
            captureTime = photo:getFormattedMetadata("dateTimeOriginal"),
            cameraMake = photo:getFormattedMetadata("cameraMake"),
            cameraModel = photo:getFormattedMetadata("cameraModel"),
            lens = photo:getFormattedMetadata("lens"),
            
            -- Settings
            iso = photo:getFormattedMetadata("isoSpeedRating"),
            aperture = photo:getFormattedMetadata("aperture"),
            shutterSpeed = photo:getFormattedMetadata("shutterSpeed"),
            focalLength = photo:getFormattedMetadata("focalLength"),
            
            -- Lightroom specific
            rating = rawRating or 0,  -- Default to 0 if nil
            colorLabel = photo:getRawMetadata("colorNameForLabel"),
            pickStatus = photo:getRawMetadata("pickStatus"),
            isVirtualCopy = photo:getRawMetadata("isVirtualCopy"),
            stackPosition = photo:getRawMetadata("stackPositionInFolder"),
            
            -- Develop status (use basic metadata only)
            -- hasAdjustments/hasCrop not available in all Lightroom versions
            
            -- Keywords and collections
            keywords = {},
            collections = {}
        }
        
        logger:debug("Metadata table rating: " .. tostring(metadata.rating))
        
        -- Get keywords
        local keywords = photo:getRawMetadata("keywords")
        if keywords then
            for _, keyword in ipairs(keywords) do
                table.insert(metadata.keywords, {
                    name = keyword:getName(),
                    synonyms = keyword:getSynonyms()
                })
            end
        end
        
        -- Get collections
        local collections = photo:getContainedCollections()
        if collections then
            for _, collection in ipairs(collections) do
                table.insert(metadata.collections, {
                    name = collection:getName(),
                    type = collection:type()
                })
            end
        end
        
        logger:info("Retrieved metadata for photo: " .. metadata.filename)
        logger:debug("About to send metadata with rating: " .. tostring(metadata.rating))
        
        callback({
            result = metadata
        })
    end)
end

-- Get current selection
function CatalogModule.getSelectedPhotos(params, callback)
    local wrappedCallback = ErrorUtils.wrapCallback(callback, "getSelectedPhotos")
    
    -- Ensure modules are loaded
    local moduleSuccess, moduleError = ErrorUtils.safeCall(ensureLrModules)
    if not moduleSuccess then
        wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.RESOURCE_UNAVAILABLE, 
            "Failed to load Lightroom modules: " .. tostring(moduleError)))
        return
    end
    
    local logger = getLogger()
    logger:debug("Getting currently selected photos")
    
    local catalog = LrApplication.activeCatalog()
    
    catalog:withReadAccessDo(function()
        local selectedSuccess, selectedPhotos = ErrorUtils.safeCall(function()
            return catalog:getTargetPhotos()
        end)
        
        if not selectedSuccess or not selectedPhotos or #selectedPhotos == 0 then
            wrappedCallback(ErrorUtils.createSuccess({
                photos = {},
                count = 0
            }, "No photos currently selected"))
            return
        end
        
        local results = {}
        
        for i, photo in ipairs(selectedPhotos) do
            local photoData = {
                id = photo.localIdentifier
            }
            
            -- Safely get photo metadata
            ErrorUtils.safeCall(function()
                photoData.filename = photo:getFormattedMetadata("fileName")
                photoData.folderPath = photo:getFormattedMetadata("folderName")
                photoData.path = photo:getRawMetadata("path")
                photoData.captureTime = photo:getFormattedMetadata("dateTimeOriginal")
                photoData.rating = photo:getRawMetadata("rating")
                photoData.pickStatus = photo:getRawMetadata("pickStatus")
                photoData.fileFormat = photo:getRawMetadata("fileFormat")
                photoData.isVirtualCopy = photo:getRawMetadata("isVirtualCopy")
            end)

            table.insert(results, photoData)
        end
        
        logger:info("Retrieved " .. #results .. " selected photos")
        
        wrappedCallback(ErrorUtils.createSuccess({
            photos = results,
            count = #results
        }, "Selected photos retrieved successfully"))
    end)
end

-- Set photo selection
function CatalogModule.setSelectedPhotos(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local photoIds = params.photoIds
    
    if not photoIds or type(photoIds) ~= "table" then
        callback({
            error = {
                code = "INVALID_PHOTO_IDS",
                message = "Photo IDs array is required"
            }
        })
        return
    end
    
    logger:debug("Setting photo selection to " .. #photoIds .. " photos")
    
    local catalog = LrApplication.activeCatalog()
    
    -- Use withWriteAccessDo with timeout to prevent blocking
    local selectResult = nil
    local writeSuccess, writeError = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Set Photo Selection", function()
            local photos = {}
            local notFound = {}

            -- Find all photos by localIdentifier
            for _, photoId in ipairs(photoIds) do
                local photo = catalog:getPhotoByLocalId(tonumber(photoId))
                if photo then
                    table.insert(photos, photo)
                else
                    table.insert(notFound, photoId)
                end
            end

            if #photos == 0 then
                error("No photos found with provided IDs")
            end

            -- Set selection
            catalog:setSelectedPhotos(photos[1], photos)

            selectResult = {
                selected = #photos,
                notFound = #notFound > 0 and notFound or nil
            }
        end, { timeout = 10 })  -- 10 second timeout
    end)

    if writeSuccess and selectResult then
        logger:info("Successfully set selection to " .. selectResult.selected .. " photos")
        callback({
            result = selectResult
        })
    else
        logger:error("Failed to set photo selection: " .. tostring(writeError))
        callback({
            error = {
                code = "WRITE_ACCESS_BLOCKED",
                message = "Failed to set photo selection: " .. tostring(writeError)
            }
        })
    end
end

-- Get all photos in catalog
function CatalogModule.getAllPhotos(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local limit = params.limit or 1000  -- Default limit to prevent memory issues
    local offset = params.offset or 0
    
    logger:debug("Getting all photos from catalog")
    
    local catalog = LrApplication.activeCatalog()
    
    catalog:withReadAccessDo(function()
        local allPhotos = catalog:getAllPhotos()
        
        if not allPhotos then
            callback({
                error = {
                    code = "NO_PHOTOS",
                    message = "No photos found in catalog"
                }
            })
            return
        end
        
        logger:info("Found " .. #allPhotos .. " total photos in catalog")
        
        -- Apply pagination
        local startIndex = offset + 1
        local endIndex = math.min(startIndex + limit - 1, #allPhotos)
        local pagedPhotos = {}
        
        for i = startIndex, endIndex do
            local photo = allPhotos[i]
            table.insert(pagedPhotos, {
                id = photo.localIdentifier,
                filename = photo:getFormattedMetadata("fileName"),
                path = photo:getRawMetadata("path"),
                captureTime = photo:getFormattedMetadata("dateTimeOriginal"),
                fileFormat = photo:getRawMetadata("fileFormat"),
                rating = photo:getRawMetadata("rating"),
                pickStatus = photo:getRawMetadata("pickStatus")
            })
        end
        
        callback({
            result = {
                photos = pagedPhotos,
                total = #allPhotos,
                offset = offset,
                limit = limit,
                returned = #pagedPhotos
            }
        })
    end)
end

-- Find photo by file path
function CatalogModule.findPhotoByPath(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local path = params.path
    
    if not path then
        callback({
            error = {
                code = "MISSING_PATH",
                message = "File path is required"
            }
        })
        return
    end
    
    logger:debug("Finding photo by path: " .. path)
    
    local catalog = LrApplication.activeCatalog()
    
    catalog:withReadAccessDo(function()
        local photo = catalog:findPhotoByPath(path)
        
        if not photo then
            callback({
                error = {
                    code = "PHOTO_NOT_FOUND",
                    message = "No photo found at path: " .. path
                }
            })
            return
        end
        
        callback({
            result = {
                id = photo.localIdentifier,
                filename = photo:getFormattedMetadata("fileName"),
                path = photo:getRawMetadata("path"),
                captureTime = photo:getFormattedMetadata("dateTimeOriginal"),
                fileFormat = photo:getRawMetadata("fileFormat"),
                rating = photo:getRawMetadata("rating"),
                camera = photo:getFormattedMetadata("cameraModel")
            }
        })
    end)
end

-- Known filter keys for findPhotos
local KNOWN_FILTER_KEYS = {
    flag = true, rating = true, ratingOp = true, colorLabel = true, camera = true,
    folderPath = true, captureDateFrom = true, captureDateTo = true,
    fileFormat = true, keyword = true, filename = true,
}

-- Chunk processing constants
local FILTER_CHUNK_SIZE = 50
local METADATA_CHUNK_SIZE = 50
local DEFAULT_PAGE_SIZE = 500
local MAX_PAGE_SIZE = 2000

-- Get CommandRouter from global state for abort checking
local function getCommandRouter()
    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.router then
        return _G.LightroomPythonBridge.router
    end
    return nil
end

-- Match a single photo against search criteria
local function matchPhoto(photo, searchDesc)
    -- Light filters first --

    -- Rating filter
    if searchDesc.rating then
        local rating = photo:getRawMetadata("rating") or 0
        local op = searchDesc.ratingOp or "=="
        if op == "==" and rating ~= searchDesc.rating then return false end
        if op == ">=" and rating < searchDesc.rating then return false end
        if op == "<=" and rating > searchDesc.rating then return false end
        if op == ">" and rating <= searchDesc.rating then return false end
        if op == "<" and rating >= searchDesc.rating then return false end
    end

    -- Flag filter
    if searchDesc.flag then
        local pickStatus = photo:getRawMetadata("pickStatus") or 0
        if searchDesc.flag == "pick" and pickStatus ~= 1 then return false end
        if searchDesc.flag == "reject" and pickStatus ~= -1 then return false end
        if searchDesc.flag == "none" and pickStatus ~= 0 then return false end
    end

    -- Color label filter
    if searchDesc.colorLabel then
        local label = photo:getRawMetadata("colorNameForLabel") or ""
        if searchDesc.colorLabel == "none" then
            if label ~= "" and label ~= "none" then return false end
        else
            if label ~= searchDesc.colorLabel then return false end
        end
    end

    -- File format filter (exact match)
    if searchDesc.fileFormat then
        local fmt = photo:getRawMetadata("fileFormat") or ""
        if fmt ~= searchDesc.fileFormat then return false end
    end

    -- Heavy filters --

    -- Camera filter
    if searchDesc.camera then
        local camera = photo:getFormattedMetadata("cameraModel") or ""
        if not string.find(string.lower(camera), string.lower(searchDesc.camera)) then
            return false
        end
    end

    -- Capture date range filter (use raw date + W3C format for locale-independent comparison)
    if searchDesc.captureDateFrom or searchDesc.captureDateTo then
        local rawDate = photo:getRawMetadata("dateTimeOriginal")
        if rawDate then
            local isoDate
            if LrDate and LrDate.timeToW3CDate then
                isoDate = LrDate.timeToW3CDate(rawDate)
            else
                isoDate = photo:getFormattedMetadata("dateTimeOriginal") or ""
            end
            if searchDesc.captureDateFrom and isoDate < searchDesc.captureDateFrom then
                return false
            end
            if searchDesc.captureDateTo and isoDate > searchDesc.captureDateTo then
                return false
            end
        else
            return false
        end
    end

    -- Folder path filter (substring match)
    if searchDesc.folderPath then
        local path = photo:getRawMetadata("path") or ""
        if not string.find(path, searchDesc.folderPath, 1, true) then
            return false
        end
    end

    -- Filename filter (substring match)
    if searchDesc.filename then
        local fname = photo:getFormattedMetadata("fileName") or ""
        if not string.find(fname, searchDesc.filename, 1, true) then
            return false
        end
    end

    -- Keyword filter (substring match on keyword names)
    if searchDesc.keyword then
        local keywords = photo:getRawMetadata("keywords") or {}
        local keywordMatch = false
        for _, kw in ipairs(keywords) do
            local kwName = kw:getName()
            if string.find(string.lower(kwName), string.lower(searchDesc.keyword), 1, true) then
                keywordMatch = true
                break
            end
        end
        if not keywordMatch then return false end
    end

    return true
end

-- Advanced photo search with criteria
function CatalogModule.findPhotos(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local searchDesc = params.searchDesc or {}
    local limit = math.min(params.limit or DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE)
    local offset = math.max(params.offset or 0, 0)

    logger:debug("Finding photos with search criteria")

    -- Validate: check for unknown filter keys
    local warnings = {}
    for key, _ in pairs(searchDesc) do
        if not KNOWN_FILTER_KEYS[key] then
            table.insert(warnings, "Unknown filter key: " .. tostring(key))
        end
    end

    -- Validate: rating must be a number
    if searchDesc.rating ~= nil and type(searchDesc.rating) ~= "number" then
        callback({
            error = {
                code = "INVALID_PARAM",
                message = "rating must be a number"
            }
        })
        return
    end

    local catalog = LrApplication.activeCatalog()
    local partialErrors = {}
    local aborted = false
    local abortReason = nil
    local requestId = params._requestId
    local command = params._command or "catalog.findPhotos"
    local router = getCommandRouter()

    -- Step 1: Get all photos (lightweight, no chunking needed)
    local allPhotos
    catalog:withReadAccessDo(function()
        allPhotos = catalog:getAllPhotos()
    end)

    if not allPhotos or #allPhotos == 0 then
        callback({
            result = {
                photos = {},
                total = 0,
                returned = 0,
                offset = offset,
                limit = limit,
                warnings = #warnings > 0 and warnings or nil
            }
        })
        return
    end

    -- Step 2: Filter in chunks (yield between chunks to avoid blocking)
    local filtered = {}
    local totalPhotos = #allPhotos
    for chunkStart = 1, totalPhotos, FILTER_CHUNK_SIZE do
        -- Abort check at chunk boundary
        if router and requestId and router:shouldAbort(requestId, command) then
            aborted = true
            abortReason = router:isCancelled(requestId) and "cancelled" or "timeout"
            break
        end
        local chunkEnd = math.min(chunkStart + FILTER_CHUNK_SIZE - 1, totalPhotos)
        local chunkOk, chunkErr = LrTasks.pcall(function()
            catalog:withReadAccessDo(function()
                for i = chunkStart, chunkEnd do
                    if matchPhoto(allPhotos[i], searchDesc) then
                        table.insert(filtered, allPhotos[i])
                    end
                end
            end)
        end)
        if not chunkOk then
            table.insert(partialErrors, {
                chunk = chunkStart .. "-" .. chunkEnd,
                error = tostring(chunkErr)
            })
        end
        LrTasks.yield()
    end

    -- Step 3: Apply pagination
    local total = #filtered
    local startIndex = offset + 1
    local endIndex = math.min(offset + limit, total)
    local pagedPhotos = {}
    for i = startIndex, endIndex do
        table.insert(pagedPhotos, filtered[i])
    end

    -- Step 4: Build metadata in chunks
    local resultPhotos = {}
    if not aborted then
        for chunkStart = 1, #pagedPhotos, METADATA_CHUNK_SIZE do
            -- Abort check at chunk boundary
            if router and requestId and router:shouldAbort(requestId, command) then
                aborted = true
                abortReason = router:isCancelled(requestId) and "cancelled" or "timeout"
                break
            end
            local chunkEnd = math.min(chunkStart + METADATA_CHUNK_SIZE - 1, #pagedPhotos)
            local chunkOk, chunkErr = LrTasks.pcall(function()
                catalog:withReadAccessDo(function()
                    for i = chunkStart, chunkEnd do
                        local photo = pagedPhotos[i]
                        table.insert(resultPhotos, {
                            id = photo.localIdentifier,
                            filename = photo:getFormattedMetadata("fileName"),
                            path = photo:getRawMetadata("path"),
                            captureTime = photo:getFormattedMetadata("dateTimeOriginal"),
                            fileFormat = photo:getRawMetadata("fileFormat"),
                            rating = photo:getRawMetadata("rating"),
                            pickStatus = photo:getRawMetadata("pickStatus"),
                            colorLabel = photo:getRawMetadata("colorNameForLabel")
                        })
                    end
                end)
            end)
            if not chunkOk then
                table.insert(partialErrors, {
                    chunk = "metadata " .. chunkStart .. "-" .. chunkEnd,
                    error = tostring(chunkErr)
                })
            end
            LrTasks.yield()
        end
    end

    local responseResult = {
        photos = resultPhotos,
        total = total,
        returned = #resultPhotos,
        offset = offset,
        limit = limit,
        processedCount = #resultPhotos,
        totalCount = total,
        warnings = #warnings > 0 and warnings or nil
    }

    if aborted then
        responseResult.incomplete = true
        responseResult.reason = abortReason
    elseif #partialErrors > 0 then
        responseResult.incomplete = true
        responseResult.reason = "chunk_errors"
        responseResult.partialErrors = partialErrors
    end

    callback({ result = responseResult })
end

-- Get collections in catalog
function CatalogModule.getCollections(params, callback)
    ensureLrModules()
    local logger = getLogger()

    logger:debug("Getting collections from catalog")

    local catalog = LrApplication.activeCatalog()
    local includePhotoCounts = params and params.includePhotoCounts

    local collections
    catalog:withReadAccessDo(function()
        collections = catalog:getChildCollections()
    end)

    local resultCollections = {}
    local COLLECTION_CHUNK_SIZE = 50
    for chunkStart = 1, #collections, COLLECTION_CHUNK_SIZE do
        local chunkEnd = math.min(chunkStart + COLLECTION_CHUNK_SIZE - 1, #collections)
        catalog:withReadAccessDo(function()
            for i = chunkStart, chunkEnd do
                local collection = collections[i]
                local entry = {
                    id = collection.localIdentifier,
                    name = collection:getName(),
                    type = collection:type(),
                }
                if includePhotoCounts then
                    entry.photoCount = #collection:getPhotos()
                end
                table.insert(resultCollections, entry)
            end
        end)
        LrTasks.yield()
    end

    callback({
        result = {
            collections = resultCollections,
            count = #resultCollections
        }
    })
end

-- Get keywords in catalog
function CatalogModule.getKeywords(params, callback)
    ensureLrModules()
    local logger = getLogger()
    
    logger:debug("Getting keywords from catalog")
    
    local catalog = LrApplication.activeCatalog()
    
    catalog:withReadAccessDo(function()
        local keywords = catalog:getKeywords()
        
        local resultKeywords = {}
        for _, keyword in ipairs(keywords) do
            table.insert(resultKeywords, {
                id = keyword.localIdentifier,
                name = keyword:getName(),
                photoCount = #keyword:getPhotos()
            })
        end
        
        callback({
            result = {
                keywords = resultKeywords,
                count = #resultKeywords
            }
        })
    end)
end

-- Get folders in catalog
function CatalogModule.getFolders(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local includeSubfolders = params.includeSubfolders or false
    
    logger:debug("Getting folders from catalog")
    
    local catalog = LrApplication.activeCatalog()
    
    catalog:withReadAccessDo(function()
        local rootFolders = catalog:getFolders()
        
        local function buildFolderTree(folder, depth)
            depth = depth or 0
            local folderPath = folder:getPath()
            local folderData = {
                id = folderPath, -- Use path as ID since folders don't have localIdentifier
                name = folder:getName(),
                path = folderPath,
                type = folder:type(),
                depth = depth,
                photoCount = #folder:getPhotos(false), -- Photos directly in this folder
                totalPhotoCount = #folder:getPhotos(true), -- Photos including subfolders
                subfolders = {}
            }
            
            -- Get parent folder info if available
            local parent = folder:getParent()
            if parent then
                folderData.parentId = parent:getPath()
                folderData.parentName = parent:getName()
            end
            
            -- Recursively get subfolders if requested
            if includeSubfolders then
                local children = folder:getChildren()
                if children then
                    for _, child in ipairs(children) do
                        table.insert(folderData.subfolders, buildFolderTree(child, depth + 1))
                    end
                end
            end
            
            return folderData
        end
        
        local resultFolders = {}
        for _, folder in ipairs(rootFolders) do
            table.insert(resultFolders, buildFolderTree(folder))
        end
        
        logger:info("Retrieved " .. #resultFolders .. " root folders from catalog")
        
        callback({
            result = {
                folders = resultFolders,
                count = #resultFolders,
                includeSubfolders = includeSubfolders
            }
        })
    end)
end

-- Batch get formatted metadata for multiple photos
function CatalogModule.batchGetFormattedMetadata(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local photoIds = params.photoIds
    local keys = params.keys or {"fileName", "dateTimeOriginal", "rating"}
    
    logger:debug("Batch metadata - photoIds type: " .. type(photoIds))
    if photoIds then
        logger:debug("Batch metadata - photoIds length: " .. tostring(#photoIds))
        if type(photoIds) == "table" then
            for i, id in ipairs(photoIds) do
                logger:debug("  photoId[" .. i .. "] = " .. tostring(id) .. " (type: " .. type(id) .. ")")
            end
        end
    end
    
    if not photoIds then
        callback({
            error = {
                code = "MISSING_PHOTO_IDS", 
                message = "Photo IDs parameter is missing"
            }
        })
        return
    end
    
    if type(photoIds) ~= "table" then
        callback({
            error = {
                code = "INVALID_PHOTO_IDS_TYPE",
                message = "Photo IDs must be an array, got: " .. type(photoIds)
            }
        })
        return
    end
    
    if #photoIds == 0 then
        callback({
            error = {
                code = "EMPTY_PHOTO_IDS",
                message = "Photo IDs array is empty"
            }
        })
        return
    end
    
    logger:debug("Batch getting metadata for " .. #photoIds .. " photos")
    logger:debug("Keys type: " .. type(keys))
    if type(keys) == "table" then
        logger:debug("Keys length: " .. #keys)
        for i, key in ipairs(keys) do
            logger:debug("  key[" .. i .. "] = " .. tostring(key))
        end
    else
        logger:debug("Keys value: " .. tostring(keys))
    end
    
    local catalog = LrApplication.activeCatalog()
    
    catalog:withReadAccessDo(function()
        local photos = {}
        for _, photoId in ipairs(photoIds) do
            local photo = catalog:getPhotoByLocalId(tonumber(photoId))
            if photo then
                table.insert(photos, photo)
            end
        end
        
        if #photos == 0 then
            callback({
                result = {
                    metadata = {},
                    requested = #photoIds,
                    found = 0
                }
            })
            return
        end
        
        -- Use batch API for efficiency
        local batchResults = catalog:batchGetFormattedMetadata(photos, keys)
        
        local results = {}
        for _, photo in ipairs(photos) do
            local metadata = {}
            local photoMeta = batchResults[photo]
            if photoMeta then
                for k, v in pairs(photoMeta) do
                    metadata[k] = v
                end
            end
            metadata.id = photo.localIdentifier
            table.insert(results, metadata)
        end
        
        callback({
            result = {
                metadata = results,
                requested = #photoIds,
                found = #photos,
                keys = keys
            }
        })
    end)
end

-- Set photo rating (Gap C fix)
function CatalogModule.setRating(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local photoId = params.photoId
    local rating = params.rating ~= nil and tonumber(params.rating) or nil

    if not photoId then
        callback(ErrorUtils.createError("MISSING_PARAM", "photoId is required"))
        return
    end
    if rating == nil or rating < 0 or rating > 5 then
        callback(ErrorUtils.createError("INVALID_PARAM_VALUE", "rating must be between 0 and 5"))
        return
    end

    local catalog = LrApplication.activeCatalog()
    local writeSuccess, writeError = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Set Rating", function()
            local photo = catalog:getPhotoByLocalId(tonumber(photoId))
            if not photo then error("Photo not found: " .. tostring(photoId)) end
            -- LR API: setRawMetadata("rating", 0) throws; use nil for unrated
            local ratingValue = rating
            if rating == 0 then ratingValue = nil end
            photo:setRawMetadata("rating", ratingValue)
        end, { timeout = 10 })
    end)

    if writeSuccess then
        callback(ErrorUtils.createSuccess({ photoId = photoId, rating = rating, message = "Rating set successfully" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to set rating: " .. tostring(writeError)))
    end
end

-- Add keywords to photo (Gap C fix)
function CatalogModule.addKeywords(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local photoId = params.photoId
    local keywords = params.keywords

    if not photoId then
        callback(ErrorUtils.createError("MISSING_PARAM", "photoId is required"))
        return
    end
    if not keywords or type(keywords) ~= "table" or #keywords == 0 then
        callback(ErrorUtils.createError("INVALID_PARAM_VALUE", "keywords must be a non-empty array"))
        return
    end

    local catalog = LrApplication.activeCatalog()
    local addedKeywords = {}
    local writeSuccess, writeError = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Add Keywords", function()
            local photo = catalog:getPhotoByLocalId(tonumber(photoId))
            if not photo then error("Photo not found: " .. tostring(photoId)) end
            for _, kwName in ipairs(keywords) do
                local keyword = catalog:createKeyword(kwName, {}, false, nil, true)
                if keyword then
                    photo:addKeyword(keyword)
                    table.insert(addedKeywords, kwName)
                end
            end
        end, { timeout = 10 })
    end)

    if writeSuccess then
        callback(ErrorUtils.createSuccess({ photoId = photoId, addedKeywords = addedKeywords, count = #addedKeywords, message = "Keywords added successfully" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to add keywords: " .. tostring(writeError)))
    end
end

-- Set photo flag (pick/reject/none)
function CatalogModule.setFlag(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local photoId = params.photoId
    local flag = params.flag  -- 1=pick, -1=reject, 0=none

    if not photoId then
        callback(ErrorUtils.createError("MISSING_PARAM", "photoId is required"))
        return
    end
    if flag ~= 1 and flag ~= -1 and flag ~= 0 then
        callback(ErrorUtils.createError("INVALID_PARAM_VALUE",
            "flag must be 1 (pick), -1 (reject), or 0 (none)"))
        return
    end

    local catalog = LrApplication.activeCatalog()
    local writeSuccess, writeError = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Set Flag", function()
            local photo = catalog:getPhotoByLocalId(tonumber(photoId))
            if not photo then
                error("Photo not found: " .. tostring(photoId))
            end
            photo:setRawMetadata("pickStatus", flag)
        end, { timeout = 10 })
    end)

    if writeSuccess then
        callback(ErrorUtils.createSuccess({
            photoId = photoId,
            flag = flag,
            message = "Flag set successfully"
        }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED",
            "Failed to set flag: " .. tostring(writeError)))
    end
end

-- Get photo flag status
function CatalogModule.getFlag(params, callback)
    ensureLrModules()
    local logger = getLogger()
    local photoId = params.photoId

    if not photoId then
        callback(ErrorUtils.createError("MISSING_PARAM", "photoId is required"))
        return
    end

    local catalog = LrApplication.activeCatalog()
    catalog:withReadAccessDo(function()
        local photo = catalog:getPhotoByLocalId(tonumber(photoId))
        if not photo then
            callback(ErrorUtils.createError("PHOTO_NOT_FOUND",
                "Photo not found: " .. tostring(photoId)))
            return
        end

        local pickStatus = photo:getRawMetadata("pickStatus") or 0
        local label = "none"
        if pickStatus == 1 then label = "pick"
        elseif pickStatus == -1 then label = "reject"
        end

        callback(ErrorUtils.createSuccess({
            photoId = photoId,
            pickStatus = pickStatus,
            label = label
        }))
    end)
end

-- Set photo title
function CatalogModule.setTitle(params, callback)
    ensureLrModules()
    local photoId = params.photoId
    local title = params.title

    if not photoId then
        callback(ErrorUtils.createError("MISSING_PARAM", "photoId is required"))
        return
    end
    if not title then
        callback(ErrorUtils.createError("MISSING_PARAM", "title is required"))
        return
    end

    local catalog = LrApplication.activeCatalog()
    local writeSuccess, writeError = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Set Title", function()
            local photo = catalog:getPhotoByLocalId(tonumber(photoId))
            if not photo then error("Photo not found: " .. tostring(photoId)) end
            photo:setRawMetadata("title", title)
        end, { timeout = 10 })
    end)

    if writeSuccess then
        callback(ErrorUtils.createSuccess({ photoId = photoId, title = title, message = "Title set successfully" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to set title: " .. tostring(writeError)))
    end
end

-- Set photo caption
function CatalogModule.setCaption(params, callback)
    ensureLrModules()
    local photoId = params.photoId
    local caption = params.caption

    if not photoId then
        callback(ErrorUtils.createError("MISSING_PARAM", "photoId is required"))
        return
    end
    if not caption then
        callback(ErrorUtils.createError("MISSING_PARAM", "caption is required"))
        return
    end

    local catalog = LrApplication.activeCatalog()
    local writeSuccess, writeError = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Set Caption", function()
            local photo = catalog:getPhotoByLocalId(tonumber(photoId))
            if not photo then error("Photo not found: " .. tostring(photoId)) end
            photo:setRawMetadata("caption", caption)
        end, { timeout = 10 })
    end)

    if writeSuccess then
        callback(ErrorUtils.createSuccess({ photoId = photoId, caption = caption, message = "Caption set successfully" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to set caption: " .. tostring(writeError)))
    end
end

-- Set photo color label
function CatalogModule.setColorLabel(params, callback)
    ensureLrModules()
    local photoId = params.photoId
    local label = params.label

    if not photoId then
        callback(ErrorUtils.createError("MISSING_PARAM", "photoId is required"))
        return
    end
    if not label then
        callback(ErrorUtils.createError("MISSING_PARAM", "label is required"))
        return
    end

    local catalog = LrApplication.activeCatalog()
    local writeSuccess, writeError = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Set Color Label", function()
            local photo = catalog:getPhotoByLocalId(tonumber(photoId))
            if not photo then error("Photo not found: " .. tostring(photoId)) end
            photo:setRawMetadata("colorNameForLabel", label)
        end, { timeout = 10 })
    end)

    if writeSuccess then
        callback(ErrorUtils.createSuccess({ photoId = photoId, label = label, message = "Color label set successfully" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to set color label: " .. tostring(writeError)))
    end
end

-- Apply a develop preset by name
function CatalogModule.applyDevelopPreset(params, callback)
    ensureLrModules()
    local logger = getLogger()

    if not params or not params.presetName then
        callback(ErrorUtils.createError("MISSING_PARAM", "presetName is required"))
        return
    end

    local presetName = params.presetName
    logger:debug("Applying develop preset: " .. presetName)

    -- Search for the preset by name across all folders
    local targetPreset = nil
    local folders = LrApplication.developPresetFolders()
    for _, folder in ipairs(folders) do
        local presets = folder:getDevelopPresets()
        for _, preset in ipairs(presets) do
            if preset:getName() == presetName then
                targetPreset = preset
                break
            end
        end
        if targetPreset then break end
    end

    if not targetPreset then
        callback(ErrorUtils.createError("PHOTO_NOT_FOUND",
            "Develop preset not found: " .. presetName))
        return
    end

    local catalog = LrApplication.activeCatalog()
    local photo = catalog:getTargetPhoto()
    if not photo then
        callback(ErrorUtils.createError("PHOTO_NOT_FOUND", "No photo selected"))
        return
    end

    local writeSuccess, writeError = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Apply Develop Preset", function()
            photo:applyDevelopPreset(targetPreset)
        end, { timeout = 10 })
    end)

    if writeSuccess then
        callback(ErrorUtils.createSuccess({
            preset = presetName,
            applied = true,
            message = "Develop preset applied successfully"
        }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED",
            "Failed to apply develop preset: " .. tostring(writeError)))
    end
end

-- Create a develop snapshot
function CatalogModule.createDevelopSnapshot(params, callback)
    ensureLrModules()
    local logger = getLogger()

    if not params or not params.name then
        callback(ErrorUtils.createError("MISSING_PARAM", "name is required"))
        return
    end

    local name = params.name
    logger:debug("Creating develop snapshot: " .. name)

    local catalog = LrApplication.activeCatalog()
    local photo = catalog:getTargetPhoto()
    if not photo then
        callback(ErrorUtils.createError("PHOTO_NOT_FOUND", "No photo selected"))
        return
    end

    local writeSuccess, writeError = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Create Develop Snapshot", function()
            photo:createDevelopSnapshot(name)
        end, { timeout = 10 })
    end)

    if writeSuccess then
        callback(ErrorUtils.createSuccess({
            name = name,
            created = true,
            message = "Develop snapshot created successfully"
        }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED",
            "Failed to create develop snapshot: " .. tostring(writeError)))
    end
end

-- Copy develop settings from selected photo
function CatalogModule.copySettings(params, callback)
    ensureLrModules()
    local logger = getLogger()
    logger:debug("Copying develop settings from selected photo")

    local catalog = LrApplication.activeCatalog()
    local photo = catalog:getTargetPhoto()
    if not photo then
        callback(ErrorUtils.createError("PHOTO_NOT_FOUND", "No photo selected"))
        return
    end

    local success, result = ErrorUtils.safeCall(function()
        photo:copySettings()
    end)

    if success then
        callback(ErrorUtils.createSuccess({
            copied = true,
            message = "Develop settings copied successfully"
        }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED",
            "Failed to copy develop settings: " .. tostring(result)))
    end
end

-- Paste develop settings to selected photo
function CatalogModule.pasteSettings(params, callback)
    ensureLrModules()
    local logger = getLogger()
    logger:debug("Pasting develop settings to selected photo")

    local catalog = LrApplication.activeCatalog()
    local photo = catalog:getTargetPhoto()
    if not photo then
        callback(ErrorUtils.createError("PHOTO_NOT_FOUND", "No photo selected"))
        return
    end

    local writeSuccess, writeError = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Paste Develop Settings", function()
            photo:pasteSettings()
        end, { timeout = 10 })
    end)

    if writeSuccess then
        callback(ErrorUtils.createSuccess({
            pasted = true,
            message = "Develop settings pasted successfully"
        }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED",
            "Failed to paste develop settings: " .. tostring(writeError)))
    end
end

function CatalogModule.rotateLeft(params, callback)
    ensureLrModules()
    local catalog = LrApplication.activeCatalog()
    local photo = catalog:getTargetPhoto()
    if not photo then
        callback(ErrorUtils.createError("PHOTO_NOT_FOUND", "No photo selected"))
        return
    end
    local success, err = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Rotate Left", function()
            photo:rotateLeft()
        end, { timeout = 10 })
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Rotated left" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", tostring(err)))
    end
end

function CatalogModule.rotateRight(params, callback)
    ensureLrModules()
    local catalog = LrApplication.activeCatalog()
    local photo = catalog:getTargetPhoto()
    if not photo then
        callback(ErrorUtils.createError("PHOTO_NOT_FOUND", "No photo selected"))
        return
    end
    local success, err = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Rotate Right", function()
            photo:rotateRight()
        end, { timeout = 10 })
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Rotated right" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", tostring(err)))
    end
end

function CatalogModule.createVirtualCopy(params, callback)
    ensureLrModules()
    local catalog = LrApplication.activeCatalog()
    local photo = catalog:getTargetPhoto()
    if not photo then
        callback(ErrorUtils.createError("PHOTO_NOT_FOUND", "No photo selected"))
        return
    end
    local success, err = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Create Virtual Copy", function()
            photo:createVirtualCopy()
        end, { timeout = 10 })
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "Virtual copy created" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", tostring(err)))
    end
end

function CatalogModule.setMetadata(params, callback)
    ensureLrModules()
    local photoId = params.photoId
    local key = params.key
    local value = params.value

    if not photoId then
        callback(ErrorUtils.createError("MISSING_PARAM", "Photo ID is required"))
        return
    end
    if not key then
        callback(ErrorUtils.createError("MISSING_PARAM", "Metadata key is required"))
        return
    end

    local catalog = LrApplication.activeCatalog()
    catalog:withWriteAccessDo("Set Metadata", function()
        local photo = catalog:getPhotoByLocalId(tonumber(photoId))
        if not photo then
            callback(ErrorUtils.createError("PHOTO_NOT_FOUND", "Photo with ID " .. photoId .. " not found"))
            return
        end
        local success, err = ErrorUtils.safeCall(function()
            photo:setRawMetadata(key, value)
        end)
        if success then
            callback(ErrorUtils.createSuccess({ photoId = photoId, key = key, value = value, message = "Metadata set" }))
        else
            callback(ErrorUtils.createError("OPERATION_FAILED", "Failed to set metadata: " .. tostring(err)))
        end
    end, { timeout = 10 })
end

function CatalogModule.createCollection(params, callback)
    ensureLrModules()
    local name = params.name
    if not name then
        callback(ErrorUtils.createError("MISSING_PARAM", "Collection name is required"))
        return
    end
    local catalog = LrApplication.activeCatalog()
    local success, err = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Create Collection", function()
            catalog:createCollection(name, nil, true)
        end, { timeout = 10 })
    end)
    if success then
        callback(ErrorUtils.createSuccess({ name = name, message = "Collection created" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", tostring(err)))
    end
end

function CatalogModule.createSmartCollection(params, callback)
    ensureLrModules()
    local name = params.name
    if not name then
        callback(ErrorUtils.createError("MISSING_PARAM", "Smart collection name is required"))
        return
    end
    local searchDesc = params.searchDesc or {}
    local catalog = LrApplication.activeCatalog()
    local success, err = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Create Smart Collection", function()
            catalog:createSmartCollection(name, searchDesc, nil, true)
        end, { timeout = 10 })
    end)
    if success then
        callback(ErrorUtils.createSuccess({ name = name, message = "Smart collection created" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", tostring(err)))
    end
end

function CatalogModule.createCollectionSet(params, callback)
    ensureLrModules()
    local name = params.name
    if not name then
        callback(ErrorUtils.createError("MISSING_PARAM", "Collection set name is required"))
        return
    end
    local catalog = LrApplication.activeCatalog()
    local success, err = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Create Collection Set", function()
            catalog:createCollectionSet(name, nil, true)
        end, { timeout = 10 })
    end)
    if success then
        callback(ErrorUtils.createSuccess({ name = name, message = "Collection set created" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", tostring(err)))
    end
end

function CatalogModule.createKeyword(params, callback)
    ensureLrModules()
    local keyword = params.keyword
    if not keyword then
        callback(ErrorUtils.createError("MISSING_PARAM", "Keyword is required"))
        return
    end
    local catalog = LrApplication.activeCatalog()
    local success, err = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Create Keyword", function()
            catalog:createKeyword(keyword, {}, true, nil, true)
        end, { timeout = 10 })
    end)
    if success then
        callback(ErrorUtils.createSuccess({ keyword = keyword, message = "Keyword created" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", tostring(err)))
    end
end

function CatalogModule.removeKeyword(params, callback)
    ensureLrModules()
    local photoId = params.photoId
    local keyword = params.keyword
    if not photoId or not keyword then
        callback(ErrorUtils.createError("MISSING_PARAM", "Photo ID and keyword are required"))
        return
    end
    local catalog = LrApplication.activeCatalog()
    local opResult = nil
    local opError = nil
    local writeSuccess, writeErr = ErrorUtils.safeCall(function()
        catalog:withWriteAccessDo("Remove Keyword", function()
            local photo = catalog:getPhotoByLocalId(tonumber(photoId))
            if not photo then
                opError = { code = "PHOTO_NOT_FOUND", message = "Photo not found" }
                return
            end
            -- Find keyword object by name
            local keywords = photo:getRawMetadata("keywords")
            local keywordObj = nil
            if keywords then
                for _, kw in ipairs(keywords) do
                    if kw:getName() == keyword then
                        keywordObj = kw
                        break
                    end
                end
            end
            if not keywordObj then
                opError = { code = "KEYWORD_NOT_FOUND", message = "Keyword '" .. keyword .. "' not found on this photo" }
                return
            end
            photo:removeKeyword(keywordObj)
            opResult = { photoId = photoId, keyword = keyword, message = "Keyword removed" }
        end, { timeout = 10 })
    end)

    if opError then
        callback(ErrorUtils.createError(opError.code, opError.message))
    elseif writeSuccess and opResult then
        callback(ErrorUtils.createSuccess(opResult))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", tostring(writeErr)))
    end
end

function CatalogModule.setViewFilter(params, callback)
    ensureLrModules()
    local filter = params.filter or {}
    local catalog = LrApplication.activeCatalog()
    local success, err = ErrorUtils.safeCall(function()
        catalog:setViewFilter(filter)
    end)
    if success then
        callback(ErrorUtils.createSuccess({ message = "View filter set" }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", tostring(err)))
    end
end

function CatalogModule.getCurrentViewFilter(params, callback)
    ensureLrModules()
    local catalog = LrApplication.activeCatalog()
    local success, result = ErrorUtils.safeCall(function()
        return catalog:getCurrentViewFilter()
    end)
    if success then
        callback(ErrorUtils.createSuccess({ filter = result }))
    else
        callback(ErrorUtils.createError("OPERATION_FAILED", tostring(result)))
    end
end

function CatalogModule.removeFromCatalog(params, callback)
    ensureLrModules()
    local photoId = params.photoId
    if not photoId then
        callback(ErrorUtils.createError("MISSING_PARAM", "Photo ID is required"))
        return
    end
    local catalog = LrApplication.activeCatalog()
    catalog:withWriteAccessDo("Remove From Catalog", function()
        local photo = catalog:getPhotoByLocalId(tonumber(photoId))
        if not photo then
            callback(ErrorUtils.createError("PHOTO_NOT_FOUND", "Photo not found"))
            return
        end
        local success, err = ErrorUtils.safeCall(function()
            catalog:removePhoto(photo)
        end)
        if success then
            callback(ErrorUtils.createSuccess({ photoId = photoId, message = "Photo removed from catalog" }))
        else
            callback(ErrorUtils.createError("OPERATION_FAILED", tostring(err)))
        end
    end, { timeout = 10 })
end

return CatalogModule