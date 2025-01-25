from abc import abstractmethod

from typing import AsyncIterator, Type

from liteagent import Tool
from liteagent import Message


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
