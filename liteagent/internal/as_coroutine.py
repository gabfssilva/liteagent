import asyncio
import inspect
from functools import wraps
from typing import Callable, Awaitable


def as_coroutine[T](func: Callable[..., T]) -> Callable[..., Awaitable[T]]:
    """
    A decorator that checks if a function is a coroutine function.
    If it is, it awaits the result. If not, it delegates the processing to a thread.

    This allows mixing synchronous and asynchronous functions seamlessly.

    Args:
        func: The function to wrap

    Returns:
        A coroutine function that handles both sync and async functions
    """

    @wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return await asyncio.to_thread(func, *args, **kwargs)

    return wrapper
