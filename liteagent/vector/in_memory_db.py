from typing import List, AsyncIterator
import numpy as np
from fastembed import TextEmbedding
from liteagent.vector import VectorDatabase, Document, Chunk

class InMemory(VectorDatabase):
    model: TextEmbedding
    vectors: List[np.ndarray]
    chunks: List[Chunk]

    def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5", chunk_size: int = 3000, overlap: int = 500) -> None:
        self.model = TextEmbedding(model_name)
        self.vectors = []
        self.chunks = []
        self.chunk_size = chunk_size
        self.overlap = overlap

    def _split_text(self, text: str) -> List[str]:
        words = text.split()
        chunks = []
        for i in range(0, len(words), self.chunk_size - self.overlap):
            chunk = " ".join(words[i:i + self.chunk_size])
            chunks.append(chunk)
        return chunks

    async def store(self, documents: AsyncIterator[Document]):
        async for doc in documents:
            chunks = self._split_text(doc.content)
            chunk_embeddings = list(self.model.embed(chunks))

            for chunk_text, embedding in zip(chunks, chunk_embeddings):
                chunk = Chunk(
                    content=chunk_text,
                    metadata=doc.metadata
                )
                self.vectors.append(embedding)
                self.chunks.append(chunk)

    async def search(self, query: str, k: int = 1) -> AsyncIterator[Chunk]:
        query_embedding = next(self.model.embed([query]))
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
