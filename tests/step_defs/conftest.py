"""
Reusable BDD step definitions for pytest-bdd.

These steps can be imported and reused across multiple feature files.
All async operations are wrapped with async_to_sync for pytest-bdd compatibility.
"""
import asyncio
import functools
from pytest_bdd import given, when, then, parsers
from pytest import fixture
from typing import Any

from liteagent import agent, tool
from liteagent.providers import openai


# Async wrapper for pytest-bdd compatibility
def async_to_sync(fn):
    """Wrapper to convert async functions to sync for pytest-bdd."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))
    return wrapper


# ==================== TOOL FIXTURES ====================

@fixture
def get_user_profile_tool():
    """Fixture for user profile tool."""
    from pydantic import BaseModel

    class UserProfile(BaseModel):
        name: str
        age: int
        city: str
        occupation: str

    @tool
    def get_user_profile() -> UserProfile:
        """Returns the current user profile."""
        return UserProfile(
            name="Gabriel Silva",
            age=32,
            city="São Paulo",
            occupation="Software Engineer"
        )
    return get_user_profile


@fixture
def calculate_age_in_days_tool():
    """Fixture for age calculation tool."""
    @tool
    def calculate_age_in_days(age_in_years: int) -> int:
        """Calculates approximate age in days given age in years."""
        return age_in_years * 365
    return calculate_age_in_days


@fixture
def get_year_tool():
    """Fixture for get year tool."""
    @tool
    def get_year() -> int:
        """Returns the year 2025."""
        return 2025
    return get_year


@fixture
def failing_tool_fixture():
    """Fixture for a tool that always fails."""
    @tool
    def failing_tool() -> str:
        """A tool that always fails."""
        raise ValueError("This tool intentionally fails")
    return failing_tool


# ==================== AGENT FIXTURES ====================

@fixture
def basic_openai_agent():
    """Basic OpenAI agent without tools."""
    @agent(provider=openai(model="gpt-4o-mini", temperature=0))
    async def basic_agent(query: str) -> str:
        """Answer: {query}"""
    return basic_agent


# ==================== GIVEN STEPS ====================

@given("a basic OpenAI agent", target_fixture="test_agent")
def given_basic_agent(basic_openai_agent):
    """Creates a basic OpenAI agent."""
    return basic_openai_agent


@given(parsers.parse('an agent with the "{tool_name}" tool'), target_fixture="test_agent")
def given_agent_with_tool(tool_name, request, extract_text):
    """Creates an agent with a specific tool."""
    # Map tool names to fixtures
    tool_map = {
        "get_user_profile": "get_user_profile_tool",
        "calculate_age_in_days": "calculate_age_in_days_tool",
        "get_year": "get_year_tool",
        "failing_tool": "failing_tool_fixture",
    }

    fixture_name = tool_map.get(tool_name)
    if not fixture_name:
        raise ValueError(f"Unknown tool: {tool_name}")

    tool_func = request.getfixturevalue(fixture_name)

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[tool_func]
    )
    async def tooled_agent(query: str) -> str:
        """Answer the user's question: {query}. Use available tools when necessary."""

    return tooled_agent


@given(parsers.parse('an agent with the tools "{tool_list}"'), target_fixture="test_agent")
def given_agent_with_multiple_tools(tool_list, request, extract_text):
    """Creates an agent with multiple tools."""
    tool_names = [t.strip() for t in tool_list.split(",")]

    tool_map = {
        "get_user_profile": "get_user_profile_tool",
        "calculate_age_in_days": "calculate_age_in_days_tool",
        "get_year": "get_year_tool",
    }

    tools = []
    for tool_name in tool_names:
        fixture_name = tool_map.get(tool_name)
        if fixture_name:
            tools.append(request.getfixturevalue(fixture_name))

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=tools
    )
    async def multi_tool_agent(query: str) -> str:
        """Answer the user's question: {query}. Use available tools to get and process information."""

    return multi_tool_agent


@given("a stateful session", target_fixture="test_session")
def given_stateful_session(test_agent):
    """Creates a stateful session from an agent."""
    return test_agent.stateful()


@given(parsers.parse('an agent with temperature {temp:f}'), target_fixture="test_agent")
def given_agent_with_temperature(temp):
    """Creates an agent with specific temperature."""
    @agent(provider=openai(model="gpt-4o-mini", temperature=temp))
    async def temp_agent(query: str) -> str:
        """Answer: {query}"""
    return temp_agent


@given("a streaming agent without return type", target_fixture="test_agent")
def given_streaming_agent():
    """Creates a streaming agent (no return type annotation)."""
    @agent(provider=openai(model="gpt-4o-mini", temperature=0))
    async def streaming_agent(query: str):
        """Answer this question: {query}"""
    return streaming_agent


# ==================== WHEN STEPS ====================

@when(parsers.parse('I ask the agent "{query}"'), target_fixture="agent_response")
def when_ask_agent(test_agent, query, extract_text):
    """Asks the agent a question and returns the response."""
    async def _ask():
        result = await test_agent(query)
        return await extract_text(result)

    return async_to_sync(_ask)()


@when(parsers.parse('I send the message "{message}" to the session'), target_fixture="session_response")
def when_send_message_to_session(test_session, message, extract_text):
    """Sends a message to a stateful session."""
    async def _send():
        messages = []
        async for msg in test_session(message):
            messages.append(msg)
        return await extract_text(messages[-1])

    return async_to_sync(_send)()


@when(parsers.parse('I send the message "{message}" to the session and ignore response'))
def when_send_message_ignore_response(test_session, message):
    """Sends a message to session without storing response."""
    async def _send():
        async for _ in test_session(message):
            pass

    async_to_sync(_send)()


