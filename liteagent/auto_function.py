import inspect
import asyncio
from typing import TypeVar, Callable

from pydantic import BaseModel, Field

from liteagent import Provider, agent
from liteagent.internal import depends_on

T = TypeVar("T")
R = TypeVar("R")


class FunctionDefinition(BaseModel):
    implemented_function: str = Field(
        ...,
        description="The implementation of the function in Python."
    )


def custom_key_builder(func, *args, **kwargs) -> str:
    # Sort kwargs so that the key is deterministic.
    sorted_kwargs = tuple(sorted(kwargs.items()))
    return f"{func.__module__}:{func.__name__}:{args}:{sorted_kwargs}"


@depends_on({"aiocache": "aiocache"})
def auto_function(provider: Provider, max_retries: int = 5) -> Callable[[T], R]:
    # Use our custom key_builder so we know how the key is generated.

    from aiocache import cached, Cache

    @cached(cache=Cache.MEMORY, key_builder=custom_key_builder)
    @agent(
        provider=provider,
        intercept=None,
        description=(
            "You are the best programmer ever. "
            "You always generate the best possible code. "
            "Always write clean code. "
            "Use the best techniques you can think of. "
            "Write code that is easy to understand. "
            "Do not forget about all the needed imports. "
            "Do not envelop the response in backquotes."
        ),
    )
    async def programmer_agent(name: str, description: str, signature: str) -> FunctionDefinition:
        """
        Function name: {name}
        Function description: {description}
        Expected function signature: {signature}
        """

    def decorator(func: Callable[[T], R]) -> Callable[[T], R]:
        async def wrapper(*args, **kwargs):
            func_signature = str(inspect.signature(func))
            last_exception = None

            agent_args = {
                "name": func.__name__,
                "description": func.__doc__,
                "signature": func_signature,
            }

            for attempt in range(max_retries):
                try:
                    definition = await programmer_agent(**agent_args)

                    code = definition.implemented_function
                    if code.startswith("```python"):
                        code = code[9:]
                    if code.endswith("```"):
                        code = code[:-3]

                    namespace = {}
                    exec(code, namespace)
                    generated_func = namespace[func.__name__]

                    result = generated_func(*args, **kwargs)
                    if asyncio.iscoroutine(result):
                        result = await result
                    return result

                except BaseException as exc:
                    cache_key = custom_key_builder(programmer_agent, **agent_args)
                    await programmer_agent.cache.delete(cache_key)
                    last_exception = exc

            raise last_exception

        return wrapper

    return decorator
