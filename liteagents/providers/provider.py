from abc import abstractmethod

from typing import AsyncIterator, Type

from liteagents import Tool
from liteagents.message import Message


class Provider:
    name: str

    @abstractmethod
    async def completion(
        self,
        messages: list[Message],
        tools: list[Tool],
        respond_as: Type,
    ) -> AsyncIterator[Message]:
        raise NotImplementedError
