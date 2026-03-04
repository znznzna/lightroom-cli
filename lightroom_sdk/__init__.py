"""
Lightroom Python SDK - Async interface for Lightroom Classic
"""
from .client import LightroomClient
from .exceptions import (
    LightroomSDKError,
    ConnectionError,
    TimeoutError,
    PhotoNotSelectedError,
    ParameterError,
    ParameterOutOfRangeError
)

__version__ = "1.0.0"
__all__ = [
    "LightroomClient",
    "LightroomSDKError",
    "ConnectionError", 
    "TimeoutError",
    "PhotoNotSelectedError",
    "ParameterError",
    "ParameterOutOfRangeError"
]