Feature: Agent Teams
  As a developer using LiteAgent
  I want to coordinate multiple specialized agents
  So that complex tasks can be delegated to the right expert

  Scenario: Coordinator delegates tasks to specialist
    Given a tech specialist with product specifications
    And a coordinator that delegates to the tech specialist
    When I ask the coordinator "What are the processor and RAM specifications of the Laptop X1?"
    Then the response should contain "i7"
    And the response should contain "16"

  Scenario: Coordinator orchestrates multiple specialists
    Given a sales specialist with pricing information
    And a support specialist with warranty information
    And a coordinator that delegates to both specialists
    When I ask the coordinator about price
    Then the price response should contain "5999"
    When I ask the coordinator about warranty
    Then the warranty response should contain "2"
    And the warranty response should contain "year"
