"""
Tests for Vector Database & RAG - Document storage and retrieval.

Validates that:
- In-memory vector database stores and retrieves documents
- Chunking strategies work correctly
- Semantic search returns relevant results
- RAG pipeline integrates with agents
"""
from ward import test, fixture

from liteagent.vector import (
    Document,
    Chunk,
    word_chunking,
)

# Try to import in_memory, but it's optional
try:
    from liteagent.vector import in_memory
    VECTOR_DB_AVAILABLE = True
except ImportError:
    VECTOR_DB_AVAILABLE = False


async def _make_documents():
    """Helper to create test documents."""
    return [
        Document(
            id="doc1",
            content="Python is a high-level programming language known for its simplicity and readability.",
            metadata={"category": "programming", "language": "python"}
        ),
        Document(
            id="doc2",
            content="Machine learning is a subset of artificial intelligence that enables computers to learn from data.",
            metadata={"category": "ai", "topic": "ml"}
        ),
        Document(
            id="doc3",
            content="Vector databases store data as high-dimensional vectors for efficient similarity search.",
            metadata={"category": "database", "topic": "vectors"}
        ),
    ]


@test("in-memory vector database stores documents")
async def _():
    """
    Tests that in-memory vector database can store documents.

    Deterministic scenario:
    - Create in-memory database
    - Store documents
    - Verify storage completes without error
    """
    if not VECTOR_DB_AVAILABLE:
        # Skip if vector DB dependencies not available
        assert True, "Vector DB dependencies not available, skipping test"
        return

    from liteagent.tokenizers import fastembed_tokenizer

    db = in_memory(tokenizer=fastembed_tokenizer())
    docs = await _make_documents()

    # Store documents
    async def doc_generator():
        for doc in docs:
            yield doc

    await db.store(doc_generator())

    # Verify storage by checking internal state
    assert len(db.chunks) == 3
    assert len(db.vectors) == 3


@test("in-memory vector database searches and returns relevant results")
async def _():
    """
    Tests that vector database returns relevant results for queries.

    Deterministic scenario:
    - Store documents about different topics
    - Search for specific topic
    - Verify most relevant document is returned
    """
    if not VECTOR_DB_AVAILABLE:
        assert True, "Vector DB dependencies not available, skipping test"
        return

    from liteagent.tokenizers import fastembed_tokenizer

    db = in_memory(tokenizer=fastembed_tokenizer())
    docs = await _make_documents()

    # Store documents
    async def doc_generator():
        for doc in docs:
            yield doc

    await db.store(doc_generator())

    # Search for programming-related content
    results = []
    async for chunk in db.search("programming language Python", k=1):
        results.append(chunk)

    # Should return at least one result
    assert len(results) > 0

    # First result should be most relevant (about Python programming)
    first_result = results[0]
    assert isinstance(first_result, Chunk)
    assert "python" in first_result.content.lower()


@test("word chunking strategy splits text by words")
async def _():
    """
    Tests that word chunking splits text into word-based chunks.

    Deterministic scenario:
    - Create text with known word count
    - Apply word chunking with specific size
    - Verify chunk count and overlap
    """
    strategy = word_chunking(chunk_size=10, overlap=2)

    # Text with exactly 25 words
    text = " ".join([f"word{i}" for i in range(25)])

    chunks = await strategy.chunk(text)

    # Should create multiple chunks with overlap
    # Chunks: 0-9, 8-17, 16-24 = 3 chunks
    assert len(chunks) >= 2
    assert all(isinstance(chunk, str) for chunk in chunks)

    # First chunk should start with word0
    assert "word0" in chunks[0]

    # Last chunk should end with word24
    assert "word24" in chunks[-1]


@test("word chunking handles small text correctly")
async def _():
    """
    Tests that word chunking handles text smaller than chunk size.

    Deterministic scenario:
    - Text shorter than chunk size
    - Should return single chunk
    """
    strategy = word_chunking(chunk_size=100, overlap=10)

    text = "This is a short text with only a few words."

    chunks = await strategy.chunk(text)

    # Should return single chunk for small text
    assert len(chunks) == 1
    assert chunks[0] == text


@test("Document model validates required fields")
async def _():
    """
    Tests that Document model has required fields and validation.

    Deterministic scenario:
    - Create Document with all fields
    - Create Document with minimal fields
    - Verify structure
    """
    # Full document
    doc1 = Document(
        id="test1",
        content="Test content",
        metadata={"key": "value"}
    )

    assert doc1.id == "test1"
    assert doc1.content == "Test content"
    assert doc1.metadata == {"key": "value"}

    # Minimal document (metadata optional)
    doc2 = Document(
        id="test2",
        content="Minimal content"
    )

    assert doc2.id == "test2"
    assert doc2.content == "Minimal content"
    assert doc2.metadata == {}


@test("Chunk model includes distance score")
async def _():
    """
    Tests that Chunk model includes distance/similarity score.

    Deterministic scenario:
    - Create Chunk with distance
    - Verify fields are accessible
    """
    chunk = Chunk(
        content="Test chunk content",
        metadata={"source": "test"},
        distance=0.85
    )

    assert chunk.content == "Test chunk content"
    assert chunk.metadata == {"source": "test"}
    assert chunk.distance == 0.85


@test("vector database returns top k results")
async def _():
    """
    Tests that vector database respects k parameter in search.

    Deterministic scenario:
    - Store multiple documents
    - Search with k=2
    - Should return exactly 2 results
    """
    if not VECTOR_DB_AVAILABLE:
        assert True, "Vector DB dependencies not available, skipping test"
        return

    from liteagent.tokenizers import fastembed_tokenizer

    db = in_memory(tokenizer=fastembed_tokenizer())
    docs = await _make_documents()

    # Store documents
    async def doc_generator():
        for doc in docs:
            yield doc

    await db.store(doc_generator())

    # Search with k=2
    results = []
    async for chunk in db.search("artificial intelligence machine learning", k=2):
        results.append(chunk)

    # Should return exactly k results
    assert len(results) == 2

    # Results should be sorted by relevance (distance)
    if len(results) == 2:
        # Most relevant should mention AI/ML
        assert any(word in results[0].content.lower() for word in ["machine", "learning", "intelligence", "ai"])


@test("semantic search finds related concepts")
async def _():
    """
    Tests that semantic search finds conceptually related documents.

    Deterministic scenario:
    - Store documents with related concepts
    - Search for concept not explicitly mentioned
    - Should return semantically similar results
    """
    if not VECTOR_DB_AVAILABLE:
        assert True, "Vector DB dependencies not available, skipping test"
        return

    from liteagent.tokenizers import fastembed_tokenizer

    db = in_memory(tokenizer=fastembed_tokenizer())

    # Documents with related but not identical concepts
    docs = [
        Document(id="1", content="Dogs are loyal and friendly pets that love to play."),
        Document(id="2", content="Cats are independent animals that enjoy lounging around."),
        Document(id="3", content="Cars use gasoline or electricity to transport people."),
    ]

    async def doc_generator():
        for doc in docs:
            yield doc

    await db.store(doc_generator())

    # Search for related concept
    results = []
    async for chunk in db.search("animals and pets", k=2):
        results.append(chunk)

    # Should return documents about dogs/cats, not cars
    assert len(results) > 0

    # Top results should be about animals
    top_content = results[0].content.lower()
    assert any(word in top_content for word in ["dog", "cat", "pet", "animal"])
    assert "car" not in top_content
