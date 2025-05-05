import json
import uuid
from typing import AsyncIterable, Type

from anthropic import AsyncAnthropic
from anthropic._types import NOT_GIVEN
from pydantic import BaseModel

from liteagent import Tool, ImagePath
from liteagent.codec import to_json_str
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

    async def _map_content(self, content):
        if isinstance(content, str):
            return [{"type": "text", "text": content}]
        if isinstance(content, ImageURL):
            return [{"type": "image", "source": {"type": "url", "url": content.url}}]
        if isinstance(content, ImagePath):
            return [{"type": "image", "source": {
                "type": "base64",
                "media_type": f"image/{content.image_type()}",
                "data": await content.as_base64()
            }}]
        if isinstance(content, list):
            out = []
            for item in content:
                out.extend(await self._map_content(item))
            return out
        raise ValueError(f"Invalid content type: {type(content)}")

    async def _to_anthropic(self, message: Message) -> dict:
        match message:
            case UserMessage(content=content):
                return {
                    "role": "user",
                    "content": await self._map_content(content)
                }
            case AssistantMessage(
                content=AssistantMessage.ToolUse(tool_use_id=id, name=name, arguments=BaseModel() as args)):
                return {"role": "assistant",
                        "content": [{"type": "tool_use", "id": id, "name": name, "input": args.model_dump()}]}
            case AssistantMessage(
                content=AssistantMessage.ToolUse(tool_use_id=id, name=name, arguments=dict() as args)):
                return {"role": "assistant", "content": [{"type": "tool_use", "id": id, "name": name, "input": args}]}
            case AssistantMessage(content=AssistantMessage.ToolUse(tool_use_id=id, name=name, arguments=str(args))):
                try:
                    parsed = json.loads(args)
                except:
                    parsed = args
                return {"role": "assistant", "content": [{"type": "tool_use", "id": id, "name": name, "input": parsed}]}
            case AssistantMessage() as message if message.complete():
                return {"role": "assistant", "content": [{"type": "text", "text": await to_json_str(message.content)}]}
            case ToolMessage(tool_use_id=id) as message:
                content = await to_json_str(message.content) if not isinstance(message.content,
                                                                               str) else message.content
                return {"role": "user", "content": [{"type": "tool_result", "tool_use_id": id, "content": content}]}
            case SystemMessage(content=content):
                return {"role": "system", "content": str(content)}
            case Message(role=role, content=content):
                return {"role": role, "content": [{"type": "text", "text": str(content)}]}
            case _:
                raise ValueError(f"Unknown message type: {message}")

    async def completion(self, messages: list[Message], tools: list[Tool], respond_as: Type) -> AsyncIterable[Message]:
        tool_definitions = [
            {"name": t["function"]["name"], "description": t["function"]["description"],
             "input_schema": t["function"]["parameters"]}
            for t in map(lambda tool: tool.definition, tools)
        ] if tools else NOT_GIVEN

        parsed_messages = [await self._to_anthropic(m) for m in messages]
        system_msg = next((m for m in messages if isinstance(m, SystemMessage)), None)
        system_content = system_msg.content if system_msg else NOT_GIVEN

        parsed_messages = [m for m in parsed_messages if m["role"] != "system"]
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

        if event.type == "text":
            acc = cache.setdefault("last_assistant_message", {"accumulated": "", "stream_id": f"{uuid.uuid4()}"})
            acc['accumulated'] += event.text
            messages.append(AssistantMessage(content=AssistantMessage.TextChunk(
                value=event.text,
                accumulated=acc['accumulated'],
                stream_id=acc['stream_id']
            )))

        elif event.type == "content_block_delta" and event.delta.type == "tool_use":
            key = f"tool-{event.delta.id}"
            acc = cache.get(key, {"name": event.delta.name, "accumulated": {}})
            acc["accumulated"] = merge_json(acc.get("accumulated", {}), event.delta.input or {})
            cache[key] = acc
            messages.append(AssistantMessage(content=AssistantMessage.ToolUseChunk(
                tool_use_id=event.delta.id,
                name=acc["name"],
                accumulated_arguments=acc["accumulated"]
            )))

        elif event.type == "content_block_stop" and event.content_block.type == "tool_use":
            acc = cache.pop("last_assistant_message", None)
            if acc:
                messages.append(AssistantMessage(content=AssistantMessage.TextComplete(
                    accumulated=acc['accumulated'],
                    stream_id=acc['stream_id']
                )))
            tool_id = event.content_block.id
            tool_acc = cache.pop(f"tool-{tool_id}", {})
            messages.append(AssistantMessage(content=AssistantMessage.ToolUse(
                tool_use_id=tool_id,
                name=event.content_block.name,
                arguments=tool_acc.get("accumulated", {})
            )))

        elif event.type == "message_stop":
            acc = cache.pop("last_assistant_message", None)
            if acc:
                messages.append(AssistantMessage(content=AssistantMessage.TextComplete(
                    accumulated=acc['accumulated'],
                    stream_id=acc['stream_id']
                )))
            for key in list(cache.keys()):
                if key.startswith("tool-"):
                    tool_acc = cache.pop(key)
                    tool_id = key.replace("tool-", "")
                    messages.append(AssistantMessage(content=AssistantMessage.ToolUse(
                        tool_use_id=tool_id,
                        name=tool_acc["name"],
                        arguments=tool_acc.get("accumulated", {})
                    )))

        return messages

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
