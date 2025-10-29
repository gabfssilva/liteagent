Feature: Error Handling
  As a developer using LiteAgent
  I want agents to handle errors gracefully
  So that the application doesn't crash unexpectedly

  Background:
    Given the OpenAI provider is available

  Scenario: Tool that raises exception is handled gracefully
    Given an agent with a tool that always fails
    When I ask the agent to "Try to use the failing tool"
    Then the agent should respond without crashing
    And the response should be non-empty

  Scenario: Tool with invalid parameter types fails gracefully
    Given an agent with a strict type tool
    When I ask the agent to "Use strict_type_tool with the number 42"
    Then the agent should handle the tool correctly
    And the response should contain "42"

  Scenario: Invalid API key raises appropriate error
    Given an OpenAI provider with invalid API key
    When I try to create an agent with invalid provider
    Then an authentication error should be raised

  Scenario: Tool with missing required parameter shows clear error
    Given an agent with a tool requiring parameters
    When I ask the agent to "Use requires_param with name=John and age=25"
    Then the agent should provide both parameters successfully
    And the response should contain "john"
    And the response should contain "25"

  Scenario: Multiple tool errors in sequence are handled
    Given an agent with multiple tools that can fail
    When I ask the agent to "Try to accomplish the task"
    Then the agent should handle errors and continue
    And the response should be non-empty
