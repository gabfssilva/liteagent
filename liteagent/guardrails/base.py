"""Base classes and decorator for guardrails."""

import functools
import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, List, Literal, Optional, TypeVar, Union

from liteagent.guardrails.exceptions import GuardrailViolation, InputViolation, OutputViolation

T = TypeVar("T")
ValidateOn = Literal["in", "out"]


@dataclass
class GuardrailContext:
    """Context passed to guardrails during validation.

    Contains information about the current execution state that
    guardrails can use for validation decisions.

    Attributes:
        agent_name: Name of the agent being executed
        user_input: Original user input (available during input validation)
        llm_output: LLM response (available during output validation)
        metadata: Additional metadata from the execution
    """

    agent_name: Optional[str] = None
    user_input: Optional[str] = None
    llm_output: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class Guardrail(ABC):
    """Base class for implementing guardrails.

    Guardrails are filters that validate agent inputs and/or outputs.
    They can modify the content or raise GuardrailViolation to block execution.

    A guardrail can implement one or both of:
    - validate_input: Check/modify input before sending to LLM
    - validate_output: Check/modify output before returning to user

    Example:
        class AllowedTopics(Guardrail):
            def __init__(self, topics: List[str]):
                self.topics = topics

            async def validate_input(self, user_input: str, context: GuardrailContext) -> str:
                if not any(topic in user_input for topic in self.topics):
                    raise InputViolation(f"Only these topics allowed: {self.topics}")
                return user_input
    """

    @property
    def name(self) -> str:
        """Return the name of this guardrail (defaults to class name)."""
        return self.__class__.__name__

    async def validate_input(
        self, user_input: str, context: GuardrailContext
    ) -> str:
        """Validate and optionally modify user input before LLM processing.

        Args:
            user_input: The input text from the user
            context: Execution context with metadata

        Returns:
            The validated (possibly modified) input text

        Raises:
            InputViolation: If the input violates this guardrail's policy
        """
        return user_input

    async def validate_output(
        self, llm_output: str, context: GuardrailContext
    ) -> str:
        """Validate and optionally modify LLM output before returning to user.

        Args:
            llm_output: The output text from the LLM
            context: Execution context with metadata

        Returns:
            The validated (possibly modified) output text

        Raises:
            OutputViolation: If the output violates this guardrail's policy
        """
        return llm_output


def guardrail(
    guardrail_instance: Guardrail,
    validate: Optional[List[ValidateOn]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to apply a guardrail to an agent or tool.

    Args:
        guardrail_instance: Instance of a Guardrail to apply
        validate: Which stages to validate - ["in"], ["out"], or ["in", "out"]
                 Defaults to ["in", "out"] (both)

    Example:
        @agent(provider=openai())
        @guardrail(AllowedTopics(["weather"]))  # Validates both in and out
        async def weather_bot(user_input: str) -> str:
            '''Respond to: {user_input}'''

        @agent(provider=openai())
        @guardrail(NoPII(), validate=["in"])  # Only validates input
        async def safe_bot(user_input: str) -> str:
            '''Respond to: {user_input}'''

    Returns:
        Decorator function
    """
    import inspect
    from collections.abc import AsyncIterable

    if validate is None:
        validate = ["in", "out"]

    validate_input = "in" in validate
    validate_output = "out" in validate

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Handle both sync and async functions
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                # Extract user_input from args/kwargs
                # Convention: first positional arg or 'user_input' kwarg
                user_input = None
                if args:
                    user_input = args[0]
                elif "user_input" in kwargs:
                    user_input = kwargs["user_input"]

                # Build context
                context = GuardrailContext(
                    agent_name=func.__name__,
                    user_input=str(user_input) if user_input is not None else None,
                    metadata={},
                )

                # Input validation
                if validate_input and user_input is not None:
                    try:
                        validated_input = await guardrail_instance.validate_input(
                            str(user_input), context
                        )
                        # Replace input with validated version
                        if args:
                            args = (validated_input, *args[1:])
                        else:
                            kwargs["user_input"] = validated_input
                    except GuardrailViolation as e:
                        # Add guardrail name if not set
                        if e.guardrail_name is None:
                            e.guardrail_name = guardrail_instance.name
                        raise

                # Execute the wrapped function
                result = await func(*args, **kwargs)

                # Check if result is an async iterable (streaming response)
                if inspect.isasyncgen(result) or isinstance(result, AsyncIterable):
                    # For streaming responses, output validation is not supported
                    # because it would require buffering the entire response,
                    # defeating the purpose of streaming.
                    # Only input validation is applied for streaming.
                    return result

                # For non-streaming responses, validate output
                if validate_output and result is not None:
                    # Extract text from result if it's a Message
                    from liteagent.message import AssistantMessage
                    text_to_validate = None

                    if isinstance(result, AssistantMessage):
                        if isinstance(result.content, AssistantMessage.TextStream):
                            text_to_validate = await result.content.await_complete()
                        else:
                            text_to_validate = str(result.content)
                    elif isinstance(result, str):
                        text_to_validate = result
                    elif hasattr(result, 'content'):
                        if hasattr(result.content, 'await_complete'):
                            text_to_validate = await result.content.await_complete()
                        else:
                            text_to_validate = str(result.content)
                    else:
                        text_to_validate = str(result)

                    try:
                        context.llm_output = text_to_validate
                        validated_text = await guardrail_instance.validate_output(
                            text_to_validate, context
                        )
                        # If text was modified by guardrail, we need to update the result
                        if validated_text != text_to_validate:
                            # Return the modified text directly
                            result = validated_text
                        # Otherwise return original result as-is
                    except GuardrailViolation as e:
                        if e.guardrail_name is None:
                            e.guardrail_name = guardrail_instance.name
                        raise

                return result

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                # For sync functions, we need to handle guardrails synchronously
                # This is a simplified version - in practice, you might want to
                # run async guardrails in a sync context using asyncio.run()
                user_input = None
                if args:
                    user_input = args[0]
                elif "user_input" in kwargs:
                    user_input = kwargs["user_input"]

                context = GuardrailContext(
                    agent_name=func.__name__,
                    user_input=str(user_input) if user_input is not None else None,
                )

                # Note: This simplified version doesn't support async guardrails
                # on sync functions. For production, you'd need asyncio.run()

                result = func(*args, **kwargs)
                return result

            return sync_wrapper

    return decorator
