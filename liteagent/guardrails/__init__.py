"""
Guardrails - Filter-based validation for LiteAgent.

Guardrails are filters that validate inputs and outputs of agents,
similar to filters in web frameworks. They can block execution if
validation fails.

Usage:
    from liteagent import agent, guardrail
    from liteagent.guardrails import AllowedTopics, NoPII
    from liteagent.providers import openai

    @agent(provider=openai())
    @guardrail(AllowedTopics(["weather", "news"]))  # Default: validates both in/out
    @guardrail(NoPII(), validate=["in"])  # Only validates input
    async def chatbot(user_input: str) -> str:
        '''Respond to: {user_input}'''

Example with custom guardrail:
    from liteagent.guardrails import Guardrail, GuardrailViolation

    class MyGuardrail(Guardrail):
        async def validate_input(self, user_input: str, context: dict) -> str:
            if "forbidden" in user_input:
                raise GuardrailViolation("Forbidden word detected")
            return user_input

        async def validate_output(self, output: str, context: dict) -> str:
            return output.replace("bad", "good")
"""

from liteagent.guardrails.base import (
    Guardrail,
    guardrail,
    GuardrailContext,
)
from liteagent.guardrails.exceptions import (
    GuardrailViolation,
    InputViolation,
    OutputViolation,
)

__all__ = [
    "Guardrail",
    "guardrail",
    "GuardrailContext",
    "GuardrailViolation",
    "InputViolation",
    "OutputViolation",
]