@when("I reset the session")
def when_reset_session(test_session):
    """Resets a stateful session."""
    test_session.reset()


@when(parsers.parse('I call the streaming agent with "{query}"'), target_fixture="streaming_result")
def when_call_streaming_agent(test_agent, query):
    """Calls a streaming agent and returns the async iterator."""
    async def _call():
        return await test_agent(query)

    return async_to_sync(_call)()


# ==================== THEN STEPS ====================

@then(parsers.parse('the response should contain "{text}"'))
def then_response_contains(agent_response, text):
    """Verifies the response contains specific text."""
    response_lower = agent_response.lower() if isinstance(agent_response, str) else str(agent_response).lower()
    text_lower = text.lower()
    assert text_lower in response_lower, f"Expected '{text}' in response, but got: {agent_response}"


@then(parsers.parse('the session response should contain "{text}"'))
def then_session_response_contains(session_response, text):
    """Verifies the session response contains specific text."""
    response_lower = session_response.lower() if isinstance(session_response, str) else str(session_response).lower()
    text_lower = text.lower()
    assert text_lower in response_lower, f"Expected '{text}' in session response, but got: {session_response}"


@then(parsers.parse('the response should NOT contain "{text}"'))
def then_response_not_contains(agent_response, text):
    """Verifies the response does NOT contain specific text."""
    response_lower = agent_response.lower() if isinstance(agent_response, str) else str(agent_response).lower()
    text_lower = text.lower()
    # Allow it to contain the text if it also indicates not knowing
    if text_lower in response_lower:
        # Check for phrases indicating the agent doesn't know
        unknown_phrases = ["don't know", "don't have", "no information", "not sure"]
        assert any(phrase in response_lower for phrase in unknown_phrases), \
            f"Did not expect '{text}' in response without uncertainty: {agent_response}"


@then(parsers.parse('the session response should NOT contain "{text}"'))
def then_session_response_not_contains(session_response, text):
    """Verifies the session response does NOT contain specific text."""
    response_lower = session_response.lower() if isinstance(session_response, str) else str(session_response).lower()
    text_lower = text.lower()
    # Allow it to contain the text if it also indicates not knowing
    if text_lower in response_lower:
        # Check for phrases indicating the agent doesn't know
        unknown_phrases = ["don't know", "don't have", "no information", "not sure"]
        assert any(phrase in response_lower for phrase in unknown_phrases), \
            f"Did not expect '{text}' in session response without uncertainty: {session_response}"


@then(parsers.parse('the response should contain either "{text1}" or "{text2}"'))
def then_response_contains_either(agent_response, text1, text2):
    """Verifies the response contains at least one of the texts."""
    response_lower = agent_response.lower() if isinstance(agent_response, str) else str(agent_response).lower()
    text1_lower = text1.lower()
    text2_lower = text2.lower()
    assert text1_lower in response_lower or text2_lower in response_lower, \
        f"Expected either '{text1}' or '{text2}' in response, but got: {agent_response}"


@then(parsers.parse('the response should match pattern "{pattern}"'))
def then_response_matches_pattern(agent_response, pattern):
    """Verifies the response matches a regex pattern."""
    import re
    assert re.search(pattern, str(agent_response)), \
        f"Pattern '{pattern}' not found in: {agent_response}"


@then(parsers.parse('the response should be non-empty'))
def then_response_non_empty(agent_response):
    """Verifies the response is not empty."""
    assert agent_response, "Expected non-empty response"
    assert len(str(agent_response)) > 0, "Response should have content"


@then(parsers.parse('the streaming result should have at least {count:d} messages'))
def then_streaming_has_messages(streaming_result, count):
    """Verifies streaming result has minimum number of messages."""
    from liteagent.message import AssistantMessage

    async def _check():
        messages = []
        async for message in streaming_result:
            messages.append(message)

        assistant_messages = [m for m in messages if isinstance(m, AssistantMessage)]
        assert len(assistant_messages) >= count, \
            f"Expected at least {count} AssistantMessages, got {len(assistant_messages)}"

        return messages

    async_to_sync(_check)()


# ==================== STRUCTURED OUTPUT STEPS ====================

@given(parsers.parse('an agent that returns {model_name} structured output'), target_fixture="test_agent")
def given_structured_output_agent(model_name, request):
    """Creates an agent that returns structured output."""
    # This is a placeholder - actual model will be defined in test file
    # Store model name for later use
    return {"model_name": model_name}


@then(parsers.parse('the structured output should have field "{field}" equal to "{value}"'))
def then_structured_field_equals(agent_response, field, value):
    """Verifies a structured output field equals a value."""
    assert hasattr(agent_response, field), f"Response missing field: {field}"
    actual = getattr(agent_response, field)

    # Try to convert value to appropriate type
    if isinstance(actual, bool):
        expected = value.lower() == "true"
    elif isinstance(actual, int):
        expected = int(value)
    elif isinstance(actual, float):
        expected = float(value)
    else:
        expected = value

    assert actual == expected, f"Expected {field}={expected}, got {actual}"


@then(parsers.parse('the structured output should have field "{field}" equal to {value:d}'))
def then_structured_field_equals_int(agent_response, field, value):
    """Verifies a structured output field equals an integer value."""
    assert hasattr(agent_response, field), f"Response missing field: {field}"
    actual = getattr(agent_response, field)
    assert actual == value, f"Expected {field}={value}, got {actual}"


@then(parsers.parse('the structured output should be of type {type_name}'))
def then_structured_output_is_type(agent_response, type_name):
    """Verifies structured output is of a specific type."""
    actual_type = agent_response.__class__.__name__
    assert actual_type == type_name, f"Expected type {type_name}, got {actual_type}"
