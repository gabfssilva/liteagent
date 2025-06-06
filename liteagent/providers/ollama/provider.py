import uuid
from abc import ABC
import asyncio
from typing import Type, AsyncIterable, Callable

import httpx
from ollama import AsyncClient, ChatResponse
from pydantic import BaseModel, TypeAdapter

from liteagent import Tool
from liteagent.internal.cleanup import register_provider
from liteagent.internal.memoized import MemoizedAsyncIterable
from liteagent.message import ToolMessage, ToolRequest, Message, UserMessage, AssistantMessage, ImageBase64, ImageURL, \
    Image, ImageBytes
from liteagent.provider import Provider


class Ollama(Provider, ABC):
    name: str = "ollama"
    client: AsyncClient
    model: str
    automatic_download: bool
    downloaded: bool = False
    chat: Callable[[...], ChatResponse | AsyncIterable[ChatResponse]] = None

    def __init__(
        self,
        client: AsyncClient = AsyncClient(),
        model: str = 'llama3.2',
        automatic_download: bool = True,
    ) -> None:
        self.model = model
        self.client = client
        self.automatic_download = automatic_download
        self.chat = self.client.chat

    async def completion(
        self,
        messages: list[Message],
        tools: list[Tool] = None,
        respond_as: Type[BaseModel] = None,
    ) -> AsyncIterable[Message]:
        await self._download_if_required()

        tool_definitions = list(map(lambda tool: tool.definition, tools)) if len(tools) > 0 else None
        parsed_messages = [await self.to_ollama_format(message) for message in messages]

        response_format = None if respond_as is None else TypeAdapter(respond_as).json_schema()

        if not respond_as:
            response: AsyncIterable[ChatResponse] = await self.chat(
                model=self.model,
                tools=tool_definitions,
                messages=parsed_messages,
                format=response_format,
                stream=True
            )

            async for message in self._as_messages(response, respond_as):
                yield message
        else:
            response: ChatResponse = await self.chat(
                model=self.model,
                tools=tool_definitions,
                messages=parsed_messages,
                format=response_format
            )

            message_stream = MemoizedAsyncIterable[Message]()
            await message_stream.emit(AssistantMessage(
                content=respond_as.model_validate_json(response.message.content)
            ))
            await message_stream.close()

            async for message in message_stream:
                yield message

    @staticmethod
    def _as_messages(
        response: AsyncIterable[ChatResponse],
        respond_as: Type[BaseModel] = None
    ) -> AsyncIterable[Message]:
        message_stream: MemoizedAsyncIterable[Message] = MemoizedAsyncIterable[Message]()

        async def consume():
            nonlocal message_stream

            assistant_stream: MemoizedAsyncIterable | None = None

            try:
                async for chunk in response:
                    for call in (chunk.message.tool_calls or []):
                        await message_stream.emit(AssistantMessage(
                            content=ToolRequest(
                                id=f'{uuid.uuid4()}',
                                name=call.function.name,
                                arguments=dict(call.function.arguments)
                            )
                        ))

                        continue

                    if respond_as and chunk.message.content and chunk.message.content != '':
                        await message_stream.emit(AssistantMessage(
                            content=respond_as.model_validate_json(chunk.message.content)
                        ))
                        continue

                    if chunk.message.content and chunk.message.content != '':
                        if not assistant_stream:
                            assistant_stream = MemoizedAsyncIterable[str]()
                            await assistant_stream.emit(chunk.message.content)
                            await message_stream.emit(AssistantMessage(content=assistant_stream))
                        else:
                            await assistant_stream.emit(chunk.message.content)

                        continue

                if assistant_stream:
                    await assistant_stream.close()
                    assistant_stream = None

                await message_stream.close()

            except Exception as e:
                if assistant_stream:
                    await assistant_stream.close(e)
                await message_stream.close(e)
                raise

        asyncio.create_task(consume())

        return message_stream

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

    @staticmethod
    async def to_ollama_format(message: Message) -> dict:
        match message:
            case UserMessage(content=str() as content):
                return {
                    "role": "user",
                    "content": content,
                }

            case UserMessage(content=ImageURL() | ImageBase64() as content):
                async def image_content(image: Image):
                    match image:
                        case ImageURL(url=url):
                            async with httpx.AsyncClient() as client:
                                response = await client.get(url)
                                return response.content
                        case ImageBase64(base64=base64_str):
                            return base64_str
                        case ImageBytes(bytes=bytes):
                            return bytes
                        case _:
                            return None

                return {
                    "role": "user",
                    "images": [await image_content(content)],
                }

            case AssistantMessage(content=ToolRequest(id=id, name=name, arguments=BaseModel() as arguments)):
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

            case AssistantMessage(content=ToolRequest(id=id, name=name, arguments=dict() as arguments)):
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

            case AssistantMessage(content=ToolRequest(id=id, name=name, arguments=str(arguments))):
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

            case AssistantMessage() as message:
                return {
                    "role": "assistant",
                    "content": await message.content_as_string(),
                }

            case ToolMessage(tool_use_id=id, content=content) as message:
                return {
                    "tool_call_id": id,
                    "role": "tool",
                    "content": await message.content_as_string(),
                    "type": "function"
                }

            case Message(role=role, content=content):
                return {
                    "role": role,
                    "content": content,
                }

            case _:
                raise ValueError(f"Invalid message type: {type(message)}")

    def __repr__(self):
        return f"Ollama({self.model})"


@register_provider
def ollama(
    model: str = 'llama3.2',
    automatic_download: bool = True
) -> Provider:
    return Ollama(model=model, automatic_download=automatic_download)
