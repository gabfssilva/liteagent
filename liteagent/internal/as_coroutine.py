import asyncio
import functools
import inspect
import threading
from functools import wraps
from typing import Awaitable, Callable, Any


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
    """Decorator that runs an async function or async generator on a dedicated, persistent event loop."""

    # Create a persistent loop in its own thread (once per decorated function)
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if inspect.isasyncgenfunction(fn):
            queue: asyncio.Queue = asyncio.Queue()
            done = asyncio.Event()

            async def forward():
                try:
                    async for item in fn(*args, **kwargs):
                        await queue.put(item)
                finally:
                    done.set()

            # Submit to per-decorator loop
            asyncio.run_coroutine_threadsafe(forward(), loop)

            async def stream():
                while not (done.is_set() and queue.empty()):
                    try:
                        item = await asyncio.wait_for(queue.get(), timeout=0.1)
                        yield item
                    except asyncio.TimeoutError:
                        continue

            return stream()

        else:
            async def coro():
                return await fn(*args, **kwargs)

            future = asyncio.run_coroutine_threadsafe(coro(), loop)
            return asyncio.wrap_future(future)

    return wrapper
