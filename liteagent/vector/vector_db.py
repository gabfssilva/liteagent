from abc import abstractmethod
from typing import AsyncIterator

from liteagent.vector import Document, Chunk

class VectorDatabase:
    @abstractmethod
    async def store(self, documents: AsyncIterator[Document]):
        pass

    @abstractmethod
    async def search(self, text: str, k: int) -> AsyncIterator[Chunk]:
        pass

    @abstractmethod
    async def delete(self, document: Document):
        pass
