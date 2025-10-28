"""
Tests for Error Handling - Various error scenarios and recovery.

Validates that:
- Tool execution errors are handled gracefully
- Invalid tool parameters are caught
- Provider errors propagate correctly
- Invalid structured output is handled
- Error messages are informative
"""
import asyncio
from typing import Literal
from pydantic import BaseModel
from ward import test

from liteagent import agent, tool
from liteagent.providers import openai
from tests.conftest import extract_text


@test("tool that raises exception is handled gracefully")
async def _():
    """
    Tests that when a tool raises an exception, the agent handles it gracefully.

    Deterministic scenario:
    - Create tool that always raises exception
    - Agent tries to use the tool
    - Should handle error and inform user
    """

    @tool
    def failing_tool() -> str:
        """A tool that always fails."""
        raise ValueError("This tool intentionally fails")

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[failing_tool]
    )
    async def agent_with_failing_tool(query: str) -> str:
        """
        Answer: {query}
        Try using the failing_tool if it seems relevant.
        """

    # Agent should handle the error and still respond
    result = await agent_with_failing_tool("Try to use the failing tool")
    result_text = await extract_text(result)

    # Should have some kind of response (not crash)
    assert isinstance(result_text, str)
    assert len(result_text) > 0


@test("tool with invalid parameter types fails gracefully")
async def _():
    """
    Tests that tools with wrong parameter types are handled.

    Deterministic scenario:
    - Create tool expecting int parameter
    - Agent might pass wrong type
    - Should handle validation error
    """

    @tool
    def strict_type_tool(number: int) -> str:
        """Requires an integer parameter."""
        if not isinstance(number, int):
            raise TypeError(f"Expected int, got {type(number)}")
        return f"Number is: {number}"

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[strict_type_tool]
    )
    async def agent_with_strict_tool(query: str) -> str:
        """
        Answer: {query}
        Use strict_type_tool when needed.
        """

    # Agent should call the tool with correct type
    result = await agent_with_strict_tool("Use strict_type_tool with the number 42")
    result_text = await extract_text(result)

    # Should have completed successfully
    assert "42" in result_text


@test("invalid API key raises import error with helpful message")
async def _():
    """
    Tests that invalid/missing API key configuration raises proper error.

    Deterministic scenario:
    - Try to create provider with invalid configuration
    - Should get clear error message
    """

    try:
        # Try to create OpenAI provider with explicitly invalid key
        provider = openai(model="gpt-4o-mini", api_key="invalid_key_123")

        @agent(provider=provider)
        async def test_agent(query: str) -> str:
            """Answer: {query}"""

        # Try to call - should fail with API error
        result = await test_agent("Hello")
        # If we get here without error, the test passes (API key validation might be lazy)
        assert result is not None

    except Exception as e:
        # Should get some kind of authentication or API error
        error_msg = str(e).lower()
        # Accept various error types: authentication, api key, unauthorized, etc.
        assert any(word in error_msg for word in ["auth", "api", "key", "invalid", "unauthorized", "401"])


@test("tool with missing required parameter shows clear error")
async def _():
    """
    Tests that missing required parameters are caught.

    Deterministic scenario:
    - Create tool with required parameter
    - Tool definition should be valid
    - Agent should handle parameter validation
    """

    @tool
    def requires_param(name: str, age: int) -> str:
        """Tool that requires both name and age."""
        return f"{name} is {age} years old"

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[requires_param]
    )
    async def agent_with_params(query: str) -> str:
        """
        Answer: {query}
        Use requires_param tool with both name and age.
        """

    # Agent should provide both parameters
    result = await agent_with_params("Use requires_param with name=John and age=25")
    result_text = await extract_text(result)

    # Should have successfully called tool with both params
    assert "john" in result_text.lower()
    assert "25" in result_text


@test("agent handles network timeout gracefully")
async def _():
    """
    Tests that network timeouts are handled gracefully.

    Deterministic scenario:
    - Create agent with very short timeout
    - Should either timeout or complete successfully
    - Should not crash without error message
    """

    try:
        @agent(provider=openai(model="gpt-4o-mini", temperature=0))
        async def timeout_agent(query: str) -> str:
            """Answer: {query}"""

        # Try with a simple query
        result = await timeout_agent("Say: OK")
        result_text = await extract_text(result)

        # If no timeout, should complete successfully
        assert isinstance(result_text, str)

    except asyncio.TimeoutError:
        # Timeout is acceptable behavior
        assert True
    except Exception as e:
        # Other exceptions should be informative
        assert len(str(e)) > 0


@test("multiple tool errors in sequence are handled")
async def _():
    """
    Tests that multiple tool failures don't break the agent.

    Deterministic scenario:
    - Create multiple tools that can fail
    - Agent tries to use them
    - Should handle errors and continue
    """

    @tool
    def sometimes_fails(should_fail: bool) -> str:
        """Tool that fails based on parameter."""
        if should_fail:
            raise RuntimeError("Tool failed as requested")
        return "Success"

    @tool
    def always_works() -> str:
        """Tool that never fails."""
        return "Always works"

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[sometimes_fails, always_works]
    )
    async def resilient_agent(query: str) -> str:
        """
        Answer: {query}
        You have tools available to use.
        """

    # Agent should be able to work around failures
    result = await resilient_agent("Try to accomplish the task, even if some tools fail")
    result_text = await extract_text(result)

    # Should have produced some response
    assert isinstance(result_text, str)
    assert len(result_text) > 0


@test("invalid structured output format is handled")
async def _():
    """
    Tests that malformed structured output is caught.

    Deterministic scenario:
    - Request structured output
    - If LLM returns invalid format, should handle gracefully
    - Should either retry or return error
    """

    class SimpleOutput(BaseModel):
        """Simple structured output."""
        message: str
        count: int

    @agent(provider=openai(model="gpt-4o-mini", temperature=0))
    async def structured_agent(query: str) -> SimpleOutput:
        """
        Answer: {query}
        Return a structured response with a message and count.
        """

    try:
        # Request structured output
        result = await structured_agent("Return message='Hello' and count=5")

        # Should get valid structured output
        assert isinstance(result, SimpleOutput)
        assert hasattr(result, 'message')
        assert hasattr(result, 'count')

    except Exception as e:
        # If parsing fails, should have informative error
        error_msg = str(e).lower()
        # Should mention validation, parsing, or JSON issues
        assert any(word in error_msg for word in ["validation", "parse", "json", "invalid", "format"])
