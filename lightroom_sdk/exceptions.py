from typing import Optional, Dict, Any

class LightroomSDKError(Exception):
    """Base exception for SDK errors"""
    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}

class ConnectionError(LightroomSDKError):
    """Socket connection errors"""
    pass

class TimeoutError(LightroomSDKError):
    """Command timeout errors"""
    pass

class PhotoNotSelectedError(LightroomSDKError):
    """No photo selected in Lightroom"""
    def __init__(self, message: str = "Please select a photo in Lightroom", code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=code or "NO_PHOTO_SELECTED", details=details)

class ParameterError(LightroomSDKError):
    """Invalid parameter errors"""
    pass

class ParameterOutOfRangeError(ParameterError):
    """Parameter value outside valid range"""
    def __init__(self, message: Optional[str] = None, param: Optional[str] = None, value: Optional[float] = None, min_val: Optional[float] = None, max_val: Optional[float] = None, code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if message is None and param is not None and value is not None and min_val is not None and max_val is not None:
            message = f"Parameter '{param}' value {value} outside valid range [{min_val}, {max_val}]"
        elif message is None:
            message = "Parameter value outside valid range"
        super().__init__(message, code=code or "INVALID_PARAM_VALUE", details=details)

class PhotoNotFoundError(LightroomSDKError):
    """Photo with given ID not found"""
    def __init__(self, message: Optional[str] = None, photo_id: Optional[str] = None, code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if message is None and photo_id is not None:
            message = f"Photo with ID '{photo_id}' not found"
        elif message is None:
            message = "Photo not found"
        super().__init__(message, code=code or "PHOTO_NOT_FOUND", details=details)

class CatalogAccessError(LightroomSDKError):
    """Failed to access Lightroom catalog"""
    def __init__(self, message: str = "Failed to access Lightroom catalog", code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=code or "CATALOG_ACCESS_FAILED", details=details)

class WriteAccessBlockedError(LightroomSDKError):
    """Lightroom write operation blocked"""
    def __init__(self, message: str = "Lightroom write operation blocked", code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=code or "WRITE_ACCESS_BLOCKED", details=details)

class ResourceUnavailableError(LightroomSDKError):
    """Required Lightroom module unavailable"""
    def __init__(self, message: str = "Required Lightroom module unavailable", code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=code or "RESOURCE_UNAVAILABLE", details=details)

class HandlerError(LightroomSDKError):
    """Lua execution error"""
    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=code or "HANDLER_ERROR", details=details)

# Error code mapping from Lightroom
ERROR_CODE_MAP = {
    "MISSING_PHOTO_ID": PhotoNotSelectedError,
    "NO_PHOTO_SELECTED": PhotoNotSelectedError,
    "PHOTO_NOT_FOUND": PhotoNotFoundError,
    "INVALID_PARAM": ParameterError,
    "INVALID_PARAM_VALUE": ParameterOutOfRangeError,
    "INVALID_PARAM_TYPE": ParameterError,
    "HANDLER_ERROR": HandlerError,
    "CONNECTION_FAILED": ConnectionError,
    "CATALOG_ACCESS_FAILED": CatalogAccessError,
    "WRITE_ACCESS_BLOCKED": WriteAccessBlockedError,
    "RESOURCE_UNAVAILABLE": ResourceUnavailableError,
}