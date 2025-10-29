Feature: Stateful Sessions
  As a developer using LiteAgent
  I want sessions to maintain conversation history
  So that agents can remember context across multiple messages

  Background:
    Given a basic OpenAI agent
    And a stateful session

  Scenario: Sessions accumulate multiple facts throughout conversation
    When I send the message "My favorite color is blue." to the session and ignore response
    And I send the message "I work as a software engineer." to the session and ignore response
    And I send the message "I live in San Francisco." to the session and ignore response
    And I send the message "Tell me: what is my favorite color, profession, and city?" to the session
    Then the session response should contain "blue"
    And the session response should contain "engineer"
    And the session response should contain "Francisco"

  Scenario: Reset clears session memory
    When I send the message "My secret number is 42." to the session and ignore response
    And I reset the session
    And I send the message "What was my secret number?" to the session
    Then the session response should NOT contain "42"
