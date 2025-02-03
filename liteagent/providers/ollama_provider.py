import json
from abc import ABC
from typing import Type, AsyncIterator, Callable

from ollama import AsyncClient, ChatResponse
from pydantic import BaseModel, TypeAdapter

from liteagent import Tool, ToolResponse
from liteagent.message import ToolMessage, ToolRequest, Message, UserMessage, AssistantMessage
from liteagent.providers import Provider


class Ollama(Provider, ABC):
    client: AsyncClient
    model: str
    automatic_download: bool
    downloaded: bool = False
    chat: Callable[[...], ChatResponse | AsyncIterator[ChatResponse]] = None

    def __init__(
        self,
        client: AsyncClient = AsyncClient(),
        model: str = 'llama3.2',
        automatic_download: bool = True,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.model = model
        self.client = client
        self.automatic_download = automatic_download
        self.chat = self.client.chat

    async def completion(
        self,
        messages: list[Message],
        tools: list[Tool] = None,
        respond_as: Type[BaseModel] = None,
    ) -> AsyncIterator[Message]:
        await self._download_if_required()

        tool_definitions = list(map(lambda tool: tool.definition, tools)) if len(tools) > 0 else None
        parsed_messages = list(map(self.to_ollama_format, messages))

        response_format = None if respond_as is None else TypeAdapter(respond_as).json_schema()

        async def handle_response() -> Message:
            response: ChatResponse = await self.chat(
                model=self.model,
                tools=tool_definitions,
                messages=parsed_messages,
                format=response_format
            )

            return AssistantMessage(
                content=respond_as.model_validate_json(response.message.content)
            )

        async def handle_stream():
            response: AsyncIterator[ChatResponse] = await self.chat(
                model=self.model,
                tools=tool_definitions,
                messages=parsed_messages,
                format=response_format,
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

                    continue

                if respond_as and chunk.message.content and chunk.message.content != '':
                    yield AssistantMessage(
                        content=respond_as.model_validate_json(chunk.message.content)
                    )

                    continue

                if chunk.message.content and chunk.message.content != '':
                    yield AssistantMessage(
                        content=chunk.message.content
                    )

                    continue

        if not respond_as:
            async for response in handle_stream():
                yield response
        else:
            yield await handle_response()

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
    def to_ollama_format(message: Message) -> dict:
        match message:
            case UserMessage(content=content):
                return {
                    "role": "user",
                    "content": content
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

            case AssistantMessage(content=BaseModel() as content):
                return {
                    "role": "assistant",
                    "content": content.model_dump_json(),
                }

            case AssistantMessage(content=str() as content):
                return {
                    "role": "assistant",
                    "content": content,
                }

            case ToolMessage(id=id, content=ToolResponse() as content):
                return {
                    "tool_call_id": id,
                    "role": "tool",
                    "content": json.dumps(content.__tool_response__()),
                    "type": "function"
                }

            case ToolMessage(id=id, content=BaseModel() as content):
                return {
                    "tool_call_id": id,
                    "role": "tool",
                    "content": content.model_dump_json(),
                    "type": "function"
                }

            case ToolMessage(id=id, content=dict() | list() as content):
                return {
                    "tool_call_id": id,
                    "role": "tool",
                    "content": json.dumps(content),
                    "type": "function"
                }

            case ToolMessage(id=id, content=str(content)):
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
