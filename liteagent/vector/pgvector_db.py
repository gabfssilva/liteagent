from typing import AsyncIterator, List
import os

import numpy as np
from sqlalchemy import Column, Integer, String, JSON, create_engine, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import async_sessionmaker
from pgvector.sqlalchemy import Vector

from liteagent.tokenizers import Tokenizer, fastembed_tokenizer
from liteagent.vector import VectorDatabase, Document, Chunk

Base = declarative_base()


class VectorEntry(Base):
    __tablename__ = 'vector_entries'

    id = Column(Integer, primary_key=True)
    doc_id = Column(String, nullable=False, index=True)
    content = Column(String, nullable=False)
    doc_metadata = Column(JSON, nullable=False)
    embedding = Column(Vector(384))  # Default dimension for fastembed


class PgVector(VectorDatabase):
    def __init__(
        self,
        connection_string: str,
        tokenizer: Tokenizer,
        dimension: int = 384,
        table_name: str = "vector_entries"
    ):
        self.tokenizer = tokenizer
        self.dimension = dimension
        self.table_name = table_name

        # Create async engine and session
        self.engine = create_async_engine(connection_string)
        self.async_session = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def initialize(self):
        """Initialize database tables"""
        async with self.engine.begin() as conn:
            # Create extension if it doesn't exist
            await conn.execute('CREATE EXTENSION IF NOT EXISTS vector')
            # Create tables
            await conn.run_sync(Base.doc_metadata.create_all)
        return self

    async def store(self, documents: AsyncIterator[Document]):
        """Store documents in the database"""
        async with self.async_session() as session:
            async with session.begin():
                async for doc in documents:
                    # Generate embedding
                    embedding = await self.tokenizer.encode(doc.content)

                    # Create vector entry
                    vector_entry = VectorEntry(
                        doc_id=doc.id,
                        content=doc.content,
                        metadata=doc.metadata,
                        embedding=embedding.tolist()
                    )

                    session.add(vector_entry)

    async def search(self, text: str, k: int) -> AsyncIterator[Chunk]:
        """Search for similar documents"""
        # Generate query embedding
        query_embedding = await self.tokenizer.encode(text)

        async with self.async_session() as session:
            # Use the <-> operator for cosine distance
            query = f"""
            SELECT doc_id, content, metadata,
                   1 - (embedding <=> :embedding) as similarity
            FROM vector_entries
            ORDER BY embedding <=> :embedding
            LIMIT :limit
            """

            result = await session.execute(
                query,
                {"embedding": query_embedding.tolist(), "limit": k}
            )

            for row in result:
                yield Chunk(
                    content=row.content,
                    metadata=row.metadata,
                    distance=float(row.similarity)
                )

    async def delete(self, document: Document):
        """Delete a document from the database"""
        async with self.async_session() as session:
            async with session.begin():
                await session.execute(
                    f"DELETE FROM vector_entries WHERE doc_id = :doc_id",
                    {"doc_id": document.id}
                )


async def pgvector(
    connection_string: str,
    tokenizer: Tokenizer = fastembed_tokenizer(),
    dimension: int = 384,
    table_name: str = "vector_entries"
) -> VectorDatabase:
    """
    Factory function to create and initialize a PgVector instance.

    Args:
        connection_string: PostgreSQL connection string (postgresql+asyncpg://user:pass@host/dbname)
        tokenizer: Tokenizer to use for encoding texts
        dimension: Embedding dimension
        table_name: Name of the table to use

    Returns:
        An initialized PgVector instance
    """
    db = PgVector(
        connection_string=connection_string,
        tokenizer=tokenizer,
        dimension=dimension,
        table_name=table_name
    )
    return await db.initialize()
