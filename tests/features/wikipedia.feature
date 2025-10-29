Feature: Wikipedia Tool - Wikipedia Search and Article Retrieval
  As a developer using LiteAgent
  I want to search Wikipedia and retrieve articles
  So that agents can access Wikipedia knowledge

  # Search Tests
  Scenario: Wikipedia search returns formatted results
    When I search Wikipedia for "Python" with limit 2
    Then I should get 2 search results
    And the first result should have title "Python (programming language)"
    And the first result should have description "High-level programming language"
    And the first result should have a valid Wikipedia URL

  Scenario: Wikipedia search handles empty results
    When I search Wikipedia for "NonExistentQuery123456" with limit 5
    Then I should get 0 search results

  Scenario: Wikipedia search handles missing description
    When I search Wikipedia for a page without description
    Then I should get 1 search result
    And the first result should have description "No description available"

  # Article Retrieval Tests
  Scenario: Get complete article validates Wikipedia URL
    When I get article from non-Wikipedia URL "https://example.com/article"
    Then I should get an error containing "Wikipedia"

  Scenario: Get complete article fetches and converts to markdown
    When I get article from Wikipedia URL "https://en.wikipedia.org/wiki/Python_(programming_language)"
    Then I should get a non-empty markdown result
    And the result should be a string

  Scenario: Get complete article handles missing content div
    When I get article from Wikipedia URL with missing content
    Then I should get an error containing "content body"
