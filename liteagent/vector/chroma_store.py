import os

os.environ['TOKENIZERS_PARALLELISM'] = 'False'

from typing import AsyncIterator, AsyncIterable, List

import chromadb
from chromadb import Collection

from liteagent.vector.vector_store import VectorStore, Document, Chunk

class Chroma(VectorStore):
    collection: Collection

    def __init__(self, collection: Collection = None, initial: List[Document] = []):

        if not collection:
            self.collection = chromadb.Client().get_or_create_collection('default')

        for document in initial:
            self.collection.add(
                ids=document.id,
                documents=document.content,
                metadatas=document.metadata
            )

    async def store(self, documents: AsyncIterable[Document]):
        async for document in documents:
            self.collection.add(
                ids=document.id,
                documents=document.content,
                metadatas=document.metadata
            )

    async def search(self, query: str, count: int) -> AsyncIterator[Chunk]:
        result = self.collection.query(query_texts=query, n_results=count)

        for chunk in zip(result['documents'], result['metadatas'], result['distances']):
            yield Chunk(
                content=chunk[0][0],
                metadata=chunk[1][0],
                distance=chunk[2][0]
            )

    async def delete(self, document: Document):
        raise NotImplementedError
