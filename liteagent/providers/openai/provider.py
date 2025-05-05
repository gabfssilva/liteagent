import uuid
from typing import Type, AsyncIterable

from openai import AsyncOpenAI, NOT_GIVEN
from openai.lib.streaming.chat import ChatCompletionStreamEvent, ContentDoneEvent, \
    FunctionToolCallArgumentsDoneEvent, FunctionToolCallArgumentsDeltaEvent, ChunkEvent
from openai.types.chat import ChatCompletionChunk, ChatCompletionMessageParam, ChatCompletionSystemMessageParam, \
    ChatCompletionUserMessageParam, ChatCompletionContentPartTextParam, \
    ChatCompletionContentPartImageParam, ChatCompletionToolMessageParam, ChatCompletionAssistantMessageParam, \
    ChatCompletionMessageToolCallParam
from openai.types.chat.chat_completion_chunk import Choice, ChoiceDelta

from liteagent import Tool, Provider
from liteagent.codec import to_json_str
from liteagent.message import Message, SystemMessage, UserMessage, ImageURL, ImagePath, ToolMessage, AssistantMessage


class OpenAICompatible(Provider):
    name: str
    args: dict = {}

    def __init__(
        self,
        client: AsyncOpenAI,
        name: str = None,
        model: str = 'gpt-4.1-mini',
        **kwargs
    ):
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
        messages = self._group_tool_uses(self, messages)
        oai_messages = [await self._to_oai(msg) for msg in messages if await self._to_oai(msg)]
        oai_messages = list(filter(lambda m: m is not None, oai_messages))

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
    async def _to_oai(message: Message) -> ChatCompletionMessageParam | None:
        match message:
            case message if not message.complete():
                return None

            case SystemMessage(content=content):
                return ChatCompletionSystemMessageParam(
                    role="system",
                    content=content,
                )

            case UserMessage(content=str() as content):
                return ChatCompletionUserMessageParam(
                    role="user",
                    content=[ChatCompletionContentPartTextParam(
                        text=content,
                        type='text'
                    )]
                )

            case UserMessage(content=str() as content):
                return ChatCompletionUserMessageParam(
                    role="user",
                    content=[ChatCompletionContentPartTextParam(
                        text=content,
                        type='text'
                    )]
                )

            case UserMessage(content=ImageURL(url=url)):
                return ChatCompletionUserMessageParam(
                    role="user",
                    content=[ChatCompletionContentPartImageParam(
                        image_url={
                            "url": url,
                            "detail": "auto"
                        },
                        type='image_url'
                    )]
                )

            case UserMessage(content=ImagePath() as image):
                return ChatCompletionUserMessageParam(
                    role="user",
                    content=[ChatCompletionContentPartImageParam(
                        image_url={
                            "url": f"data:image/{image.image_type()};base64,{await image.as_base64()}",
                            "detail": "auto"
                        },
                        type='image_url'
                    )]
                )

            case ToolMessage() as message:
                return ChatCompletionToolMessageParam(
                    role="tool",
                    tool_call_id=message.tool_use_id,
                    content=await to_json_str(message.content),
                )

            case AssistantMessage(
                content=AssistantMessage.ToolUse(tool_use_id=tool_use_id, name=name, arguments=arguments)):
                return ChatCompletionAssistantMessageParam(
                    role='assistant',
                    tool_calls=[
                        ChatCompletionMessageToolCallParam(
                            id=tool_use_id,
                            type='function',
                            function={
                                "name": name,
                                "arguments": await to_json_str(arguments)
                            }
                        )
                    ]
                )

            case AssistantMessage(content=AssistantMessage.TextComplete(accumulated=content)):
                return ChatCompletionAssistantMessageParam(
                    role='assistant',
                    content=content
                )

            case _:
                raise Exception(f"Unknown message: {message}")

    @staticmethod
    def _group_tool_uses(self, messages: list[Message]) -> list[Message]:
        grouped_tool_use = []
        pending_tool_calls = {}

        for i, msg in enumerate(messages):
            if isinstance(msg, AssistantMessage) and isinstance(msg.content, AssistantMessage.ToolUse):
                pending_tool_calls[msg.content.tool_use_id] = msg
                continue

            if isinstance(msg, ToolMessage) and msg.tool_use_id in pending_tool_calls:
                grouped_tool_use.append(pending_tool_calls.pop(msg.tool_use_id))
                grouped_tool_use.append(msg)
                continue

            grouped_tool_use.append(msg)

        grouped_tool_use.extend(pending_tool_calls.values())
        return grouped_tool_use

    def __repr__(self):
        return f"{self.name}({self.model})"
