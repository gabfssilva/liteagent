Feature: Tool Calling
  As a developer using LiteAgent
  I want agents to call tools and use returned data
  So that agents can access external information and perform computations

  Background:
    Given the OpenAI provider is available

  Scenario: Agent calls a single tool and uses returned data
    Given an agent with the "get_user_profile" tool
    When I ask the agent "What is the full name and occupation of the user?"
    Then the response should contain either "Gabriel Silva" or "Gabriel"
    And the response should contain either "Software Engineer" or "engineer"

  Scenario: Agent calls multiple tools in sequence
    Given an agent with the tools "get_user_profile, calculate_age_in_days"
    When I ask the agent "How many days approximately has the user lived? First get their age then calculate."
    Then the response should contain either "11680" or "11,680"

  Scenario: Agent calls tools with structured parameters
    Given an agent with the "calculate_age_in_days" tool
    When I ask the agent "How many days are in 25 years?"
    Then the response should contain either "9125" or "9,125"
