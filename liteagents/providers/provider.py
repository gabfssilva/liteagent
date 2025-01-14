from abc import abstractmethod

from typing import AsyncIterator

from liteagents import Tool
from liteagents.message import Message


class Provider:
    name: str

    @abstractmethod
    async def completion(
        self,
        messages: list[Message],
        tools: list[Tool],
    ) -> AsyncIterator[Message]:
        raise NotImplementedError
