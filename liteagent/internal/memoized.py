import asyncio
from asyncio import Task, Queue, Lock
from collections.abc import AsyncIterable, AsyncIterator


class _Stop:
    def __init__(self, reason: Exception | None = None):
        self.reason = reason


class MemoizedAsyncIterable[T](AsyncIterable[T]):
    _done: bool
    _lock: Lock
    _consumers: list[Queue[T]]
    _main: Queue[T | _Stop]
    _buffer: list[T]
    _broadcast_task: Task[None]
    _producer_task: Task[None] | None
    _close_task: Task[None] | None

    def __init__(self):
        self._buffer: list[T] = []
        self._main: asyncio.Queue[T | _Stop] = asyncio.Queue()
        self._consumers: list[asyncio.Queue[T]] = []
        self._lock = asyncio.Lock()
        self._broadcast_task = asyncio.create_task(self._broadcast())
        self._producer_task = None
        self._close_task = None
        self._done = False

    @classmethod
    def from_async_iterable(cls, iterable: AsyncIterable[T]):
        self = cls()

        async def _from_async_iterator():
            try:
                async for item in iterable:
                    await self.emit(item)
            finally:
                await self.close()

        self._producer_task = asyncio.create_task(_from_async_iterator())
        return self

    def iterator(self) -> AsyncIterable[T]:
        return self.__aiter__()

    async def _broadcast(self):
        while not self._done:
            item = await self._main.get()

            async with self._lock:
                self._buffer.append(item)
                consumers = list(self._consumers)

                if isinstance(item, _Stop):
                    self._done = True

            tasks = [consumer.put(item) for consumer in consumers]
            await asyncio.gather(*tasks)

    async def collect(self) -> list[T]:
        return [item async for item in self]

    def __aiter__(self) -> AsyncIterator[T]:
        queue = asyncio.Queue()

        async def consume() -> AsyncIterator[T]:
            async with self._lock:
                for item in self._buffer:
                    await queue.put(item)

                self._consumers.append(queue)

            try:
                while True:
                    item = await queue.get()

                    if isinstance(item, _Stop):
                        queue.task_done()

                        if item.reason:
                            raise item.reason

                        break

                    queue.task_done()
                    yield item
            finally:
                async with self._lock:
                    if queue in self._consumers:
                        self._consumers.remove(queue)

        return consume()

    async def emit(self, item: T):
        if self._done:
            raise RuntimeError("Cannot emit to a closed MemoizedAsyncIterable")

        await self._main.put(item)

    async def close(self, reason: Exception | None = None):
        await self._main.put(_Stop(reason=reason))
        await self._broadcast_task

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close(reason=exc)


async def main():
    async with MemoizedAsyncIterable() as stream:
        await stream.emit(1)
        await stream.emit(2)
        await stream.emit(3)

    async for element in stream:
        print(element)


if __name__ == '__main__':
    asyncio.run(main())
