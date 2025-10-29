Feature: Cached Iterator
  As a developer using LiteAgent
  I want cached async iteration with replay support
  So that multiple consumers can iterate over the same data stream

  Scenario: CachedStringAccumulator appends text correctly
    Given a CachedStringAccumulator
    When I append "Hello"
    And I append " "
    And I append "World"
    And I complete the accumulator
    Then the final value should be "Hello World"
    And the accumulator should be complete

  Scenario: CachedStringAccumulator await_complete waits for completion
    Given a CachedStringAccumulator
    When I append values with delays and complete in background
    And I await completion
    Then the final value should be "First Second Third"

  Scenario: CachedStringAccumulator cannot mutate after completion
    Given a completed CachedStringAccumulator with value "Initial"
    When I try to append " More"
    Then it should raise a RuntimeError with message "Cannot append to completed iterator"

  Scenario: CachedStringAccumulator await_as_json parses JSON correctly
    Given a CachedStringAccumulator
    When I append JSON content in parts
    And I parse as JSON
    Then the JSON should have field "name" equal to "John"
    And the JSON should have field "age" equal to 30

  Scenario: AppendableIterator yields appended values
    Given an AppendableIterator
    When I append values "First", "Second", "Third" and complete
    And I iterate over the values
    Then I should receive values in order: "First", "Second", "Third"

  Scenario: AppendableIterator prevents append after complete
    Given a completed AppendableIterator
    When I try to append "Should fail"
    Then it should raise a RuntimeError with message "Cannot append to completed iterator"

  Scenario: CachedAsyncIterator caches values from source
    Given a CachedAsyncIterator with source yielding "A", "B", "C"
    When I iterate over the cached values
    Then I should receive values: "A", "B", "C"
    And the iterator should be complete

  Scenario: CachedAsyncIterator allows replay for late consumers
    Given a CachedAsyncIterator with delayed source
    When the first consumer iterates fully
    And a second consumer starts late
    Then both consumers should receive: "First", "Second", "Third"

  Scenario: CachedAsyncIterator supports multiple concurrent consumers
    Given a CachedAsyncIterator with source yielding 5 values
    When two consumers iterate concurrently
    Then both should receive all 5 values in order

  Scenario: CachedAsyncIterator await_complete waits for source exhaustion
    Given a CachedAsyncIterator with slow source
    When I await completion
    Then the iterator should be complete
