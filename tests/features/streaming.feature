Feature: Agent Streaming
  As a developer using LiteAgent
  I want agents to stream responses token-by-token
  So that I can provide real-time feedback to users

  Background:
    Given the OpenAI provider is available

  Scenario: Streaming agent returns messages with TextStream
    Given a streaming agent without return type
    When I call the streaming agent with "Write a sentence about Python"
    Then the streaming result should have at least 1 messages
    And the streaming result should contain AssistantMessage

  Scenario: TextStream content accumulates and completes
    Given a streaming agent without return type
    When I stream a response for "Explain programming in 2 sentences"
    Then the streamed content should be non-empty
    And the streamed content should contain "programm"
    And the stream should be marked as complete

  Scenario: Non-streaming agent returns complete result immediately
    Given a non-streaming agent with return type
    When I call the non-streaming agent with "Say: Hello"
    Then the non-streaming result should be AssistantMessage
    And the non-streaming result should contain "hello"

  Scenario: Streaming works with tool calling
    Given a streaming agent with tools
    When I call the streaming agent with tools with "What year is it?"
    Then the tool streaming result should have messages
    And the tool streaming result should contain "2025"
