from typing import List

from pydantic import BaseModel

class Document(BaseModel):
    id: str
    content: str
    metadata: dict = {}

class Chunk(BaseModel):
    content: str
    metadata: dict = {}
    distance: float = 0.0

class Chunks(BaseModel):
    chunks: List[Chunk]
