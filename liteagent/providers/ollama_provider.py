import asyncio
from abc import ABC
from typing import Type, AsyncIterator

import ollama
from pydantic import BaseModel, TypeAdapter

import json

from liteagent import Tool
from liteagent.providers import Provider
from liteagent.message import ToolMessage, ToolRequest, Message, UserMessage, AssistantMessage, SystemMessage

from ollama import AsyncClient, ChatResponse


class Ollama(Provider, ABC):
    client: AsyncClient
    model: str
    automatic_download: bool
    downloaded: bool = False

    def __init__(self, client: AsyncClient = AsyncClient(), model: str = 'llama3.2', automatic_download: bool = True):
        self.model = model
        self.client = client
        self.automatic_download = automatic_download

    async def completion(
        self,
        messages: list[Message],
        tools: list[Tool] = None,
        respond_as: Type = str,
    ) -> AsyncIterator[Message]:
        await self._download_if_required()

        def map_message(message: Message) -> dict:
            match message:
                case UserMessage(content=content):
                    return {
                        "role": "user",
                        "content": content,
                    }

                case AssistantMessage(content=str(content)):
                    return {
                        "role": "assistant",
                        "content": content,
                    }

                case AssistantMessage(content=ToolRequest(id=id, name=name, arguments=arguments)):
                    if isinstance(arguments, BaseModel):
                        arguments = arguments.model_dump()

                    return {
                        "role": "assistant",
                        "tool_calls": [{
                            "id": id,
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": arguments,
                            }
                        }]
                    }

                case ToolMessage(id=id, content=content):
                    if isinstance(content, BaseModel):
                        content = content.model_dump_json()
                    elif isinstance(content, dict):
                        content = json.dumps(content)
                    else:
                        content = f'{content}'

                    return {
                        "tool_call_id": id,
                        "role": "tool",
                        "content": content,
                        "type": "function"
                    }

                case Message(role=role, content=content):
                    return {
                        "role": role,
                        "content": content,
                    }

                case _:
                    raise ValueError(f"Invalid message type: {type(message)}")

        tool_definitions = list(map(lambda tool: tool.definition, tools)) if len(tools) > 0 else None
        parsed_messages = list(map(map_message, messages))

        response: AsyncIterator[ChatResponse] = await self.client.chat(
            model=self.model,
            tools=tool_definitions,
            messages=parsed_messages,
            format=None if respond_as is None else TypeAdapter(respond_as).json_schema(),
            stream=True
        )

        async for chunk in response:
            for call in (chunk.message.tool_calls or []):
                yield AssistantMessage(
                    content=ToolRequest(
                        id='0',
                        name=call.function.name,
                        arguments=dict(call.function.arguments)
                    )
                )

            if chunk.message.content and chunk.message.content != '':
                yield AssistantMessage(
                    content=chunk.message.content
                )

    async def _download_if_required(self):
        if self.automatic_download and not self.downloaded:
            available_models = (await self.client.list()).models

            if not any(filter(lambda m: m.model == self.model, available_models)):
                from rich.progress import Progress

                with Progress() as progress:
                    download_task = progress.add_task(f"[blue]Downloading {self.model}...")
                    response = await self.client.pull(model=self.model, stream=True)

                    async for update in response:
                        progress.update(download_task, completed=update.completed, total=update.total)

            self.downloaded = True
