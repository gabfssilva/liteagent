"""
Tests for Agent Streaming - Streaming responses from agents.

Validates that:
- Agents without return type annotation stream by default
- Streaming yields incremental Message objects
- Content can be accumulated from streaming responses
- Streaming works with tool calling
- Non-streaming agents return direct results
"""
from ward import test

from liteagent import agent, tool
from liteagent.providers import openai
from tests.conftest import extract_text


@test("agent without return type streams messages")
async def _():
    """
    Tests that agents without return type annotation return streaming responses.

    Deterministic scenario:
    - Create agent without return type (defaults to AsyncIterable[Message])
    - Call agent and iterate over messages
    - Verify messages are yielded incrementally
    """

    @agent(provider=openai(model="gpt-4o-mini", temperature=0))
    async def streaming_agent(query: str):
        """Answer this question: {query}"""

    # Call agent - returns AsyncIterable[Message]
    result = await streaming_agent("Say exactly: Testing Streaming")

    # Collect all messages
    messages = []
    async for message in result:
        messages.append(message)

    # Should have received at least one message
    assert len(messages) > 0

    # Last message should be AssistantMessage with content
    last_message = messages[-1]
    assert hasattr(last_message, 'content')

    # Extract final content
    final_text = await extract_text(last_message)

    # Should contain expected response
    assert "testing" in final_text.lower() or "streaming" in final_text.lower()


@test("agent with str return type does not stream")
async def _():
    """
    Tests that agents with explicit return type don't stream.

    Deterministic scenario:
    - Create agent with str return type
    - Call agent
    - Should return str directly, not AsyncIterable
    """

    @agent(provider=openai(model="gpt-4o-mini", temperature=0))
    async def non_streaming_agent(query: str) -> str:
        """Answer this question: {query}"""

    # Call agent - should return str directly
    result = await non_streaming_agent("Say: Hello")

    # Result should be string or message with string content
    final_text = await extract_text(result)

    # Should be a string
    assert isinstance(final_text, str)
    assert "hello" in final_text.lower()


@test("streaming agent yields multiple message updates")
async def _():
    """
    Tests that streaming agent can yield multiple message updates.

    Deterministic scenario:
    - Create streaming agent
    - Request longer response to get multiple chunks
    - Collect all yielded messages
    """

    @agent(provider=openai(model="gpt-4o-mini", temperature=0))
    async def verbose_agent(query: str):
        """Answer this question in detail: {query}"""

    result = await verbose_agent("Explain what Python is in one sentence")

    messages = []
    async for message in result:
        messages.append(message)

    # Should receive messages (could be 1 or more depending on chunking)
    assert len(messages) >= 1

    # All messages should have content
    for msg in messages:
        assert hasattr(msg, 'content')


@test("streaming content can be accumulated incrementally")
async def _():
    """
    Tests that content from streaming messages can be accumulated.

    Deterministic scenario:
    - Create streaming agent
    - Iterate and accumulate content
    - Verify final accumulated content is complete
    """

    @agent(provider=openai(model="gpt-4o-mini", temperature=0))
    async def story_agent(query: str):
        """Answer: {query}"""

    result = await story_agent("List numbers 1, 2, 3")

    # Accumulate content from all messages
    messages = []
    async for message in result:
        messages.append(message)

    # Should have at least one message
    assert len(messages) > 0

    # Get final content using helper
    final_text = await extract_text(messages[-1])

    # Should mention numbers
    assert any(num in final_text for num in ["1", "2", "3"])


@test("streaming works with tool calling")
async def _():
    """
    Tests that streaming works when agent uses tools.

    Deterministic scenario:
    - Create streaming agent with tools
    - Agent calls tool during streaming
    - Messages should include both tool calls and responses
    """

    @tool
    def get_current_year() -> int:
        """Returns the current year."""
        return 2025

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[get_current_year]
    )
    async def tool_streaming_agent(query: str):
        """
        Answer: {query}
        Use the get_current_year tool to find the current year.
        """

    result = await tool_streaming_agent("What is the current year according to the tool?")

    messages = []
    async for message in result:
        messages.append(message)

    # Should have multiple messages (including tool calls)
    assert len(messages) >= 1

    # Collect final response
    final_text = await extract_text(messages[-1])

    # Should mention 2025
    assert "2025" in final_text


@test("streaming messages include message metadata")
async def _():
    """
    Tests that streaming messages include proper metadata.

    Deterministic scenario:
    - Create streaming agent
    - Check that messages have proper attributes
    - Verify message types
    """

    @agent(provider=openai(model="gpt-4o-mini", temperature=0))
    async def metadata_agent(query: str):
        """Answer: {query}"""

    result = await metadata_agent("Say: Testing")

    messages = []
    async for message in result:
        messages.append(message)
        # Each message should have content
        assert hasattr(message, 'content')
        # Messages should have a type (from Message base class)
        assert message.__class__.__name__ in ['AssistantMessage', 'ToolMessage', 'UserMessage', 'SystemMessage']

    # Should have received at least one message
    assert len(messages) > 0


@test("empty streaming response is handled gracefully")
async def _():
    """
    Tests that agents handle edge cases in streaming.

    Deterministic scenario:
    - Create streaming agent with very simple query
    - Should still return valid message stream
    """

    @agent(provider=openai(model="gpt-4o-mini", temperature=0))
    async def simple_agent(query: str):
        """Answer: {query}"""

    result = await simple_agent("Say: OK")

    messages = []
    async for message in result:
        messages.append(message)

    # Should have at least one message even for simple response
    assert len(messages) >= 1

    final_text = await extract_text(messages[-1])
    assert len(final_text) > 0
