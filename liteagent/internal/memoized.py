import asyncio
from typing import AsyncIterator


class _Stop:
    pass


class ContentStream[T]:
    def __init__(self):
        self._buffer: list[T] = []
        self._main: asyncio.Queue[T | _Stop] = asyncio.Queue()
        self._consumers: list[asyncio.Queue[T]] = []
        self._lock = asyncio.Lock()

        self._pending_tasks: list[asyncio.Task] = [
            asyncio.create_task(self._broadcast())
        ]

        self._done = False

    @classmethod
    def from_async_iterator(cls, iterator: AsyncIterator[T]):
        self = cls()

        async def _from_async_iterator():
            async for item in iterator:
                await self.emit(item)

            await self.close()

        asyncio.create_task(_from_async_iterator())

        return self

    def iterator(self) -> AsyncIterator[T]:
        return self.__aiter__()

    async def _broadcast(self):
        while not self._done:
            item = await self._main.get()

            async with self._lock:
                for consumer in self._consumers:
                    await consumer.put(item)

                self._buffer.append(item)

                if item is _Stop:
                    self._done = True
                    return

    async def collect(self) -> list[T]:
        return [item async for item in self]

    def __aiter__(self) -> AsyncIterator[T]:
        queue = asyncio.Queue()

        async def consume():
            async with self._lock:
                for item in self._buffer:
                    await queue.put(item)

                self._consumers.append(queue)

            try:
                while True:
                    item = await queue.get()
                    if item is _Stop:
                        break
                    yield item
            finally:
                async with self._lock:
                    if queue in self._consumers:
                        self._consumers.remove(queue)

        return consume()

    async def emit(self, item: T):
        await self._main.put(item)

    async def close(self):
        await self._main.put(_Stop)
        await asyncio.gather(*self._pending_tasks)
