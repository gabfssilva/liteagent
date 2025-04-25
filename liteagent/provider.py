from abc import abstractmethod
from typing import AsyncIterable, Type

from .message import Message
from .tool import Tool


class Provider:
    @abstractmethod
    def completion(
        self,
        messages: list[Message],
        tools: list[Tool],
        respond_as: Type,
    ) -> AsyncIterable[Message]:
        raise NotImplementedError

    async def destroy(self):
        """
        Close and clean up any resources held by this provider.
        This method should be called when the program is about to exit.
        Default implementation does nothing, but providers should override
        this to handle their specific cleanup needs.
        """
        pass
