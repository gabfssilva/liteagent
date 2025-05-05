import uuid
from typing import Type, AsyncIterable

from openai import AsyncOpenAI, NOT_GIVEN
from openai.lib.streaming.chat import ChatCompletionStreamEvent, ContentDoneEvent, \
    FunctionToolCallArgumentsDoneEvent, FunctionToolCallArgumentsDeltaEvent, ChunkEvent
from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import Choice, ChoiceDelta

from liteagent.codec import to_json_str
from liteagent.message import Message, SystemMessage, UserMessage, ImageURL, ImagePath, ToolMessage, AssistantMessage
from liteagent import Tool, Provider


class OpenAICompatible(Provider):
    name: str
    args: dict = {}

    def __init__(self, client: AsyncOpenAI, name: str = None, model: str = 'gpt-4o-mini', **kwargs):
        self.client = client
        self.model = model
        self.args = kwargs
        self.name = name or "OpenAI"

    async def completion(
        self,
        messages: list[Message],
        tools: list[Tool],
        respond_as: Type,
    ) -> AsyncIterable[Message]:
        tool_definitions = [tool.definition for tool in tools] if tools else NOT_GIVEN

        oai_messages = []
        pending_tool_calls: dict[str, dict] = {}

        for i, msg in enumerate(messages):
            if isinstance(msg, AssistantMessage) and isinstance(msg.content, AssistantMessage.ToolUse):
                tool_call_dict = await self._to_oai(msg)
                if tool_call_dict:
                    pending_tool_calls[msg.content.tool_use_id] = tool_call_dict
                continue

            if isinstance(msg, ToolMessage) and msg.tool_use_id in pending_tool_calls:
                oai_messages.append(pending_tool_calls.pop(msg.tool_use_id))
                oai_messages.append(await self._to_oai(msg))
                continue

            converted = await self._to_oai(msg)
            if converted:
                oai_messages.append(converted)

        oai_messages.extend(pending_tool_calls.values())

        cache: dict = {}

        async with self.client.beta.chat.completions.stream(
            model=self.model,
            messages=oai_messages,
            tools=tool_definitions,
            response_format=respond_as or NOT_GIVEN,
            **self.args
        ) as stream:
            async for event in stream:
                message = self._from_oai(event, cache)
                if message:
                    yield message

    @staticmethod
    def _from_oai(event: ChatCompletionStreamEvent, cache: dict) -> Message | None:
        match event:
            case ChunkEvent(
                chunk=ChatCompletionChunk(
                    choices=[
                        Choice(delta=ChoiceDelta(tool_calls=None, content=str(content)))
                    ]
                )
            ) if content != "":
                acc = cache.get("last_assistant_message", None)

                if not acc:
                    acc = {
                        "accumulated": "",
                        "stream_id": f'{uuid.uuid4()}'
                    }

                    cache["last_assistant_message"] = acc

                acc['accumulated'] = acc['accumulated'] + content

                return AssistantMessage(content=AssistantMessage.TextChunk(
                    value=content,
                    accumulated=acc['accumulated'],
                    stream_id=acc['stream_id']
                ))

            case ContentDoneEvent(content=content, parsed=parsed):
                acc = cache.pop("last_assistant_message", None)
                stream_id = acc['stream_id'] if acc else f'{uuid.uuid4()}'

                return AssistantMessage(content=parsed if parsed is not None else AssistantMessage.TextComplete(
                    accumulated=content,
                    stream_id=stream_id
                ))

            case FunctionToolCallArgumentsDeltaEvent(
                name=name,
                index=index,
                arguments=arguments,
                parsed_arguments=parsed,
            ):
                cache.pop("last_assistant_message", None)

                id = cache.get(f"{name}-{index}", None)

                if not id:
                    id = f'{uuid.uuid4()}'
                    cache[f"{name}-{index}"] = id

                return AssistantMessage(content=AssistantMessage.ToolUseChunk(
                    tool_use_id=id,
                    name=name,
                    accumulated_arguments=arguments if not parsed or len(parsed) == 0 else parsed,
                ))

            case FunctionToolCallArgumentsDoneEvent(
                name=name,
                index=index,
                arguments=arguments,
                parsed_arguments=parsed
            ):
                cache.pop("last_assistant_message", None)

                id = cache.get(f"{name}-{index}", None)

                if not id:
                    id = f'{uuid.uuid4()}'
                    cache[f"{name}-{index}"] = id

                return AssistantMessage(content=AssistantMessage.ToolUse(
                    tool_use_id=id,
                    name=name,
                    arguments=parsed or arguments
                ))

            case _:
                return None

    @staticmethod
    async def _to_oai(message: Message) -> dict | None:
        match message:
            case SystemMessage(content=content):
                return {
                    "role": "system",
                    "content": content,
                }

            case UserMessage(content=str() as content):
                return {
                    "role": "user",
                    "content": [{
                        "type": "text",
                        "text": content
                    }]
                }

            case UserMessage(content=ImageURL(url=url)):
                return {
                    "role": "user",
                    "content": [{
                        "type": "image_url",
                        "image_url": {"url": url}
                    }]
                }

            case UserMessage(content=ImagePath() as image):
                return {
                    "role": "user",
                    "content": [{
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{image.image_type()};base64,{await image.as_base64()}"
                        }
                    }]
                }

            case ToolMessage() as message:
                return {
                    "role": "tool",
                    "tool_call_id": message.tool_use_id,
                    "content": await to_json_str(message.content),
                }

            case AssistantMessage(content=AssistantMessage.ToolUseChunk() | AssistantMessage.TextChunk()):
                return None

            case AssistantMessage(content=AssistantMessage.ToolUse(tool_use_id=id, name=name, arguments=arguments)):
                return {
                    "role": "assistant",
                    "tool_calls": [{
                        "id": id,
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": await to_json_str(arguments)
                        }
                    }]
                }

            case AssistantMessage() as message:
                return {
                    "role": "assistant",
                    "content": await to_json_str(message.content),
                }

            case _:
                raise Exception(f"Unknown message: {message}")

    def __repr__(self):
        return f"OpenAICompatible({self.model})"
