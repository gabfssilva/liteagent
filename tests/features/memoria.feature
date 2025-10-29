Feature: Memoria Tool - Long-term Memory Storage
  As a developer using LiteAgent
  I want to store and retrieve long-term memories
  So that agents can remember information across sessions

  Background:
    Given a memoria tool with simple storage

  Scenario: Store single memory and return ID
    When I store a memory with content "Remember: user prefers Python" and type "semantic"
    Then the store operation should return 1 memory ID
    And the first memory ID should be "0"

  Scenario: Store multiple memories and return IDs
    When I store multiple memories:
      | content                     | type       |
      | User likes cats             | semantic   |
      | User's birthday is Jan 1    | episodic   |
      | To send email: use smtp     | procedural |
    Then the store operation should return 3 memory IDs
    And the memory IDs should be "0", "1", "2"

  Scenario: Store supports different memory types
    When I store memories with different types
    Then I should be able to retrieve memories by type
    And the semantic memory should have type "semantic"
    And the episodic memory should have type "episodic"
    And the procedural memory should have type "procedural"

  Scenario: Retrieve returns empty dict when no memories
    Given an empty memoria storage
    When I retrieve all memories
    Then the result should be an empty dict

  Scenario: Retrieve returns all stored memories
    Given I have stored 2 memories
    When I retrieve all memories
    Then the result should contain 2 memories
    And memory "0" should have content "First memory"
    And memory "1" should have content "Second memory"

  Scenario: Update modifies existing memory content
    Given I have stored a memory with ID "0"
    When I update memory "0" with new content "Updated content"
    Then the update should succeed
    And retrieving memory "0" should show "Updated content"

  Scenario: Update returns not found for non-existent ID
    When I try to update memory "999" with content "New content"
    Then the update should return "not found"

  Scenario: Delete removes memory successfully
    Given I have stored a memory with ID "0"
    When I delete memory "0"
    Then the delete should succeed
    And memory "0" should no longer exist

  Scenario: Delete returns not found for non-existent ID
    When I try to delete memory "999"
    Then the delete should return "not found"

  Scenario: Full CRUD cycle works correctly
    When I store a memory "CRUD test memory"
    And I retrieve the memory
    And I update the memory with "Updated CRUD memory"
    And I delete the memory
    Then the memory should no longer exist
