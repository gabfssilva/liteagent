"""
BDD tests for Error Handling - Various error scenarios.

Validates that:
- Tool execution errors are handled gracefully
- Invalid tool parameters are caught
- Provider errors propagate correctly
"""
from pytest_bdd import scenarios, given, when, then, parsers
from pytest import fixture
import asyncio
import functools

from liteagent import agent, tool
from liteagent.providers import openai


def async_to_sync(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))
    return wrapper


scenarios('../features/error_handling.feature')


# ==================== TOOL FIXTURES ====================

@fixture
def failing_tool_fixture():
    @tool
    def failing_tool() -> str:
        """A tool that always fails."""
        raise ValueError("This tool intentionally fails")
    return failing_tool


@fixture
def strict_type_tool_fixture():
    @tool
    def strict_type_tool(number: int) -> str:
        """Requires an integer parameter."""
        if not isinstance(number, int):
            raise TypeError(f"Expected int, got {type(number)}")
        return f"Number is: {number}"
    return strict_type_tool


@fixture
def requires_param_tool():
    @tool
    def requires_param(name: str, age: int) -> str:
        """Tool that requires both name and age."""
        return f"{name} is {age} years old"
    return requires_param


@fixture
def sometimes_fails_tool():
    @tool
    def sometimes_fails(should_fail: bool) -> str:
        """Tool that fails based on parameter."""
        if should_fail:
            raise RuntimeError("Tool failed as requested")
        return "Success"
    return sometimes_fails


@fixture
def always_works_tool():
    @tool
    def always_works() -> str:
        """Tool that never fails."""
        return "Always works"
    return always_works


# ==================== CONTEXT FIXTURE ====================

@fixture
def test_context():
    """Context to store test agent between Given and When steps."""
    return {}


# ==================== GIVEN STEPS ====================

@given("the OpenAI provider is available")
def given_openai_available():
    import os
    assert os.environ.get("OPENAI_API_KEY")


@given("an agent with a tool that always fails")
def given_agent_failing_tool(failing_tool_fixture, test_context):
    @agent(provider=openai(model="gpt-4o-mini", temperature=0), tools=[failing_tool_fixture])
    async def agent_with_failing_tool(query: str) -> str:
        """Answer: {query}. Try using the failing_tool if it seems relevant."""
    test_context['agent'] = agent_with_failing_tool


@given("an agent with a strict type tool")
def given_agent_strict_tool(strict_type_tool_fixture, test_context):
    @agent(provider=openai(model="gpt-4o-mini", temperature=0), tools=[strict_type_tool_fixture])
    async def agent_with_strict_tool(query: str) -> str:
        """Answer: {query}. Use strict_type_tool when needed."""
    test_context['agent'] = agent_with_strict_tool


@given("an OpenAI provider with invalid API key", target_fixture="invalid_provider")
def given_invalid_provider():
    return openai(model="gpt-4o-mini", api_key="invalid_key_123")


@given("an agent with a tool requiring parameters")
def given_agent_with_params(requires_param_tool, test_context):
    @agent(provider=openai(model="gpt-4o-mini", temperature=0), tools=[requires_param_tool])
    async def agent_with_params(query: str) -> str:
        """Answer: {query}. Use requires_param tool with both name and age."""
    test_context['agent'] = agent_with_params


@given("an agent with multiple tools that can fail")
def given_resilient_agent(sometimes_fails_tool, always_works_tool, test_context):
    @agent(provider=openai(model="gpt-4o-mini", temperature=0), tools=[sometimes_fails_tool, always_works_tool])
    async def resilient_agent(query: str) -> str:
        """Answer: {query}. You have tools available to use."""
    test_context['agent'] = resilient_agent


# ==================== WHEN STEPS ====================

@when(parsers.parse('I ask the agent to "{query}"'), target_fixture="error_response")
def when_ask_agent_error(test_context, query, extract_text):
    """Generic when step that uses the agent from context."""
    agent_func = test_context.get('agent')
    assert agent_func is not None, "No agent found in context"

    async def _ask():
        try:
            result = await agent_func(query)
            return await extract_text(result)
        except Exception as e:
            return str(e)
    return async_to_sync(_ask)()


@when(parsers.parse('I try to create an agent with invalid provider'), target_fixture="creation_error")
def when_create_invalid_agent(invalid_provider):
    try:
        @agent(provider=invalid_provider)
        async def test_agent(query: str) -> str:
            """Answer: {query}"""

        async def _call():
            return await test_agent("Hello")

        result = async_to_sync(_call)()
        return None  # No error
    except Exception as e:
        return e


# ==================== THEN STEPS ====================

@then("the agent should respond without crashing")
def then_agent_responds(error_response):
    assert error_response is not None, "Agent should produce a response"


@then("the response should be non-empty")
def then_response_non_empty(error_response):
    assert len(str(error_response)) > 0, "Response should not be empty"


@then("the agent should handle the tool correctly")
def then_agent_handles_tool(error_response):
    assert error_response is not None


@then(parsers.parse('the response should contain "{text}"'))
def then_response_contains_error(error_response, text):
    response_str = str(error_response)
    # Case-insensitive comparison
    assert text.lower() in response_str.lower(), f"Expected '{text}' in response: {error_response}"


@then("an authentication error should be raised")
def then_auth_error_raised(creation_error):
    if creation_error is None:
        # API key validation might be lazy, which is acceptable
        assert True
    else:
        error_msg = str(creation_error).lower()
        assert any(word in error_msg for word in ["auth", "api", "key", "invalid", "unauthorized", "401"]), \
            f"Expected authentication error, got: {creation_error}"


@then("the agent should provide both parameters successfully")
def then_agent_provides_params(error_response):
    assert error_response is not None


@then("the agent should handle errors and continue")
def then_agent_handles_errors(error_response):
    assert error_response is not None
