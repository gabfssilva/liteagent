Feature: Agent Teams
  As a developer using LiteAgent
  I want to coordinate multiple specialized agents
  So that complex tasks can be delegated to the right expert

  Background:
    Given the OpenAI provider is available

  Scenario: Coordinator delegates tasks to technical specialist
    Given a tech specialist with technical specifications tool
    And a coordinator that delegates to tech specialist
    When I ask the coordinator "What are the processor and RAM specifications of the Laptop X1?"
    Then the coordinator response should contain "i7"
    And the coordinator response should contain "16"

  Scenario: Coordinator orchestrates multiple specialists for pricing
    Given a sales specialist with pricing tool
    And a support specialist with warranty tool
    And a multi-team coordinator
    When I ask the multi-team coordinator "What is the price of the Laptop X1?"
    Then the multi-team response should contain "5999"

  Scenario: Coordinator orchestrates multiple specialists for warranty
    Given a sales specialist with pricing tool
    And a support specialist with warranty tool
    And a multi-team coordinator
    When I ask the multi-team coordinator "What is the warranty period for the Laptop X1?"
    Then the multi-team response should contain "2"
    And the multi-team response should contain "year"

  Scenario: Teams work with structured output
    Given a catalog specialist with product info tool
    And an availability checker that uses catalog specialist
    When I check availability for "Is the Laptop X1 available?"
    Then the availability report should have product_name "Laptop X1"
    And the availability report should have is_available true
    And the availability report status should indicate available
