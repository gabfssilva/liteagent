from typing import Type, AsyncIterator

from openai import BaseModel

from liteagent import Tool, ToolResponse
from liteagent.message import ToolMessage, ToolRequest, Message, UserMessage, AssistantMessage
from liteagent.providers import Provider

from vllm import LLM


class VLLM(Provider):
    llm: LLM

    async def completion(
        self,
        messages: list[Message],
        tools: list[Tool] = None,
        respond_as: Type[BaseModel] = None,
    ) -> AsyncIterator[Message]:
        pass
