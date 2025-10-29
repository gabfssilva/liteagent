Feature: Built-in Tools
  As a developer using LiteAgent
  I want to use built-in tools that come with the library
  So that agents can execute code, perform calculations, and access time information

  Background:
    Given the built-in tools are loaded

  Scenario: Python runner executes simple Python code
    Given an agent with the "python_runner" tool
    When I ask the agent "Calculate 5 + 3 using Python"
    Then the response should contain "8"

  Scenario: Python runner makes HTTP requests
    Given an agent with the "python_runner" tool
    When I ask the agent "Use requests to GET https://httpbin.org/json and return the 'slideshow' property from the JSON"
    Then the response should contain either "slideshow" or "author"

  Scenario: Calculator evaluates mathematical expressions
    Given an agent with the "calculator" tool
    When I ask the agent "What is 10 * 5 + 2?"
    Then the response should contain "52"

  Scenario: Calculator evaluates complex expressions
    Given an agent with the "calculator" tool
    When I ask the agent "Calculate (100 / 4) + (3 ** 2)"
    Then the response should contain "34"

  Scenario: Today returns current date
    Given an agent with the "today" tool
    When I ask the agent "What is today's date?"
    Then the response should contain the current year

  Scenario: Clock is an eager tool executed automatically
    Given an agent with the "clock" tool
    When I ask the agent "What is the current time?"
    Then the response should match pattern "time|:|current"

  Scenario: Agent uses multiple built-in tools together
    Given an agent with the tools "python_runner, calculator"
    When I ask the agent "Calculate 15 * 3"
    Then the response should contain "45"
