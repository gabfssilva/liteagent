import asyncio
from typing import (
    Callable, Dict, List, Any, Awaitable, Protocol,
    TypeVar, Type, Optional
)

from liteagent.events import Event

T = TypeVar('T', bound=Event)
EventHandler = Callable[[T], Awaitable[Optional[bool]]]


class EventBus(Protocol):
    def on(self, event_type: Type[T]) -> Callable[[EventHandler[T]], EventHandler[T]]: ...

    async def emit(self, event: Event) -> bool: ...

    async def start(self): ...

    async def stop(self): ...


class _DedupCache:
    def __init__(self, maxsize=1000):
        self.store = set()
        self.maxsize = maxsize

    def add(self, value) -> bool:
        if value in self.store:
            return False

        self.store.add(value)

        if len(self.store) > self.maxsize:
            self.store.pop()

        return True


class _Bus:
    def __init__(self) -> None:
        self.type_handlers: Dict[Type, List[EventHandler]] = {}
        self.queue: asyncio.Queue[Any] = asyncio.Queue()
        self._running = False
        self._message_cache = _DedupCache()
        self._running_task: asyncio.Task | None = None

    def on(self, event_type: Type[T]) -> Callable[[EventHandler[T]], EventHandler[T]]:
        """
        Register a handler for a specific event type

        Example:
            @bus.on(MyEvent)
            async def handler(event: MyEvent) -> bool:
                # Process event...
                if done_with_this_event_type:
                    return False  # Unregister this handler
                return True  # Stay registered
        """

        def decorator(func: EventHandler[T]) -> EventHandler[T]:
            self.type_handlers.setdefault(event_type, []).append(func)
            return func

        return decorator

    async def emit(self, event: Event) -> bool:
        if not self._running:
            await self.start()

        if self._message_cache.add(event):
            await self.queue.put(event)
            return True

        return False

    async def _dispatch(self):
        while self._running:
            event = await self.queue.get()

            tasks = []
            handlers_to_remove = []

            for handler_type, handlers in self.type_handlers.items():
                if isinstance(event, handler_type):
                    for i, handler in enumerate(handlers):
                        task = handler(event)
                        tasks.append((handler_type, i, handler, task))

            if tasks:
                for handler_type, idx, handler, task in tasks:
                    try:
                        result = await task
                        if result is False:
                            handlers_to_remove.append((handler_type, handler))
                    except Exception as e:
                        continue

            for handler_type, handler in handlers_to_remove:
                if handler_type in self.type_handlers:
                    if handler in self.type_handlers[handler_type]:
                        self.type_handlers[handler_type].remove(handler)

                    if not self.type_handlers[handler_type]:
                        del self.type_handlers[handler_type]

            self.queue.task_done()

    async def start(self):
        if self._running:
            return

        self._running = True
        self._running_task = asyncio.create_task(self._dispatch())

    async def stop(self):
        self._running = False
        if self._running_task:
            await self._running_task
        await self.queue.join()


bus: EventBus = _Bus()
