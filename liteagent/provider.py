from abc import abstractmethod
from typing import AsyncIterator, Type

from .message import Message
from .tool import Tool

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
        
    async def destroy(self):
        """
        Close and clean up any resources held by this provider.
        This method should be called when the program is about to exit.
        Default implementation does nothing, but providers should override
        this to handle their specific cleanup needs.
        """
        pass
