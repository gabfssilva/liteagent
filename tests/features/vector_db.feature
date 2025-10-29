Feature: Vector Database & RAG - Document Storage and Retrieval
  As a developer using LiteAgent
  I want to store and retrieve documents in a vector database
  So that agents can perform semantic search and RAG operations

  Background:
    Given vector database dependencies are available

  # Document Storage
  Scenario: In-memory vector database stores documents
    Given test documents about programming, AI, and databases
    When I store documents in the in-memory database
    Then the database should contain 3 chunks
    And the database should contain 3 vectors

  Scenario: In-memory vector database searches and returns relevant results
    Given test documents about programming, AI, and databases
    And documents are stored in the database
    When I search for "programming language Python" with k=1
    Then I should get at least 1 search result
    And the first result should contain "python"

  # Chunking Strategies
  Scenario: Word chunking strategy splits text by words
    Given a word chunking strategy with size 10 and overlap 2
    When I chunk text with 25 words
    Then I should get at least 2 chunks
    And the first chunk should contain "word0"
    And the last chunk should contain "word24"

  Scenario: Word chunking handles small text correctly
    Given a word chunking strategy with size 100 and overlap 10
    When I chunk text "This is a short text with only a few words."
    Then I should get 1 chunk
    And the chunk should equal the original text

  # Data Models
  Scenario: Document model validates required fields
    When I create a Document with id "test1", content "Test content", and metadata
    Then the Document should have id "test1"
    And the Document should have content "Test content"
    And the Document should have metadata

  Scenario: Document model allows minimal fields
    When I create a Document with id "test2" and content "Minimal content"
    Then the Document should have id "test2"
    And the Document should have content "Minimal content"
    And the Document should have empty metadata

  Scenario: Chunk model includes distance score
    When I create a Chunk with content, metadata, and distance 0.85
    Then the Chunk should have content "Test chunk content"
    And the Chunk should have metadata
    And the Chunk should have distance 0.85

  # Search Operations
  Scenario: Vector database returns top k results
    Given test documents about programming, AI, and databases
    And documents are stored in the database
    When I search for "artificial intelligence machine learning" with k=2
    Then I should get exactly 2 search results
    And the first result should be most relevant to AI/ML

  Scenario: Semantic search finds related concepts
    Given documents about dogs, cats, and cars
    And documents are stored in the database
    When I search for "animals and pets" with k=2
    Then I should get at least 1 search result
    And the top result should be about animals
    And the top result should not be about cars
