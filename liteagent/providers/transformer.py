from abc import abstractmethod
from typing import AsyncIterator, Type

from attr.validators import max_len

from liteagent import Message, Tool
from liteagent.internal import register_provider
from liteagent.providers import Provider
from liteagent.message import ToolMessage, ToolRequest, Message, UserMessage, AssistantMessage

from transformers import pipeline
import asyncio
import json


class Transformer(Provider):
    name: str = "transformer"
    model: str

    async def completion(
        self,
        messages: list[Message],
        tools: list[Tool],
        respond_as: Type,
    ) -> AsyncIterator[Message]:
        generator = pipeline("text-generation", model=self.model)

        formatted_prompt = self.format_messages(messages, tools)

        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(
            None,
            lambda: generator(formatted_prompt, return_full_text=False)
        )

        for response in output:
            yield AssistantMessage(content=response["generated_text"])

    @staticmethod
    def format_messages(messages: list[Message], tools: list[Tool]) -> str:
        formatted = ""
        for message in messages:
            match message:
                case UserMessage(content=content):
                    formatted += f"User: {content}\n"
                case AssistantMessage(content=content):
                    formatted += f"Assistant: {content}\n"
                case ToolMessage(id=id, content=content):
                    formatted += f"Tool[{id}]: {content}\n"
                case _:
                    formatted += f"{message.role}: {message.content}\n"

        if tools:
            formatted += "\nAvailable Tools:\n"
            for tool in tools:
                formatted += f"- {tool.name}: {tool.definition}\n"

        return formatted
