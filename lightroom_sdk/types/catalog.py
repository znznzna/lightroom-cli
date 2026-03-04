from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class Photo(BaseModel):
    """Photo object from catalog"""
    id: int
    filename: str
    path: str
    fileFormat: str
    folderPath: str
    captureTime: str
    isVirtualCopy: bool = False

class PhotoList(BaseModel):
    """List of photos with metadata"""
    count: int
    photos: List[Photo]

class Folder(BaseModel):
    """Folder in catalog"""
    name: str
    path: str
    photoCount: int
    subfolders: List['Folder'] = []

class Collection(BaseModel):
    """Photo collection"""
    id: int
    name: str
    photoCount: int
    parent: Optional[str] = None

# Update forward references
Folder.model_rebuild()