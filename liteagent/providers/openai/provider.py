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
from liteagent.internal.atomic_string import AtomicString


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

        try:
            async with self.client.beta.chat.completions.stream(
                model=self.model,
                messages=oai_messages,
                tools=tool_definitions,
                response_format=respond_as or NOT_GIVEN,
                **self.args
            ) as stream:
                async for event in stream:
                    message = await self._from_oai(event, cache)
                    if message:
                        yield message
        finally:
            for key, value in list(cache.items()):
                if isinstance(value, AtomicString) and not value.is_complete:
                    await value.complete()

    @staticmethod
    async def _from_oai(event: ChatCompletionStreamEvent, cache: dict) -> Message | None:
        match event:
            case ChunkEvent(
                chunk=ChatCompletionChunk(
                    choices=[
                        Choice(delta=ChoiceDelta(tool_calls=None, content=str(content)))
                    ]
                )
            ) if content != "":
                content_stream: AtomicString | None = cache.get("assistant_stream", None)

                if not content_stream:
                    content_stream = AtomicString(content)
                    cache["assistant_stream"] = content_stream

                    return AssistantMessage(content=AssistantMessage.TextStream(
                        stream_id=f'{uuid.uuid4()}',
                        content=content_stream
                    ))
                else:
                    await content_stream.append(content)
                    return None

            case ContentDoneEvent():
                for key in list(cache.keys()):
                    tool_stream = cache.pop(key)
                    await tool_stream.complete()

                return None

            case FunctionToolCallArgumentsDeltaEvent(
                name=name,
                index=index,
                arguments=arguments,
            ):
                content_stream: AtomicString | None = cache.pop("assistant_stream", None)

                if content_stream:
                    await content_stream.complete()

                tool_stream: AtomicString | None = cache.get(f"tool_stream-{name}-{index}", None)

                if not tool_stream:
                    tool_stream = AtomicString(arguments)

                    cache[f"tool_stream-{name}-{index}"] = tool_stream

                    return AssistantMessage(content=AssistantMessage.ToolUseStream(
                        tool_use_id=f'{uuid.uuid4()}',
                        name=name,
                        arguments=tool_stream
                    ))
                else:
                    await tool_stream.set(arguments)
                    return None

            case FunctionToolCallArgumentsDoneEvent(
                name=name,
                index=index,
                arguments=arguments,
            ):
                content_stream: AtomicString | None = cache.pop("assistant_stream", None)

                if content_stream:
                    await content_stream.complete()

                tool_stream: AtomicString | None = cache.pop(f"tool_stream-{name}-{index}", None)

                if tool_stream:
                    await tool_stream.set(arguments)
                    await tool_stream.complete()
                    return None
                else:
                    atomic_string = AtomicString(arguments, True)
                    return AssistantMessage(content=AssistantMessage.ToolUseStream(
                        tool_use_id=f'{uuid.uuid4()}',
                        name=name,
                        arguments=atomic_string
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

            case AssistantMessage(content=AssistantMessage.ToolUseStream() as tool_stream):
                return ChatCompletionAssistantMessageParam(
                    role='assistant',
                    tool_calls=[
                        ChatCompletionMessageToolCallParam(
                            id=tool_stream.tool_use_id,
                            type='function',
                            function={
                                "name": tool_stream.name,
                                "arguments": await tool_stream.await_complete_arguments()
                            }
                        )
                    ]
                )

            case AssistantMessage(content=AssistantMessage.TextStream() as text_stream):
                return ChatCompletionAssistantMessageParam(
                    role='assistant',
                    content=await text_stream.await_complete()
                )

            case _:
                raise Exception(f"Unknown message: {message}")

    @staticmethod
    def _group_tool_uses(self, messages: list[Message]) -> list[Message]:
        grouped_tool_use = []
        pending_tool_calls = {}

        for i, msg in enumerate(messages):
            if isinstance(msg, AssistantMessage) and isinstance(msg.content, AssistantMessage.ToolUseStream):
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
