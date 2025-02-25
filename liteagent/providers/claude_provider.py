import json
from typing import AsyncIterator, Type, Any, Dict

from anthropic import AsyncAnthropic
from anthropic._types import NOT_GIVEN
from anthropic.types import MessageStreamEvent, ContentBlockDeltaEvent, ToolUseBlock

from liteagent import Tool
from liteagent.providers import Provider
from liteagent.message import ToolMessage, ToolRequest, Message, UserMessage, AssistantMessage, SystemMessage, ImageURL, \
    ImageBase64, MessageContent

from pydantic import BaseModel


class Claude(Provider):
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
    ) -> AsyncIterator[Message]:
        tool_definitions = list(map(lambda tool: {
            "name": tool["function"]["name"],
            "description": tool["function"]["description"],
            "input_schema": tool["function"]["parameters"]
        }, map(lambda tool: tool.definition, tools))) if len(tools) > 0 else NOT_GIVEN

        parsed_messages = list(map(self.map_message, messages))

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
            async for event in self._as_messages(stream):
                yield event

    @staticmethod
    def map_message(message: Message) -> dict:
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

            case AssistantMessage(content=BaseModel() as content):
                return {
                    "role": "assistant",
                    "content": [{
                        "type": "text",
                        "text": content.model_dump_json()
                    }]
                }

            case AssistantMessage(content=str() as content):
                return {
                    "role": "assistant",
                    "content": [{
                        "type": "text",
                        "text": content
                    }]
                }

            case ToolMessage(id=id, content=BaseModel() as content):
                return {
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": id,
                        "content": content.model_dump_json()
                    }]
                }

            case ToolMessage(id=id, content=list() | dict() as content):
                return {
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": id,
                        "content": json.dumps(content)
                    }]
                }

            case ToolMessage(id=id, content=str(content)):
                return {
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": id,
                        "content": content
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
    async def _as_messages(stream) -> AsyncIterator[Message]:
        async for event in stream:
            match event:
                # Match TextEvent
                case event if hasattr(event, "type") and event.type == "text" and hasattr(event, "text"):
                    yield AssistantMessage(content=event.text)

                # Match ContentBlockStopEvent with ToolUseBlock
                case event if (hasattr(event, "type") and event.type == "content_block_stop" and
                               hasattr(event, "content_block") and hasattr(event.content_block, "type") and
                               event.content_block.type == "tool_use"):
                    tool_block = event.content_block
                    yield AssistantMessage(
                        content=ToolRequest(
                            name=tool_block.name,
                            id=tool_block.id,
                            arguments=tool_block.input
                        )
                    )

                # Match direct tool_use events
                case event if (hasattr(event, "type") and event.type == "tool_use" and
                               hasattr(event, "tool_use")):
                    yield AssistantMessage(
                        content=ToolRequest(
                            name=event.tool_use.name,
                            id=event.tool_use.id,
                            arguments=event.tool_use.input
                        )
                    )

                # Default case
                case _:
                    pass
