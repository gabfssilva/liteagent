"""
Cached async iterator with replay support.

Provides a way to cache values from an async iterator, allowing multiple
consumers to iterate over the same sequence with replay capability for
late joiners.
"""
import asyncio
import json
from typing import TypeVar, AsyncIterator, Generic

from liteagent.codec import JsonValue

T = TypeVar('T')


class CachedAsyncIterator(Generic[T]):
    """
    Caches values from an async iterator, allowing multiple consumers with replay.

    This class wraps an async iterator and caches all values it yields. Multiple
    consumers can iterate over the cached values, with late joiners getting a
    replay of all previously yielded values before receiving new ones.

    Example:
        async def source():
            yield "Hello"
            yield " "
            yield "World"

        cached = CachedAsyncIterator(source())

        # Consumer 1
        tokens = [t async for t in cached]
        print("".join(tokens))  # "Hello World"

        # Consumer 2 (gets replay)
        async for token in cached:
            print(token)  # "Hello", " ", "World"
    """

    def __init__(self, source: AsyncIterator[T]):
        """
        Initialize the cached iterator.

        Args:
            source: The source async iterator to cache values from
        """
        self._source = source
        self._cache: list[T] = []
        self._lock = asyncio.Lock()
        self._complete = asyncio.Event()
        self._update = asyncio.Event()
        self._broadcast_task: asyncio.Task | None = None
        self._started = False

    async def _broadcast(self):
        """Background task that consumes source and populates cache."""
        try:
            async for value in self._source:
                async with self._lock:
                    self._cache.append(value)
                self._update.set()
                await asyncio.sleep(0)  # Yield to consumers
        finally:
            self._complete.set()
            self._update.set()

    def _ensure_started(self):
        """Lazy start broadcast task on first consumer."""
        if not self._started:
            self._started = True
            self._broadcast_task = asyncio.create_task(self._broadcast())

    def __aiter__(self) -> AsyncIterator[T]:
        """
        Create an async iterator over cached and future values.

        Returns:
            An async iterator that yields all cached values first,
            then continues with new values as they arrive
        """
        self._ensure_started()

        async def _consumer():
            index = 0

            while True:
                # Get current cache length
                async with self._lock:
                    cache_len = len(self._cache)

                # Yield cached values
                while index < cache_len:
                    async with self._lock:
                        if index < len(self._cache):
                            yield self._cache[index]
                    index += 1

                # Check if complete
                if self._complete.is_set():
                    break

                # Wait for new values
                await self._update.wait()
                self._update.clear()

        return _consumer()

    async def await_complete(self) -> None:
        """
        Wait until the source iterator is exhausted.

        This method blocks until the source has yielded all its values.
        """
        self._ensure_started()
        await self._complete.wait()

    @property
    def is_complete(self) -> bool:
        """
        Check if the source iterator has been exhausted.

        Returns:
            True if source is exhausted, False otherwise
        """
        return self._complete.is_set()


class AppendableIterator(Generic[T]):
    """
    An async iterator that accepts values via append() method.

    This provides a bridge between push-based producers (that call append)
    and pull-based consumers (that use async iteration). Internally uses
    a queue to buffer values.

    Example:
        appendable = AppendableIterator[str]()

        # Producer pushes values
        await appendable.append("Hello")
        await appendable.append(" World")
        await appendable.complete()

        # Consumer pulls values
        async for value in appendable:
            print(value)  # "Hello", " World"
    """

    def __init__(self):
        """Initialize an empty appendable iterator."""
        self._queue: asyncio.Queue[T | None] = asyncio.Queue()
        self._complete_flag = False

    async def append(self, value: T):
        """
        Append a value to the iterator.

        Args:
            value: The value to append

        Raises:
            RuntimeError: If called after complete()
        """
        if self._complete_flag:
            raise RuntimeError("Cannot append to completed iterator")
        await self._queue.put(value)

    async def complete(self):
        """
        Mark the iterator as complete.

        After calling this, no more values can be appended and
        consumers will stop iterating after consuming all buffered values.
        """
        if not self._complete_flag:
            self._complete_flag = True
            await self._queue.put(None)  # Sentinel value

    def __aiter__(self) -> AsyncIterator[T]:
        """
        Create an async iterator over the appended values.

        Returns:
            An async iterator that yields values in the order they were appended
        """
        async def _generator():
            while True:
                value = await self._queue.get()
                if value is None:  # Sentinel = complete
                    break
                yield value

        return _generator()


class CachedStringAccumulator:
    """
    Wrapper around CachedAsyncIterator[str] that provides AtomicString-compatible API.

    This class bridges the gap between the old AtomicString API (which accumulated
    strings internally) and the new CachedAsyncIterator API (which yields tokens).

    It provides methods like get(), append(), await_complete() for backward compatibility.
    """

    def __init__(self, initial: str = "", complete: bool = False):
        """
        Initialize the accumulator.

        Args:
            initial: Initial string value
            complete: If True, iterator is immediately marked as complete
        """
        self._appendable = AppendableIterator[str]()
        self._cached = CachedAsyncIterator(self._appendable)
        self._accumulated = initial
        self._lock = asyncio.Lock()

        # If initial value provided, append it
        if initial:
            asyncio.create_task(self._appendable.append(initial))

        # If complete, mark as complete
        if complete:
            asyncio.create_task(self._appendable.complete())

    async def append(self, text: str):
        """Append text to the accumulator."""
        async with self._lock:
            self._accumulated += text
        await self._appendable.append(text)

    async def set(self, text: str):
        """Set the accumulated text (replaces all previous content)."""
        # In streaming model, we can only append
        # This is used by provider when updating arguments
        async with self._lock:
            self._accumulated = text
        await self._appendable.append(text)

    async def get(self) -> str:
        """Get the current accumulated text."""
        async with self._lock:
            return self._accumulated

    async def await_complete(self) -> str:
        """Wait for completion and return accumulated text."""
        await self._cached.await_complete()
        return await self.get()

    async def complete(self):
        """Mark as complete."""
        await self._appendable.complete()

    @property
    def is_complete(self) -> bool:
        """Check if complete."""
        return self._cached.is_complete

    async def await_as_json(self) -> JsonValue:
        """Wait for completion and parse as JSON."""
        text = await self.await_complete()
        return json.loads(text)

    def __aiter__(self) -> AsyncIterator[str]:
        """Iterate over tokens."""
        return self._cached.__aiter__()
