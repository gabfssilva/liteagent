from abc import abstractmethod
from typing import AsyncIterable

from liteagent.vector import Document, Chunk

class VectorDatabase:
    @abstractmethod
    async def store(self, documents: AsyncIterable[Document]):
        pass

    @abstractmethod
    async def search(self, text: str, k: int) -> AsyncIterable[Chunk]:
        pass

    @abstractmethod
    async def delete(self, document: Document):
        pass
