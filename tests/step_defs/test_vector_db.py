"""
BDD tests for Vector Database & RAG - Document Storage and Retrieval.

Validates that:
- In-memory vector database stores and retrieves documents
- Chunking strategies work correctly
- Semantic search returns relevant results
- RAG pipeline integrates with agents
"""
from pytest_bdd import scenarios, given, when, then, parsers
from pytest import fixture, skip
import asyncio
import functools


def async_to_sync(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))
    return wrapper


# Load all scenarios from vector_db.feature
scenarios('../features/vector_db.feature')


# ==================== FIXTURES ====================

@fixture
def vector_db_context():
    """Context to store test state."""
    return {}


@fixture
def check_vector_dependencies():
    """Check if vector DB dependencies are available."""
    try:
        from liteagent.vector import in_memory, Document, Chunk, word_chunking
        from liteagent.tokenizers import fastembed_tokenizer
        return True
    except (ImportError, AttributeError):
        return False


@fixture
def vector_modules():
    """Load vector modules."""
    from liteagent import vector
    from liteagent import tokenizers

    return {
        'vector': vector,
        'tokenizer': tokenizers
    }


# ==================== GIVEN STEPS ====================

@given("vector database dependencies are available")
def given_vector_deps_available(check_vector_dependencies, vector_db_context):
    """Check if vector database dependencies are available."""
    if not check_vector_dependencies:
        skip("Vector DB dependencies not available")
    vector_db_context['deps_available'] = True


