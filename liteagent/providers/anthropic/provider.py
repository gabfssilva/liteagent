import json
import uuid
from typing import AsyncIterable, Type, List

from anthropic import AsyncAnthropic
from anthropic._types import NOT_GIVEN
from anthropic.types import MessageParam, TextBlockParam, ImageBlockParam, ToolResultBlockParam, ToolUseBlockParam, \
    URLImageSourceParam, Base64ImageSourceParam

from liteagent import Tool, ImagePath
from liteagent.codec import to_json_str, to_json
from liteagent.internal import register_provider
from liteagent.message import ToolMessage, Message, UserMessage, AssistantMessage, SystemMessage, ImageURL
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

    async def completion(self, messages: list[Message], tools: list[Tool], respond_as: Type) -> AsyncIterable[Message]:
        tool_definitions = [
            {"name": t["function"]["name"], "description": t["function"]["description"],
             "input_schema": t["function"]["parameters"]}
            for t in map(lambda tool: tool.definition, tools)
        ] if tools else NOT_GIVEN

        parsed_messages = [await self._to_anthropic(m) for m in messages]
        parsed_messages = filter(lambda m: m is not None, parsed_messages)
        system_msg = next((m for m in messages if isinstance(m, SystemMessage)), None)
        system_content = system_msg.content if system_msg else NOT_GIVEN

        cache = {}

        async with self.client.messages.stream(
            model=self.model,
            messages=parsed_messages,
            system=system_content,
            tools=tool_definitions,
            **self.args
        ) as stream:
            async for event in stream:
                for msg in self._from_anthropic(event, cache):
                    yield msg

    def _from_anthropic(self, event, cache: dict) -> list[Message]:
        messages = []

        if event.type == "message_start":
            cache["current_message"] = {
                "stream_id": str(uuid.uuid4())
            }

        elif event.type == "content_block_start":
            cache.setdefault("content_blocks", {})[event.index] = {
                "type": event.content_block.type,
                "id": getattr(event.content_block, "id", None),
                "name": getattr(event.content_block, "name", None),
                "data": ""  # accumulate raw string only
            }

        elif event.type == "content_block_delta":
            block = cache["content_blocks"].get(event.index)
            if not block:
                return messages

            if event.delta.type == "text_delta":
                block["data"] += event.delta.text
                messages.append(AssistantMessage(content=AssistantMessage.TextChunk(
                    value=event.delta.text,
                    accumulated=block["data"],
                    stream_id=cache["current_message"]["stream_id"]
                )))

            elif event.delta.type == "input_json_delta":
                block["data"] += event.delta.partial_json or ""
                messages.append(AssistantMessage(content=AssistantMessage.ToolUseChunk(
                    tool_use_id=block['id'],
                    name=block["name"],
                    accumulated_arguments=block["data"]
                )))

        elif event.type == "content_block_stop":
            block = cache["content_blocks"].pop(event.index, None)
            if not block:
                return messages

            if block["type"] == "text":
                messages.append(AssistantMessage(content=AssistantMessage.TextComplete(
                    accumulated=block["data"],
                    stream_id=cache["current_message"]["stream_id"]
                )))

            elif block["type"] == "tool_use":
                messages.append(AssistantMessage(content=AssistantMessage.ToolUse(
                    tool_use_id=block["id"],
                    name=block["name"],
                    arguments=json.loads(block["data"])
                )))

        elif event.type == "message_stop":
            cache.pop("current_message", None)

        return messages

    async def _map_content(self, content) -> List[TextBlockParam | ImageBlockParam]:
        """Map different content types to Anthropic content blocks."""
        if isinstance(content, str):
            return [TextBlockParam(type="text", text=content)]

        if isinstance(content, ImageURL):
            return [ImageBlockParam(
                type="image",
                source=URLImageSourceParam(type="url", url=content.url)
            )]

        if isinstance(content, ImagePath):
            return [ImageBlockParam(
                type="image",
                source=Base64ImageSourceParam(
                    type="base64",
                    media_type=content.image_type(),
                    data=await content.as_base64()
                )
            )]

        if isinstance(content, list):
            return [m for item in content for m in await self._map_content(item)]

        raise ValueError(f"Invalid content type: {type(content)}")

    async def _to_anthropic(self, message: Message) -> MessageParam | None:
        match message:
            case UserMessage(content=content):
                return MessageParam(
                    role="user",
                    content=await self._map_content(content)
                )

            case AssistantMessage(
                content=AssistantMessage.ToolUse(tool_use_id=tool_use_id, name=name, arguments=args)
            ):
                return MessageParam(
                    role="assistant",
                    content=[ToolUseBlockParam(
                        type="tool_use",
                        id=tool_use_id,
                        name=name,
                        input=await to_json(args)
                    )]
                )
            case AssistantMessage() as message if message.complete():
                return MessageParam(
                    role="assistant",
                    content=[TextBlockParam(
                        type="text",
                        text=await to_json_str(message.content)
                    )]
                )
            case ToolMessage(tool_use_id=tool_use_id, content=content):
                return MessageParam(
                    role="user",
                    content=[ToolResultBlockParam(
                        type="tool_result",
                        tool_use_id=tool_use_id,
                        content=await to_json_str(content)
                    )]
                )

            case SystemMessage():
                return None

            case _:
                raise ValueError(f"Unknown message type: {message}")

    async def destroy(self):
        if hasattr(self.client, 'close'):
            await self.client.close()

    def __repr__(self):
        return f"Anthropic({self.model})"


@register_provider
def anthropic(client: AsyncAnthropic, model: str = 'claude-3-7-sonnet-20250219', **kwargs) -> Provider:
    return Anthropic(client=client, model=model, **kwargs)


def merge_json(old, new):
    if not isinstance(old, dict) or not isinstance(new, dict):
        return new
    result = old.copy()
    for k, v in new.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = merge_json(result[k], v)
        else:
            result[k] = v
    return result
