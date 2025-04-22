import asyncio
import functools
import inspect
import threading
from functools import wraps
from typing import Any, Callable
from typing import Awaitable


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


def isolated_loop(fn: Callable[..., Any]):
    """Decorator that runs an async function or async generator in a separate thread with its own event loop."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if inspect.isasyncgenfunction(fn):
            # It's an async generator — yield items through a queue
            queue: asyncio.Queue = asyncio.Queue()
            done = asyncio.Event()

            async def forward():
                try:
                    async for item in fn(*args, **kwargs):
                        await queue.put(item)
                finally:
                    done.set()

            def thread_main():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(forward())
                loop.close()

            threading.Thread(target=thread_main, daemon=True).start()

            async def stream():
                while not (done.is_set() and queue.empty()):
                    try:
                        item = await asyncio.wait_for(queue.get(), timeout=0.1)
                        yield item
                    except asyncio.TimeoutError:
                        continue

            return stream()

        else:
            # It's a regular async function — run and return result
            async def coro():
                return await fn(*args, **kwargs)

            def run():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(coro())
                loop.close()
                return result

            return asyncio.to_thread(run)

    return wrapper
