import asyncio
from typing import AsyncIterable, Type

from pydantic import BaseModel, TypeAdapter

from liteagent import Tool
from liteagent.internal import register_provider
from liteagent.internal.memoized import MemoizedAsyncIterable
from liteagent.message import ToolRequest, Message, AssistantMessage, ToolMessage
from liteagent.provider import Provider

from google import genai
from google.genai import types

class Google(Provider):
    name: str = "gemini"

    def __init__(self, client: genai.Client, model: str = "gemini-2.0-flash-exp", **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.model = model
        self.args = kwargs

    async def completion(
        self,
        messages: list[Message],
        tools: list[Tool] = None,
        respond_as: Type[BaseModel] = None,
    ) -> AsyncIterable[Message]:
        prompt = ""
        for message in messages:
            prompt += f"{message.role.capitalize()}: {await message.content_as_string()}\n"

        tool_definitions = [self._tool_def(tool) for tool in tools] if tools else None

        response_format = None
        if respond_as:
            response_format = TypeAdapter(respond_as).json_schema()

        config = {}
        if response_format:
            config["response_mime_type"] = "application/json"
            config["response_schema"] = response_format
        if tool_definitions:
            config["tools"] = [types.Tool(function_declarations=tool_definitions)]

        stream = await self.client.aio.models.generate_content_stream(
            model=self.model,
            contents=prompt,
            config=config,
            **self.args
        )

        async for message in await self._as_messages(stream, respond_as):
            yield message

    async def _as_messages(self, stream, respond_as: Type[BaseModel] = None) -> AsyncIterable[Message]:
        message_stream: MemoizedAsyncIterable[Message] = MemoizedAsyncIterable[Message]()
        assistant_stream: MemoizedAsyncIterable | None = None

        async def consume():
            nonlocal message_stream, assistant_stream

            assistant_message = ""

            try:
                async for chunk in stream:
                    if hasattr(chunk, "function_calls") and chunk.function_calls:
                        for call in chunk.function_calls:
                            await message_stream.emit(AssistantMessage(
                                content=ToolRequest(
                                    id=str(call.id or "0"),
                                    name=call.name,
                                    arguments=call.args,
                                )
                            ))

                        if assistant_stream:
                            await assistant_stream.close()
                        await message_stream.close()
                        return

                    if respond_as:
                        assistant_message = assistant_message + chunk.text

                        try:
                            parsed_content = respond_as.model_validate_json(assistant_message)
                            await message_stream.emit(AssistantMessage(content=parsed_content))

                            if assistant_stream:
                                await assistant_stream.close()
                            await message_stream.close()
                            return
                        except Exception:
                            continue

                    if hasattr(chunk, "text") and chunk.text:
                        if not assistant_stream:
                            assistant_stream = MemoizedAsyncIterable[str]()
                            await assistant_stream.emit(chunk.text)
                            await message_stream.emit(AssistantMessage(content=assistant_stream))
                        else:
                            await assistant_stream.emit(chunk.text)

                if assistant_stream:
                    await assistant_stream.close()

                await message_stream.close()

            except Exception as e:
                if assistant_stream:
                    await assistant_stream.close()
                await message_stream.close()
                raise e

        asyncio.create_task(consume())

        return message_stream

    def _tool_def(self, tool: Tool) -> types.FunctionDeclaration:
        return types.FunctionDeclaration(
            name=tool.name,
            parameters=self._recursive_purge_dict_key(tool.input.model_json_schema(), 'title'),
            description=tool.description,
        )

    def _recursive_purge_dict_key(self, d: dict[str, any], k: str) -> None:
        if isinstance(d, dict):
            for key in list(d.keys()):
                if key == k and "type" in d.keys():
                    del d[key]
                else:
                    self._recursive_purge_dict_key(d[key], k)

@register_provider
def google(
    client: genai.Client = None,
    model: str = "gemini-2.0-flash"
) -> Provider: 
    return Google(client or genai.Client(), model)
