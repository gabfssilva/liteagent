"""Step definitions for guardrails BDD tests."""

import asyncio
import functools
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from liteagent import agent
from liteagent.guardrails import Guardrail, GuardrailContext, guardrail
from liteagent.guardrails.builtin import (
    AllowedTopics,
    NoPII,
    NoPromptInjection,
    NoSecrets,
    ToxicContent,
)
from liteagent.guardrails.exceptions import (
    GuardrailViolation,
    InputViolation,
    OutputViolation,
)
from liteagent.message import AssistantMessage
from liteagent.provider import Provider

scenarios("../features/guardrails.feature")


# Async wrapper for pytest-bdd compatibility
def async_to_sync(fn):
    """Wrapper to convert async functions to sync for pytest-bdd."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))
    return wrapper


# Mock Provider for testing
class MockEchoProvider(Provider):
    """Provider that simply echoes the user input."""

    async def completion(self, messages, **kwargs):
        # Find last user message
        user_msg = None
        for msg in reversed(messages):
            if msg.role == "user":
                user_msg = msg
                break

        if user_msg:
            from liteagent.internal.cached_iterator import CachedStringAccumulator
            text = str(user_msg.content)
            content = CachedStringAccumulator()
            stream = AssistantMessage.TextStream(
                stream_id="test-stream",
                content=content
            )
            # Yield message first
            yield AssistantMessage(content=stream)
            # Then append and complete
            await content.append(text)
            await content.complete()
        else:
            from liteagent.internal.cached_iterator import CachedStringAccumulator
            content = CachedStringAccumulator()
            stream = AssistantMessage.TextStream(
                stream_id="test-stream",
                content=content
            )
            yield AssistantMessage(content=stream)
            await content.append("No input received")
            await content.complete()


class MockPIIProvider(Provider):
    """Provider that returns PII in output."""

    async def completion(self, messages, **kwargs):
        from liteagent.internal.cached_iterator import CachedStringAccumulator
        content = CachedStringAccumulator()
        stream = AssistantMessage.TextStream(
            stream_id="test-stream",
            content=content
        )
        yield AssistantMessage(content=stream)
        await content.append("My email is leaked@example.com and phone is 555-1234")
        await content.complete()


# Fixtures
@pytest.fixture
def mock_echo_provider():
    """Return a mock provider that echoes input."""
    return MockEchoProvider()


@pytest.fixture
def mock_pii_provider():
    """Return a mock provider that returns PII."""
    return MockPIIProvider()


# Custom guardrail for testing
class PoliteGuardrail(Guardrail):
    """Requires 'please' in input."""

    async def validate_input(self, user_input: str, context: GuardrailContext) -> str:
        if "please" not in user_input.lower():
            raise InputViolation("Input must contain 'please'")
        return user_input


# Given steps
@given("a mock provider that echoes the input", target_fixture="test_provider")
def given_mock_echo_provider(mock_echo_provider):
    """Store mock echo provider."""
    return mock_echo_provider


@given("a mock provider that returns PII in output", target_fixture="test_provider")
def given_mock_pii_provider(mock_pii_provider):
    """Store mock PII provider."""
    return mock_pii_provider


@given("an agent with AllowedTopics guardrail for weather topics", target_fixture="test_agent")
def given_agent_with_allowed_topics(test_provider):
    """Create agent with AllowedTopics guardrail."""
    @guardrail(AllowedTopics(["weather", "forecast", "temperature", "climate"]))
    @agent(provider=test_provider)
    async def weather_agent(user_input: str) -> str:
        """Respond to: {user_input}"""
    return weather_agent


@given("an agent with NoPII guardrail that redacts", target_fixture="test_agent")
def given_agent_with_nopii_redact(test_provider):
    """Create agent with NoPII guardrail that redacts."""
    @guardrail(NoPII(block_on_detection=False))
    @agent(provider=test_provider)
    async def safe_agent(user_input: str) -> str:
        """Respond to: {user_input}"""
    return safe_agent


@given("an agent with NoPII guardrail that blocks on output", target_fixture="test_agent")
def given_agent_with_nopii_block_output(test_provider):
    """Create agent with NoPII guardrail that blocks on output."""
    @guardrail(NoPII(block_on_detection=True))
    @agent(provider=test_provider)
    async def strict_agent(user_input: str) -> str:
        """Respond to: {user_input}"""
    return strict_agent


@given("an agent with NoPromptInjection guardrail", target_fixture="test_agent")
def given_agent_with_no_prompt_injection(test_provider):
    """Create agent with NoPromptInjection guardrail."""
    @guardrail(NoPromptInjection())
    @agent(provider=test_provider)
    async def secure_agent(user_input: str) -> str:
        """Respond to: {user_input}"""
    return secure_agent


@given("an agent with AllowedTopics and NoPII guardrails", target_fixture="test_agent")
def given_agent_with_multiple_guardrails(test_provider):
    """Create agent with multiple guardrails."""
    @guardrail(NoPII(block_on_detection=False))
    @guardrail(AllowedTopics(["weather", "forecast", "NYC", "climate"]))
    @agent(provider=test_provider)
    async def multi_guarded_agent(user_input: str) -> str:
        """Respond to: {user_input}"""
    return multi_guarded_agent


@given("an agent with NoPII guardrail that validates only input", target_fixture="test_agent")
def given_agent_with_nopii_input_only(test_provider):
    """Create agent with NoPII guardrail that validates only input."""
    @guardrail(NoPII(block_on_detection=True), validate=["in"])
    @agent(provider=test_provider)
    async def input_only_agent(user_input: str) -> str:
        """Respond to: {user_input}"""
    return input_only_agent


@given("an agent with NoPII guardrail that validates only output", target_fixture="test_agent")
def given_agent_with_nopii_output_only(test_provider):
    """Create agent with NoPII guardrail that validates only output."""
    @guardrail(NoPII(block_on_detection=False), validate=["out"])
    @agent(provider=test_provider)
    async def output_only_agent(user_input: str) -> str:
        """Respond to: {user_input}"""
    return output_only_agent


@given("an agent with NoSecrets guardrail", target_fixture="test_agent")
def given_agent_with_no_secrets(test_provider):
    """Create agent with NoSecrets guardrail."""
    @guardrail(NoSecrets())
    @agent(provider=test_provider)
    async def secret_detecting_agent(user_input: str) -> str:
        """Respond to: {user_input}"""
    return secret_detecting_agent


@given("an agent with ToxicContent guardrail that redacts", target_fixture="test_agent")
def given_agent_with_toxic_content_redact(test_provider):
    """Create agent with ToxicContent guardrail that redacts."""
    @guardrail(ToxicContent(block_on_detection=False))
    @agent(provider=test_provider)
    async def family_friendly_agent(user_input: str) -> str:
        """Respond to: {user_input}"""
    return family_friendly_agent


@given("a custom guardrail that requires \"please\" in input", target_fixture="test_agent")
def given_agent_with_custom_guardrail(test_provider):
    """Create agent with custom guardrail."""
    @guardrail(PoliteGuardrail())
    @agent(provider=test_provider)
    async def polite_agent(user_input: str) -> str:
        """Respond to: {user_input}"""
    return polite_agent


# When steps
@when(parsers.parse('I call the agent with "{user_input}"'), target_fixture="agent_result")
def when_call_agent(test_agent, user_input):
    """Call the agent with given input."""
    async def run():
        try:
            # Call agent in non-streaming mode to allow output validation
            result = await test_agent(user_input)

            # Extract text using same logic as conftest extract_text
            if isinstance(result, str):
                text = result
            elif hasattr(result, 'content'):
                content = result.content
                if hasattr(content, 'await_complete'):
                    text = await content.await_complete()
                else:
                    text = str(content)
            else:
                text = str(result)

            return {"success": True, "text": text, "exception": None}
        except GuardrailViolation as e:
            return {"success": False, "text": None, "exception": e}

    return async_to_sync(run)()


# Then steps
@then("the agent should respond successfully")
def then_agent_responds_successfully(agent_result):
    """Verify agent responded without exception."""
    assert agent_result["success"], f"Agent raised exception: {agent_result['exception']}"
    assert agent_result["text"] is not None


@then("the agent should raise InputViolation")
def then_agent_raises_input_violation(agent_result):
    """Verify agent raised InputViolation."""
    assert not agent_result["success"], "Agent should have raised exception"
    assert isinstance(agent_result["exception"], InputViolation)


@then("the agent should raise OutputViolation")
def then_agent_raises_output_violation(agent_result):
    """Verify agent raised OutputViolation."""
    assert not agent_result["success"], "Agent should have raised exception"
    assert isinstance(agent_result["exception"], OutputViolation)


@then(parsers.parse('the response should contain "{text}"'))
def then_response_contains(agent_result, text):
    """Verify response contains text."""
    assert agent_result["success"], "Agent raised exception"
    assert text in agent_result["text"], f"Expected '{text}' in '{agent_result['text']}'"


@then(parsers.parse('the response should not contain "{text}"'))
def then_response_not_contains(agent_result, text):
    """Verify response does not contain text."""
    assert agent_result["success"], "Agent raised exception"
    assert text not in agent_result["text"], f"Did not expect '{text}' in '{agent_result['text']}'"


@then(parsers.parse('the violation message should contain "{text}"'))
def then_violation_message_contains(agent_result, text):
    """Verify violation message contains text."""
    assert not agent_result["success"], "Agent should have raised exception"
    exception = agent_result["exception"]
    assert text.lower() in str(exception).lower()


@then("the response should contain PII")
def then_response_contains_pii(agent_result):
    """Verify response contains PII."""
    assert agent_result["success"], "Agent raised exception"
    # Check for common PII patterns
    text = agent_result["text"]
    has_email = "@" in text and ".com" in text
    has_phone = any(char.isdigit() for char in text) and ("-" in text or len([c for c in text if c.isdigit()]) >= 7)
    assert has_email or has_phone, f"Expected PII in response: {text}"
