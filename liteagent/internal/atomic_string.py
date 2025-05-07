import asyncio
import json
from typing import AsyncIterator

from liteagent.codec import JsonValue


class AtomicString:
    def __init__(self, initial: str = ""):
        self._value = initial
        self._lock = asyncio.Lock()
        self._complete_event = asyncio.Event()
        self._subscribers = []

    async def append(self, text: str):
        async with self._lock:
            if self.is_complete:
                raise RuntimeError("Cannot mutate a complete AtomicString")

            self._value += text

            for semaphore in self._subscribers:
                semaphore.set()

    async def get(self) -> str:
        if self.is_complete:
            return self._value

        async with self._lock:
            return self._value

    async def await_complete(self) -> str:
        await self._complete_event.wait()
        return self._value

    @property
    def is_complete(self) -> bool:
        return self._complete_event.is_set()

    async def complete(self):
        self._complete_event.set()
        
        for semaphore in self._subscribers:
            semaphore.set()

    async def await_as_json(self) -> JsonValue:
        return json.loads(await self.await_complete())

    def __repr__(self):
        return self._value

    def __aiter__(self):
        async def _get_iterator() -> AsyncIterator[str]:
            if self.is_complete:
                yield self._value
                return

            semaphore = asyncio.Event()

            async with self._lock:
                self._subscribers.append(semaphore)

            try:
                current_value = await self.get()
                yield current_value

                while not self.is_complete:
                    await semaphore.wait()
                    value = await self.get()

                    if value != current_value:
                        current_value = value
                        yield current_value

                    semaphore.clear()

                final_value = await self.get()

                if final_value != current_value:
                    yield final_value

            except asyncio.CancelledError:
                pass

        return _get_iterator()
