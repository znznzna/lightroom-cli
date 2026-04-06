"""
Lightroom Python SDK - Async interface for Lightroom Classic
"""

from .client import LightroomClient
from .exceptions import (
    ConnectionError,
    LightroomSDKError,
    ParameterError,
    ParameterOutOfRangeError,
    PhotoNotSelectedError,
    TimeoutError,
)

__version__ = "1.2.2"
__all__ = [
    "LightroomClient",
    "LightroomSDKError",
    "ConnectionError",
    "TimeoutError",
    "PhotoNotSelectedError",
    "ParameterError",
    "ParameterOutOfRangeError",
]
