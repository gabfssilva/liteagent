from typing import List, AsyncIterable
import numpy as np
from fastembed import TextEmbedding

from liteagent.tokenizers import Tokenizer, fastembed_tokenizer
from liteagent.vector import VectorDatabase, Document, Chunk


class InMemory(VectorDatabase):
    model: TextEmbedding
    vectors: List[np.ndarray]
    chunks: List[Chunk]

    def __init__(self, tokenizer: Tokenizer) -> None:
        self.tokenizer = tokenizer
        self.vectors = []
        self.chunks = []

    async def store(self, documents: AsyncIterable[Document]):
        async for doc in documents:
            embedding = await self.tokenizer.encode(doc.content)
            chunk = Chunk(content=doc.content, metadata=doc.metadata)
            self.vectors.append(embedding)
            self.chunks.append(chunk)

    async def search(self, query: str, k: int = 1) -> AsyncIterable[Chunk]:
        query_embedding = await self.tokenizer.encode(query)
        similarities = [self._cosine_similarity(query_embedding, v) for v in self.vectors]
        nearest_indices = np.argsort(similarities)[-k:][::-1]

        for i in nearest_indices:
            chunk = Chunk(
                content=self.chunks[i].content,
                metadata=self.chunks[i].metadata,
                distance=similarities[i]
            )
            yield chunk

    @staticmethod
    def _cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

    async def delete(self, document: Document):
        raise NotImplementedError


def in_memory(tokenizer: Tokenizer = None) -> VectorDatabase:
    return InMemory(tokenizer or fastembed_tokenizer())
