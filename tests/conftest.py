"""
Shared configurations and fixtures for all BDD tests.
"""
import asyncio
import functools
from typing import Any, Callable
from pytest import fixture


def async_to_sync(fn: Callable) -> Callable:
    """
    Wrapper to convert async functions to sync for pytest-bdd compatibility.

    pytest-bdd doesn't play well with @pytest.mark.asyncio, so we wrap
    async operations with asyncio.run() to execute them synchronously.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))
    return wrapper


@fixture
def extract_text():
    """
    Fixture that provides text extraction helper for different agent return types.

    Agents can return:
    - str directly
    - Message with content TextStream
    - Message with content str
    """
    async def _extract(result) -> str:
        if isinstance(result, str):
            return result

        if hasattr(result, 'content'):
            content = result.content
            if hasattr(content, 'await_complete'):
                return await content.await_complete()
            return str(content)

        return str(result)

    return _extract


@fixture
def run_async():
    """
    Fixture that provides a helper to run async functions in sync context.
    Usage: run_async(some_async_function(args))
    """
    def _run(coro):
        return asyncio.run(coro)
    return _run
