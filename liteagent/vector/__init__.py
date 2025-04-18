__all__ = [
    "VectorDatabase",
    "Document",
    "Chunk",
    "Chunks",
    "loaders",
    "ChunkingStrategy",
    "word_chunking",
    "token_chunking",
    "in_memory",
    "chroma",
    "chroma_in_memory",
    "pgvector",
    "qdrant"
]

# Import lightweight classes immediately
from .models import Document, Chunk, Chunks
from .vector_db import VectorDatabase
from .chunk import ChunkingStrategy, token_chunking, word_chunking

# Lazy import for heavier modules
def __getattr__(name):
    if name == 'loaders':
        from . import loaders as module
        globals()[name] = module
        return module
    elif name == 'in_memory':
        from .in_memory_db import in_memory as module
        globals()[name] = module
        return module
    elif name == 'chroma':
        from .chroma_db import chroma as module
        globals()[name] = module
        return module
    elif name == 'chroma_in_memory':
        from .chroma_db import chroma_in_memory as module
        globals()[name] = module
        return module
    elif name == 'pgvector':
        from .pgvector_db import pgvector as module
        globals()[name] = module
        return module
    elif name == 'qdrant':
        from .qdrant_db import qdrant as module
        globals()[name] = module
        return module
    
    raise AttributeError(f"module 'liteagent.vector' has no attribute '{name}'")