@given("test documents about programming, AI, and databases")
def given_test_documents(vector_modules, vector_db_context):
    """Create test documents."""
    Document = vector_modules['vector'].Document

    docs = [
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

    vector_db_context['documents'] = docs


@given("documents are stored in the database")
def given_documents_stored(vector_modules, vector_db_context):
    """Store documents in the database."""
    in_memory = vector_modules['vector'].in_memory
    fastembed_tokenizer = vector_modules['tokenizer'].fastembed_tokenizer

    db = in_memory(tokenizer=fastembed_tokenizer())
    docs = vector_db_context.get('documents', [])

    async def _store():
        async def doc_generator():
            for doc in docs:
                yield doc
        await db.store(doc_generator())

    async_to_sync(_store)()
    vector_db_context['database'] = db


@given(parsers.parse("a word chunking strategy with size {size:d} and overlap {overlap:d}"))
def given_word_chunking_strategy(vector_modules, vector_db_context, size, overlap):
    """Create a word chunking strategy."""
    word_chunking = vector_modules['vector'].word_chunking
    strategy = word_chunking(chunk_size=size, overlap=overlap)
    vector_db_context['chunking_strategy'] = strategy


@given("documents about dogs, cats, and cars")
def given_animal_documents(vector_modules, vector_db_context):
    """Create documents with related but different concepts."""
    Document = vector_modules['vector'].Document

    docs = [
        Document(id="1", content="Dogs are loyal and friendly pets that love to play."),
        Document(id="2", content="Cats are independent animals that enjoy lounging around."),
        Document(id="3", content="Cars use gasoline or electricity to transport people."),
    ]

    vector_db_context['documents'] = docs


# ==================== WHEN STEPS ====================

@when("I store documents in the in-memory database")
def when_store_documents(vector_modules, vector_db_context):
    """Store documents in the database."""
    in_memory = vector_modules['vector'].in_memory
    fastembed_tokenizer = vector_modules['tokenizer'].fastembed_tokenizer

    db = in_memory(tokenizer=fastembed_tokenizer())
    docs = vector_db_context.get('documents', [])

    async def _store():
        async def doc_generator():
            for doc in docs:
                yield doc
        await db.store(doc_generator())

    async_to_sync(_store)()
    vector_db_context['database'] = db


@when(parsers.parse('I search for "{query}" with k={k:d}'))
def when_search_database(vector_db_context, query, k):
    """Search the database."""
    db = vector_db_context.get('database')

    async def _search():
        results = []
        async for chunk in db.search(query, k=k):
            results.append(chunk)
        return results

    results = async_to_sync(_search)()
    vector_db_context['search_results'] = results


@when(parsers.parse("I chunk text with {word_count:d} words"))
def when_chunk_text_with_words(vector_db_context, word_count):
    """Chunk text with specific word count."""
    strategy = vector_db_context.get('chunking_strategy')
    text = " ".join([f"word{i}" for i in range(word_count)])

    async def _chunk():
        return await strategy.chunk(text)

    chunks = async_to_sync(_chunk)()
    vector_db_context['chunks'] = chunks
    vector_db_context['original_text'] = text


@when(parsers.parse('I chunk text "{text}"'))
def when_chunk_text(vector_db_context, text):
    """Chunk specific text."""
    strategy = vector_db_context.get('chunking_strategy')

    async def _chunk():
        return await strategy.chunk(text)

    chunks = async_to_sync(_chunk)()
    vector_db_context['chunks'] = chunks
    vector_db_context['original_text'] = text


@when(parsers.parse('I create a Document with id "{doc_id}", content "{content}", and metadata'))
def when_create_document_with_metadata(vector_modules, vector_db_context, doc_id, content):
    """Create a document with metadata."""
    Document = vector_modules['vector'].Document
    doc = Document(
        id=doc_id,
        content=content,
        metadata={"key": "value"}
    )
    vector_db_context['document'] = doc


@when(parsers.parse('I create a Document with id "{doc_id}" and content "{content}"'))
def when_create_document_minimal(vector_modules, vector_db_context, doc_id, content):
    """Create a document with minimal fields."""
    Document = vector_modules['vector'].Document
    doc = Document(
        id=doc_id,
        content=content
    )
    vector_db_context['document'] = doc


@when(parsers.parse("I create a Chunk with content, metadata, and distance {distance:f}"))
def when_create_chunk(vector_modules, vector_db_context, distance):
    """Create a chunk with all fields."""
    Chunk = vector_modules['vector'].Chunk
    chunk = Chunk(
        content="Test chunk content",
        metadata={"source": "test"},
        distance=distance
    )
    vector_db_context['chunk'] = chunk


# ==================== THEN STEPS ====================

@then(parsers.parse("the database should contain {count:d} chunks"))
def then_database_has_chunks(vector_db_context, count):
    """Validate number of chunks in database."""
    db = vector_db_context.get('database')
    assert len(db.chunks) == count, f"Expected {count} chunks, got {len(db.chunks)}"


@then(parsers.parse("the database should contain {count:d} vectors"))
def then_database_has_vectors(vector_db_context, count):
    """Validate number of vectors in database."""
    db = vector_db_context.get('database')
    assert len(db.vectors) == count, f"Expected {count} vectors, got {len(db.vectors)}"


@then(parsers.parse("I should get at least {count:d} search result"))
def then_get_at_least_results(vector_db_context, count):
    """Validate minimum number of search results."""
    results = vector_db_context.get('search_results', [])
    assert len(results) >= count, f"Expected at least {count} results, got {len(results)}"


@then(parsers.parse("I should get at least {count:d} search results"))
def then_get_at_least_results_plural(vector_db_context, count):
    """Validate minimum number of search results (plural)."""
    then_get_at_least_results(vector_db_context, count)


@then(parsers.parse("I should get exactly {count:d} search results"))
def then_get_exactly_results(vector_db_context, count):
    """Validate exact number of search results."""
    results = vector_db_context.get('search_results', [])
    assert len(results) == count, f"Expected exactly {count} results, got {len(results)}"


@then(parsers.parse('the first result should contain "{text}"'))
def then_first_result_contains(vector_modules, vector_db_context, text):
    """Validate first result contains text."""
    results = vector_db_context.get('search_results', [])
    assert len(results) > 0, "No results found"

    Chunk = vector_modules['vector'].Chunk
    first_result = results[0]
    assert isinstance(first_result, Chunk), f"Expected Chunk, got {type(first_result)}"
    assert text.lower() in first_result.content.lower(), \
        f"Expected '{text}' in content: {first_result.content}"


@then("the first result should be most relevant to AI/ML")
def then_first_result_relevant_to_ai(vector_db_context):
    """Validate first result is relevant to AI/ML."""
    results = vector_db_context.get('search_results', [])
    assert len(results) > 0, "No results found"

    first_result = results[0]
    keywords = ["machine", "learning", "intelligence", "ai"]
    content_lower = first_result.content.lower()
    assert any(word in content_lower for word in keywords), \
        f"Expected AI/ML keywords in: {first_result.content}"


@then(parsers.parse("I should get {count:d} chunk"))
def then_should_get_chunk(vector_db_context, count):
    """Validate exact number of chunks (singular)."""
    chunks = vector_db_context.get('chunks', [])
    assert len(chunks) == count, f"Expected {count} chunk(s), got {len(chunks)}"


@then(parsers.parse("I should get {count:d} chunks"))
def then_should_get_chunks(vector_db_context, count):
    """Validate exact number of chunks."""
    chunks = vector_db_context.get('chunks', [])
    assert len(chunks) == count, f"Expected {count} chunks, got {len(chunks)}"


@then(parsers.parse("I should get at least {count:d} chunks"))
def then_should_get_at_least_chunks(vector_db_context, count):
    """Validate minimum number of chunks."""
    chunks = vector_db_context.get('chunks', [])
    assert len(chunks) >= count, f"Expected at least {count} chunks, got {len(chunks)}"


@then(parsers.parse('the first chunk should contain "{text}"'))
def then_first_chunk_contains(vector_db_context, text):
    """Validate first chunk contains text."""
    chunks = vector_db_context.get('chunks', [])
    assert len(chunks) > 0, "No chunks found"
    assert text in chunks[0], f"Expected '{text}' in first chunk: {chunks[0]}"


@then(parsers.parse('the last chunk should contain "{text}"'))
def then_last_chunk_contains(vector_db_context, text):
    """Validate last chunk contains text."""
    chunks = vector_db_context.get('chunks', [])
    assert len(chunks) > 0, "No chunks found"
    assert text in chunks[-1], f"Expected '{text}' in last chunk: {chunks[-1]}"


@then("the chunk should equal the original text")
def then_chunk_equals_original(vector_db_context):
    """Validate chunk equals original text."""
    chunks = vector_db_context.get('chunks', [])
    original = vector_db_context.get('original_text')
    assert len(chunks) == 1, f"Expected 1 chunk, got {len(chunks)}"
    assert chunks[0] == original, f"Expected chunk to equal original text"


@then(parsers.parse('the Document should have id "{doc_id}"'))
def then_document_has_id(vector_db_context, doc_id):
    """Validate document ID."""
    doc = vector_db_context.get('document')
    assert doc.id == doc_id, f"Expected id '{doc_id}', got '{doc.id}'"


@then(parsers.parse('the Document should have content "{content}"'))
def then_document_has_content(vector_db_context, content):
    """Validate document content."""
    doc = vector_db_context.get('document')
    assert doc.content == content, f"Expected content '{content}', got '{doc.content}'"


@then("the Document should have metadata")
def then_document_has_metadata(vector_db_context):
    """Validate document has metadata."""
    doc = vector_db_context.get('document')
    assert doc.metadata == {"key": "value"}, f"Expected metadata, got {doc.metadata}"


@then("the Document should have empty metadata")
def then_document_has_empty_metadata(vector_db_context):
    """Validate document has empty metadata."""
    doc = vector_db_context.get('document')
    assert doc.metadata == {}, f"Expected empty metadata, got {doc.metadata}"


@then(parsers.parse('the Chunk should have content "{content}"'))
def then_chunk_has_content(vector_db_context, content):
    """Validate chunk content."""
    chunk = vector_db_context.get('chunk')
    assert chunk.content == content, f"Expected content '{content}', got '{chunk.content}'"


@then("the Chunk should have metadata")
def then_chunk_has_metadata(vector_db_context):
    """Validate chunk has metadata."""
    chunk = vector_db_context.get('chunk')
    assert chunk.metadata == {"source": "test"}, f"Expected metadata, got {chunk.metadata}"


@then(parsers.parse("the Chunk should have distance {distance:f}"))
def then_chunk_has_distance(vector_db_context, distance):
    """Validate chunk distance."""
    chunk = vector_db_context.get('chunk')
    assert chunk.distance == distance, f"Expected distance {distance}, got {chunk.distance}"


@then("the top result should be about animals")
def then_top_result_about_animals(vector_db_context):
    """Validate top result is about animals."""
    results = vector_db_context.get('search_results', [])
    assert len(results) > 0, "No results found"

    top_content = results[0].content.lower()
    keywords = ["dog", "cat", "pet", "animal"]
    assert any(word in top_content for word in keywords), \
        f"Expected animal keywords in: {top_content}"


@then("the top result should not be about cars")
def then_top_result_not_about_cars(vector_db_context):
    """Validate top result is not about cars."""
    results = vector_db_context.get('search_results', [])
    assert len(results) > 0, "No results found"

    top_content = results[0].content.lower()
    assert "car" not in top_content, f"Did not expect 'car' in: {top_content}"
