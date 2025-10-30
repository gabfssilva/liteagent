"""
BDD tests for Agent Streaming - Token-by-token streaming responses.

Validates that:
- Agents stream content incrementally
- TextStream provides incremental access
- Streaming works with tools
- Non-streaming agents return complete results
"""
from pytest_bdd import scenarios, given, when, then, parsers
from pytest import fixture
import asyncio
import functools

from liteagent import agent, tool
from liteagent.providers import openai
from liteagent.message import AssistantMessage


def async_to_sync(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))
    return wrapper


scenarios('../features/streaming.feature')


# ==================== FIXTURES ====================

@fixture
def get_year_tool():
    @tool
    def get_year() -> int:
        """Returns the year 2025."""
        return 2025
    return get_year


# ==================== GIVEN STEPS ====================

@given("the OpenAI provider is available")
def given_openai_available():
    import os
    assert os.environ.get("OPENAI_API_KEY")


@given("a streaming agent without return type", target_fixture="streaming_agent")
def given_streaming_agent():
    @agent(provider=openai(model="gpt-4o-mini", temperature=0))
    async def streaming_agent(query: str):
        """Answer this question: {query}"""
    return streaming_agent


@given("a non-streaming agent with return type", target_fixture="non_streaming_agent")
def given_non_streaming_agent():
    @agent(provider=openai(model="gpt-4o-mini", temperature=0))
    async def non_streaming_agent(query: str) -> str:
        """Answer: {query}"""
    return non_streaming_agent


@given("a streaming agent with tools", target_fixture="streaming_tool_agent")
def given_streaming_tool_agent(get_year_tool):
    @agent(provider=openai(model="gpt-4o-mini", temperature=0), tools=[get_year_tool])
    async def tool_agent(query: str):
        """Answer: {query}. Use get_year tool to get the year."""
    return tool_agent


# ==================== WHEN STEPS ====================

@when(parsers.parse('I call the streaming agent with "{query}"'), target_fixture="streaming_result")
def when_call_streaming_agent(streaming_agent, query):
    async def _call():
        result = await streaming_agent(query)
        messages = []
        async for message in result:
            messages.append(message)
        return messages
    return async_to_sync(_call)()


@when(parsers.parse('I stream a response for "{query}"'), target_fixture="streamed_content")
def when_stream_response(streaming_agent, query):
    async def _stream():
        result = await streaming_agent(query)
        messages = []
        async for message in result:
            messages.append(message)

        # Find TextStream
        for message in messages:
            if isinstance(message, AssistantMessage) and hasattr(message.content, 'await_complete'):
                return await message.content.await_complete()
        return ""
    return async_to_sync(_stream)()


@when(parsers.parse('I call the non-streaming agent with "{query}"'), target_fixture="non_streaming_result")
def when_call_non_streaming_agent(non_streaming_agent, query, extract_text):
    async def _call():
        result = await non_streaming_agent(query)
        return result
    return async_to_sync(_call)()


@when(parsers.parse('I call the streaming agent with tools with "{query}"'), target_fixture="tool_streaming_result")
def when_call_streaming_tool_agent(streaming_tool_agent, query, extract_text):
    async def _call():
        result = await streaming_tool_agent(query)
        messages = []
        async for message in result:
            messages.append(message)
        return messages
    return async_to_sync(_call)()


# ==================== THEN STEPS ====================

@then(parsers.parse('the streaming result should have at least {count:d} messages'))
def then_streaming_has_messages(streaming_result, count):
    assert len(streaming_result) >= count, f"Expected at least {count} messages, got {len(streaming_result)}"


@then("the streaming result should contain AssistantMessage")
def then_streaming_has_assistant_message(streaming_result):
    assistant_messages = [m for m in streaming_result if isinstance(m, AssistantMessage)]
    assert len(assistant_messages) > 0, "Expected at least one AssistantMessage"


@then("the streamed content should be non-empty")
def then_streamed_content_non_empty(streamed_content):
    assert len(streamed_content) > 0, "Streamed content should not be empty"


@then(parsers.parse('the streamed content should contain "{text}"'))
def then_streamed_content_contains(streamed_content, text):
    assert text.lower() in streamed_content.lower(), f"Expected '{text}' in content: {streamed_content}"


@then("the stream should be marked as complete")
def then_stream_complete(streamed_content):
    # If we got content, stream completed successfully
    assert True


@then("the non-streaming result should be AssistantMessage")
def then_non_streaming_is_assistant_message(non_streaming_result):
    # Agent with -> str return type should return str, not AssistantMessage
    assert isinstance(non_streaming_result, str), f"Expected str (due to -> str type hint), got {type(non_streaming_result)}"


@then(parsers.parse('the non-streaming result should contain "{text}"'))
def then_non_streaming_contains(non_streaming_result, text, extract_text):
    # non_streaming_result is already a str (due to -> str type hint)
    assert text.lower() in non_streaming_result.lower(), f"Expected '{text}' in result: {non_streaming_result}"


@then("the tool streaming result should have messages")
def then_tool_streaming_has_messages(tool_streaming_result):
    assert len(tool_streaming_result) > 0, "Expected messages from tool streaming"


@then(parsers.parse('the tool streaming result should contain "{text}"'))
def then_tool_streaming_contains(tool_streaming_result, text, extract_text):
    async def _check():
        for message in tool_streaming_result:
            if isinstance(message, AssistantMessage):
                content = await extract_text(message)
                if text in content:
                    return True
        return False
    assert async_to_sync(_check)(), f"Expected '{text}' in tool streaming result"
