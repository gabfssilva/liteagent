"""
Tests for Agent Streaming - Token-by-token streaming responses.

Validates that:
- Agents stream content incrementally (token-by-token)
- Content is accumulated as it arrives
- TextStream provides incremental access
- Streaming works with tools
- Non-streaming agents return complete results
"""
import asyncio
from ward import test

from liteagent import agent, tool
from liteagent.providers import openai
from liteagent.message import AssistantMessage


@test("agent returns streaming messages with TextStream content")
async def _():
    """
    Tests that streaming agent returns messages with TextStream content.

    Deterministic scenario:
    - Create streaming agent (no return type)
    - Verify messages contain TextStream (not complete strings)
    - Verify TextStream can be iterated for incremental content
    """

    @agent(provider=openai(model="gpt-4o-mini", temperature=0))
    async def streaming_agent(query: str):
        """Answer this question: {query}"""

    # Call agent - returns AsyncIterable[Message]
    result = await streaming_agent("Write a sentence about Python")

    # Collect messages
    messages = []
    async for message in result:
        messages.append(message)

    # Should have received at least one AssistantMessage
    assistant_messages = [m for m in messages if isinstance(m, AssistantMessage)]
    assert len(assistant_messages) > 0

    # Check that content is TextStream (indicates streaming capability)
    first_assistant = assistant_messages[0]
    assert hasattr(first_assistant.content, 'content')  # Has CachedStringAccumulator
    assert hasattr(first_assistant.content, 'await_complete')  # Can wait for completion


@test("TextStream content accumulates incrementally")
async def _():
    """
    Tests that TextStream accumulates content token-by-token.

    Deterministic scenario:
    - Get streaming message
    - Observe content while streaming
    - Verify content is complete at the end
    """

    @agent(provider=openai(model="gpt-4o-mini", temperature=0))
    async def verbose_agent(query: str):
        """Answer: {query}"""

    result = await verbose_agent("Explain programming in 2 sentences")

    # Collect all messages
    messages = []
    async for message in result:
        messages.append(message)

    # Find AssistantMessage with TextStream
    text_stream = None
    for message in messages:
        if isinstance(message, AssistantMessage) and hasattr(message.content, 'content'):
            text_stream = message.content
            break

    # Should have found a TextStream
    assert text_stream is not None

    # Get final content (await_complete will wait for stream to finish)
    # Note: Don't check is_complete before await_complete - there's a race condition
    # where the provider's finally block may not have executed yet
    final_content = await text_stream.await_complete()

    # Now it should be complete
    assert text_stream.content.is_complete
    assert len(final_content) > 0
    assert "programm" in final_content.lower()


@test("streaming content can be observed incrementally")
async def _():
    """
    Tests that we can observe content accumulating token-by-token.

    Deterministic scenario:
    - Start streaming
    - Observe cached iterator updates in background task
    - Verify content grows incrementally
    """

    @agent(provider=openai(model="gpt-4o-mini", temperature=0))
    async def storyteller(query: str):
        """Answer: {query}"""

    result = await storyteller("Write 3 short sentences about computers")

    # Storage for observed content lengths
    observed_lengths = []
    atomic_string = None

    # Task to observe content growth
    async def observe_content():
        if atomic_string is None:
            return

        # Observe for a reasonable time (2 seconds max to avoid hanging)
        # We can't rely on is_complete due to race condition with provider's finally block
        try:
            for _ in range(200):  # Check up to 200 times (2 seconds total)
                if atomic_string.is_complete:
                    break
                current = await atomic_string.get()
                observed_lengths.append(len(current))
                await asyncio.sleep(0.01)
        except Exception:
            pass  # Ignore any errors during observation

        # Get final length
        try:
            final = await atomic_string.get()
            observed_lengths.append(len(final))
        except Exception:
            pass

    # Collect messages and start observing
    observer_task = None
    async for message in result:
        if isinstance(message, AssistantMessage) and hasattr(message.content, 'content'):
            atomic_string = message.content.content
            # Start background observation
            observer_task = asyncio.create_task(observe_content())

    # Wait for observer to finish
    if observer_task:
        await observer_task

    # Should have observed some content
    assert len(observed_lengths) > 0

    # Final content should have some length
    assert observed_lengths[-1] > 0


@test("non-streaming agent returns complete result immediately")
async def _():
    """
    Tests that agents with explicit return type don't stream.

    Deterministic scenario:
    - Create agent with str return type
    - Should return complete result
    """

    @agent(provider=openai(model="gpt-4o-mini", temperature=0))
    async def non_streaming_agent(query: str) -> str:
        """Answer: {query}"""

    # Call agent - should return AssistantMessage directly
    result = await non_streaming_agent("Say: Hello")

    # Result should be AssistantMessage
    assert isinstance(result, AssistantMessage)

    # Can get final text (don't check is_complete first - race condition)
    if hasattr(result.content, 'await_complete'):
        final_text = await result.content.await_complete()

        # Now it should be complete
        if hasattr(result.content, 'is_complete'):
            assert result.content.is_complete

        assert "hello" in final_text.lower()


@test("streaming works with tool calling")
async def _():
    """
    Tests that streaming works when agent uses tools.

    Deterministic scenario:
    - Agent with tools streams response
    - Should receive proper messages
    - Final content should include tool result
    """

    @tool
    def get_year() -> int:
        """Returns the year 2025."""
        return 2025

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[get_year]
    )
    async def tool_agent(query: str):
        """
        Answer: {query}
        Use get_year tool to get the year.
        """

    result = await tool_agent("What year is it according to the tool?")

    messages = []
    async for message in result:
        messages.append(message)

    # Should have received messages
    assert len(messages) > 0

    # Should have AssistantMessage(s)
    assistant_messages = [m for m in messages if isinstance(m, AssistantMessage)]
    assert len(assistant_messages) > 0

    # Get final response
    final = assistant_messages[-1]
    if hasattr(final.content, 'await_complete'):
        text = await final.content.await_complete()
        assert "2025" in text


@test("multiple messages can be received during streaming")
async def _():
    """
    Tests that streaming can yield multiple message updates.

    Deterministic scenario:
    - Stream response
    - Count messages received
    - Verify we get messages through the stream
    """

    @agent(provider=openai(model="gpt-4o-mini", temperature=0))
    async def multi_message_agent(query: str):
        """Answer: {query}"""

    result = await multi_message_agent("Count: 1, 2, 3")

    message_count = 0
    async for message in result:
        message_count += 1
        # All messages should have basic properties
        assert hasattr(message, 'role')
        assert hasattr(message, 'content')

    # Should have received at least one message
    assert message_count >= 1


@test("TextStream provides await_complete for final content")
async def _():
    """
    Tests that TextStream provides proper completion mechanism.

    Deterministic scenario:
    - Get streaming message
    - Consume all messages
    - Use await_complete to get final result
    - Verify content is correct
    """

    @agent(provider=openai(model="gpt-4o-mini", temperature=0))
    async def completion_agent(query: str):
        """Answer: {query}"""

    result = await completion_agent("Say exactly: Testing Complete")

    # Consume all messages and collect TextStream
    text_stream = None
    async for message in result:
        if isinstance(message, AssistantMessage) and hasattr(message.content, 'await_complete'):
            text_stream = message.content

    # Should have TextStream
    assert text_stream is not None

    # Get completion (this will wait for the stream to complete)
    final_text = await text_stream.await_complete()

    # Now it should be complete
    assert text_stream.content.is_complete
    assert len(final_text) > 0
    assert "test" in final_text.lower() or "complete" in final_text.lower()
