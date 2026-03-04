from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class LightroomRequest(BaseModel):
    """JSON-RPC request format"""
    id: str
    command: str
    params: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[int] = None

class LightroomResponse(BaseModel):
    """JSON-RPC response format"""
    id: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

class LightroomError(BaseModel):
    """Error response format"""
    code: str
    message: str
    severity: str = "error"
    details: Optional[Dict[str, Any]] = None