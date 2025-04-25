import asyncio
import json
from typing import AsyncIterable, Type

from anthropic import AsyncAnthropic
from anthropic._types import NOT_GIVEN
from pydantic import BaseModel

from liteagent import Tool
from liteagent.internal import register_provider
from liteagent.internal.memoized import MemoizedAsyncIterable
from liteagent.message import ToolMessage, ToolRequest, Message, UserMessage, AssistantMessage, SystemMessage, ImageURL, \
    ImageBase64, MessageContent
from liteagent.provider import Provider


class Anthropic(Provider):
    name: str = "claude"
    args: dict = {}

    def __init__(
        self,
        client: AsyncAnthropic,
        model: str = 'claude-3-7-sonnet-20250219',
        **kwargs
    ):
        self.client = client
        self.model = model
        self.args = kwargs

    async def completion(
        self,
        messages: list[Message],
        tools: list[Tool],
        respond_as: Type,
    ) -> AsyncIterable[Message]:
        tool_definitions = list(map(lambda tool: {
            "name": tool["function"]["name"],
            "description": tool["function"]["description"],
            "input_schema": tool["function"]["parameters"]
        }, map(lambda tool: tool.definition, tools))) if len(tools) > 0 else NOT_GIVEN

        parsed_messages = [await self.map_message(message) for message in messages]

        system = next((msg for msg in messages if isinstance(msg, SystemMessage)), None)
        system_content = system.content if system else NOT_GIVEN

        parsed_messages = [msg for msg in parsed_messages if msg.get("role") != "system"]

        async with self.client.messages.stream(
            model=self.model,
            messages=parsed_messages,
            system=system_content,
            tools=tool_definitions,
            **self.args
        ) as stream:
            async for event in await self._as_messages(stream):
                yield event

    @staticmethod
    async def map_message(message: Message) -> dict:
        match message:
            case UserMessage(content=content):
                def map_content(item: MessageContent) -> list[dict]:
                    match item:
                        case ImageURL(url=url):
                            return [{"type": "image", "source": {"type": "url", "url": url}}]
                        case ImageBase64(base64=base64_str):
                            return [{"type": "image",
                                     "source": {"type": "base64", "media_type": "image/jpeg", "data": base64_str}}]
                        case str() as text:
                            return [{"type": "text", "text": text}]
                        case list() as content_list:
                            return [mapped for c in content_list for mapped in map_content(c)]
                        case _:
                            raise ValueError(f"Invalid message type: {type(item)}")

                return {
                    "role": "user",
                    "content": map_content(content)
                }

            case AssistantMessage(content=ToolRequest(id=id, name=name, arguments=BaseModel() as arguments)):
                return {
                    "role": "assistant",
                    "content": [{
                        "type": "tool_use",
                        "id": id,
                        "name": name,
                        "input": arguments.model_dump()
                    }]
                }

            case AssistantMessage(content=ToolRequest(id=id, name=name, arguments=dict() as arguments)):
                return {
                    "role": "assistant",
                    "content": [{
                        "type": "tool_use",
                        "id": id,
                        "name": name,
                        "input": arguments
                    }]
                }

            case AssistantMessage(content=ToolRequest(id=id, name=name, arguments=str(arguments))):
                try:
                    parsed_args = json.loads(arguments)
                    args_to_use = parsed_args
                except:
                    args_to_use = arguments

                return {
                    "role": "assistant",
                    "content": [{
                        "type": "tool_use",
                        "id": id,
                        "name": name,
                        "input": args_to_use
                    }]
                }

            case AssistantMessage() as message:
                return {
                    "role": "assistant",
                    "content": [{
                        "type": "text",
                        "text": await message.content_as_string()
                    }]
                }

            case ToolMessage(id=id) as message:
                return {
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": id,
                        "content": await message.content_as_string()
                    }]
                }

            case Message(role=role, content=content):
                return {
                    "role": role,
                    "content": [{"type": "text", "text": str(content)}]
                }

            case _:
                raise ValueError(f"Invalid message type: {type(message)}")

    @staticmethod
    async def _as_messages(stream) -> AsyncIterable[Message]:
        message_stream: MemoizedAsyncIterable[Message] = MemoizedAsyncIterable[Message]()
        assistant_stream: MemoizedAsyncIterable | None = None

        async def consume():
            nonlocal message_stream, assistant_stream

            try:
                async for event in stream:
                    match event:
                        # Match TextEvent
                        case event if hasattr(event, "type") and event.type == "text" and hasattr(event, "text"):
                            if not assistant_stream:
                                assistant_stream = MemoizedAsyncIterable[str]()
                                await assistant_stream.emit(event.text)
                                await message_stream.emit(AssistantMessage(content=assistant_stream))
                            else:
                                await assistant_stream.emit(event.text)

                        case event if (hasattr(event, "type") and event.type == "content_block_stop" and
                                       hasattr(event, "content_block") and hasattr(event.content_block, "type") and
                                       event.content_block.type == "tool_use"):
                            tool_block = event.content_block
                            await message_stream.emit(AssistantMessage(
                                content=ToolRequest(
                                    name=tool_block.name,
                                    id=tool_block.id,
                                    arguments=tool_block.input
                                )
                            ))

                        case event if (hasattr(event, "type") and event.type == "tool_use" and
                                       hasattr(event, "tool_use")):
                            await message_stream.emit(AssistantMessage(
                                content=ToolRequest(
                                    name=event.tool_use.name,
                                    id=event.tool_use.id,
                                    arguments=event.tool_use.input
                                )
                            ))

                        case _:
                            pass

                if assistant_stream:
                    await assistant_stream.close()

                await message_stream.close()

            except Exception as e:
                if assistant_stream:
                    await assistant_stream.close()
                await message_stream.close()
                raise

        asyncio.create_task(consume())

        return message_stream

    async def destroy(self):
        """
        Close and clean up resources used by the Claude provider.
        Closes the AsyncAnthropic client.
        """
        if hasattr(self, 'client') and hasattr(self.client, 'close'):
            await self.client.close()

    def __repr__(self):
        return f"Anthropic({self.model})"


@register_provider
def anthropic(
    client: AsyncAnthropic,
    model: str = 'claude-3-7-sonnet-20250219',
    **kwargs
) -> Provider:
    return Anthropic(
        model=model,
        client=client,
        **kwargs
    )
