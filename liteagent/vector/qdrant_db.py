from typing import AsyncIterator, List

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct

from liteagent.tokenizers import Tokenizer, fastembed_tokenizer
from liteagent.vector import VectorDatabase, Document, Chunk


class Qdrant(VectorDatabase):
    def __init__(
        self,
        client: AsyncQdrantClient,
        collection_name: str,
        tokenizer: Tokenizer,
        dimension: int = 384
    ):
        self.client = client
        self.collection_name = collection_name
        self.tokenizer = tokenizer
        self.dimension = dimension
        self.store_batch_size = 10

    @classmethod
    async def create(
        cls,
        collection_name: str = "default",
        url: str = "http://localhost:6333",
        api_key: str = None,
        tokenizer: Tokenizer = None,
        dimension: int = 384
    ) -> 'Qdrant':
        """Create and initialize a Qdrant instance"""

        if not tokenizer:
            tokenizer = fastembed_tokenizer()

        client = AsyncQdrantClient(url=url, api_key=api_key)
        
        # Check if collection exists, if not create it
        collections = await client.get_collections()
        if collection_name not in [c.name for c in collections.collections]:
            await client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=Distance.COSINE
                )
            )
        
        return cls(
            client=client,
            collection_name=collection_name,
            tokenizer=tokenizer,
            dimension=dimension
        )

    async def store(self, documents: AsyncIterator[Document]):
        """Store documents in Qdrant"""
        batch = []

        async for document in documents:
            # Generate embedding
            embedding = await self.tokenizer.encode(document.content)
            
            point = PointStruct(
                id=document.id,
                vector=embedding.tolist(),
                payload={
                    "content": document.content,
                    **document.metadata
                }
            )
            
            batch.append(point)

            if len(batch) >= self.store_batch_size:
                await self._upsert_batch(batch)
                batch.clear()

        if batch:
            await self._upsert_batch(batch)

    async def search(self, text: str, k: int) -> AsyncIterator[Chunk]:
        """Search for similar documents in Qdrant"""
        # Generate query embedding
        query_embedding = await self.tokenizer.encode(text)
        
        # Search for similar documents
        search_results = await self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding.tolist(),
            limit=k
        )
        
        for result in search_results:
            yield Chunk(
                content=result.payload.get("content", ""),
                metadata={k: v for k, v in result.payload.items() if k != "content"},
                distance=result.score
            )

    async def delete(self, document: Document):
        """Delete a document from Qdrant"""
        await self.client.delete_points(
            collection_name=self.collection_name,
            points=[document.id]
        )

    async def _upsert_batch(self, batch: List[PointStruct]):
        """Upsert a batch of points to Qdrant"""
        await self.client.upsert(
            collection_name=self.collection_name,
            points=batch
        )


async def qdrant(
    collection_name: str = "default",
    url: str = "http://localhost:6333",
    api_key: str = None,
    tokenizer: Tokenizer = None,
    dimension: int = 384
) -> VectorDatabase:
    """
    Factory function to create and initialize a Qdrant instance.
    
    Args:
        collection_name: Name of the collection to use
        url: URL of the Qdrant server
        api_key: API key for authentication
        tokenizer: Tokenizer to use for encoding texts
        dimension: Embedding dimension
        
    Returns:
        An initialized Qdrant instance
    """

    return await Qdrant.create(
        collection_name=collection_name,
        url=url,
        api_key=api_key,
        tokenizer=tokenizer or fastembed_tokenizer(),
        dimension=dimension
    )
