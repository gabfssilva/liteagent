Feature: Structured Output
  As a developer using LiteAgent
  I want agents to return structured Pydantic models
  So that I can get type-safe, validated responses

  Scenario: Classify even positive number
    When I classify the number 4
    Then the structured output should have field "number" equal to 4
    And the structured output should have field "is_even" equal to "true"
    And the structured output should have field "is_positive" equal to "true"
    And the structured output should have field "classification" equal to "even_positive"

  Scenario: Classify odd positive number
    When I classify the number 7
    Then the structured output should have field "number" equal to 7
    And the structured output should have field "is_even" equal to "false"
    And the structured output should have field "is_positive" equal to "true"
    And the structured output should have field "classification" equal to "odd_positive"

  Scenario: Classify even negative number
    When I classify the number -6
    Then the structured output should have field "number" equal to -6
    And the structured output should have field "is_even" equal to "true"
    And the structured output should have field "is_positive" equal to "false"
    And the structured output should have field "classification" equal to "even_negative"

  Scenario: Classify odd negative number
    When I classify the number -3
    Then the structured output should have field "number" equal to -3
    And the structured output should have field "is_even" equal to "false"
    And the structured output should have field "is_positive" equal to "false"
    And the structured output should have field "classification" equal to "odd_negative"

  Scenario: Extract personal information from natural text
    When I extract person info from "John is 25 years old and lives in San Francisco"
    Then the structured output should be of type PersonInfo
    And the person name should be "john"
    And the person age should be 25
    And the person city should contain "francisco"
