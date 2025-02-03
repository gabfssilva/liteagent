from abc import abstractmethod
from typing import AsyncIterator, Type

from liteagent import Message
from liteagent import Tool


class Provider:
    name: str

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    @abstractmethod
    async def completion(
        self,
        messages: list[Message],
        tools: list[Tool],
        respond_as: Type,
    ) -> AsyncIterator[Message]:
        raise NotImplementedError
