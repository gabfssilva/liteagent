import os

from liteagent.internal import audit, as_coroutine

os.environ['TOKENIZERS_PARALLELISM'] = 'False'

from typing import AsyncIterable, List, Union

import chromadb
from chromadb.api.models import AsyncCollection

from liteagent.vector import VectorDatabase, Document, Chunk


class Chroma(VectorDatabase):
    collection: AsyncCollection
    store_batch_size: int

    def __init__(self, collection: AsyncCollection, store_batch_size: int = 10):
        self.collection = collection
        self.store_batch_size = store_batch_size

    @classmethod
    async def create(
        cls,
        collection: Union[AsyncCollection, str] = None
    ) -> 'Chroma':
        if not collection or isinstance(collection, str):
            client = await chromadb.AsyncHttpClient()
            collection = await client.get_or_create_collection(collection or 'default')

        return cls(collection=collection)

    async def store(self, documents: AsyncIterable[Document]):
        batch = []

        async for document in documents:
            batch.append(document)

            if len(batch) >= self.store_batch_size:
                await self._upsert_batch(batch)
                batch.clear()

        if batch:
            await self._upsert_batch(batch)

    async def search(self, query: str, k: int) -> AsyncIterable[Chunk]:
        result = await self.collection.query(query_texts=query, n_results=k)

        for chunk in zip(result['documents'], result['metadatas'], result['distances']):
            yield Chunk(
                content=chunk[0][0],
                metadata=chunk[1][0],
                distance=chunk[2][0]
            )

    async def delete(self, document: Document):
        await self.collection.delete(ids=document.id)

    async def _upsert_batch(self, batch: List[Document]):
        await self.collection.upsert(
            ids=[doc.id for doc in batch],
            documents=[doc.content for doc in batch],
            metadatas=[doc.metadata for doc in batch]
        )


async def chroma(
    collection: Union[AsyncCollection, str] = None,
) -> VectorDatabase: return await Chroma.create(collection)


class ChromaInMemory(VectorDatabase):
    def __init__(self):
        from chromadb import Client, Settings
        client = Client(Settings(anonymized_telemetry=False, is_persistent=False))
        self.collection = client.get_or_create_collection(
            name="in_memory_collection"
        )
        self.store_batch_size = 10

    async def store(self, documents: AsyncIterable[Document]):
        batch = []

        async for document in documents:
            batch.append(document)

            if len(batch) >= self.store_batch_size:
                await self._upsert_batch(batch)
                batch.clear()

        if batch:
            await self._upsert_batch(batch)

    async def search(self, query: str, k: int) -> AsyncIterable[Chunk]:
        results = await self._query(query, k)

        for i in range(len(results['ids'][0])):
            yield Chunk(
                content=results['documents'][0][i],
                metadata=results['metadatas'][0][i],
                distance=results['distances'][0][i] if 'distances' in results else 0.0
            )

    @as_coroutine
    def _query(self, query, k):
        return self.collection.query(
            query_texts=[query],
            n_results=k
        )

    @as_coroutine
    def delete(self, document: Document):
        self.collection.delete(ids=[document.id])

    @as_coroutine
    def _upsert_batch(self, batch: List[Document]):
        self.collection.upsert(
            ids=[doc.id for doc in batch],
            documents=[doc.content for doc in batch],
            metadatas=[doc.metadata for doc in batch]
        )


def chroma_in_memory() -> VectorDatabase:
    return ChromaInMemory()
