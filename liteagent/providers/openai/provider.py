import asyncio
import json
import uuid
from typing import AsyncIterable, Type, AsyncIterable

from openai import AsyncOpenAI, NOT_GIVEN
from openai.lib.streaming.chat import FunctionToolCallArgumentsDoneEvent, ContentDoneEvent, ChunkEvent
from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import ChoiceDelta, Choice
from pydantic import BaseModel

from liteagent import Tool
from liteagent.internal.cleanup import register_provider
from liteagent.internal.memoized import MemoizedAsyncIterable
from liteagent.logger import log
from liteagent.message import ToolMessage, ToolRequest, Message, UserMessage, AssistantMessage, ImageURL, ImageBase64, \
    MessageContent
from liteagent.provider import Provider


class OpenAICompatible(Provider):
    name: str = "openai"
    args: dict = {}

    def __init__(self, client: AsyncOpenAI, model: str = 'gpt-4o-mini', **kwargs):
        self.client = client
        self.model = model
        self.args = kwargs

        provider_logger = log.bind(provider=self.name)
        provider_logger.info("provider_initialized",
                             model=model,
                             base_url=getattr(client, "base_url", "default"),
                             args=list(kwargs.keys()))

    async def completion(
        self,
        messages: list[Message],
        tools: list[Tool],
        respond_as: Type,
    ) -> AsyncIterable[Message]:
        provider_logger = log.bind(provider=self.name, model=self.model)
        provider_logger.info("completion_started",
                             message_count=len(messages),
                             tool_count=len(tools),
                             respond_as=getattr(respond_as, "__name__", str(respond_as)))

        start_time = asyncio.get_event_loop().time()

        tool_definitions = list(map(lambda tool: tool.definition, tools)) if len(tools) > 0 else NOT_GIVEN
        provider_logger.debug("preparing_tool_definitions",
                              has_tools=tool_definitions is not NOT_GIVEN)

        provider_logger.debug("mapping_messages")
        parsed_messages = [await self.map_message(message) for message in messages]
        provider_logger.debug("messages_mapped", count=len(parsed_messages))

        try:
            provider_logger.debug("opening_completion_stream")
            async with self.client.beta.chat.completions.stream(
                model=self.model,
                messages=parsed_messages,
                tools=tool_definitions,
                response_format=respond_as or NOT_GIVEN,
                **self.args
            ) as stream:
                provider_logger.debug("stream_opened")
                message_count = 0

                async for event in await self._as_messages(stream):
                    message_count += 1
                    provider_logger.debug("yielding_message",
                                          role=event.role,
                                          message_number=message_count,
                                          content_type=type(event.content).__name__)
                    yield event

                elapsed = asyncio.get_event_loop().time() - start_time
                provider_logger.info("completion_finished",
                                     elapsed_seconds=round(elapsed, 2),
                                     message_count=message_count)

        except Exception as e:
            elapsed = asyncio.get_event_loop().time() - start_time
            provider_logger.error("completion_failed",
                                  error=str(e),
                                  error_type=type(e).__name__,
                                  elapsed_seconds=round(elapsed, 2))

    @staticmethod
    async def map_message(message: Message) -> dict:
        message_logger = log.bind(provider="openai", method="map_message")
        message_logger.debug("mapping_message", role=message.role, content_type=type(message.content).__name__)
        match message:
            case UserMessage(content=content):
                def map_content(item: MessageContent) -> list[dict]:
                    match item:
                        case ImageURL(url=url):
                            return [{"type": "image_url", "image_url": {"url": url}}]
                        case ImageBase64(base64=base64_str):
                            return [{"type": "image_base64", "image_base64": base64_str}]
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
                    "tool_calls": [{
                        "id": id,
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": arguments.model_dump_json(),
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
                            "arguments": json.dumps(arguments),
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

            case ToolMessage(id=id) as message:
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

    @staticmethod
    async def _as_messages(stream) -> AsyncIterable[Message]:
        stream_logger = log.bind(provider="openai", method="_as_messages")
        stream_logger.debug("creating_message_stream")

        message_stream: MemoizedAsyncIterable[Message] = MemoizedAsyncIterable[Message]()
        assistant_stream: MemoizedAsyncIterable | None = None
        event_count = 0
        content_events = 0
        tool_events = 0

        async def consume():
            nonlocal message_stream, assistant_stream, event_count, content_events, tool_events

            stream_logger.debug("stream_consume_started")

            try:
                async for event in stream:
                    event_count += 1

                    match event:
                        case ChunkEvent(
                            chunk=ChatCompletionChunk(
                                choices=[Choice(delta=ChoiceDelta(tool_calls=None, content=str(content)))]
                            )
                        ) if content != "":
                            content_events += 1

                            if not assistant_stream:
                                stream_logger.debug("creating_assistant_stream")
                                assistant_stream = MemoizedAsyncIterable[str]()
                                await assistant_stream.emit(content)
                                stream_logger.debug("emitting_first_assistant_message")
                                await message_stream.emit(AssistantMessage(content=assistant_stream))
                            else:
                                stream_logger.debug("emitting_content_chunk", chunk_size=len(content))
                                await assistant_stream.emit(content)

                        case ContentDoneEvent(parsed=parsed) if parsed is not None:
                            stream_logger.debug("content_done_event_received", parsed_type=type(parsed).__name__)
                            await message_stream.emit(AssistantMessage(content=parsed))

                        case FunctionToolCallArgumentsDoneEvent(
                            type="tool_calls.function.arguments.done",
                            name=name,
                            index=index,
                            arguments=arguments,
                            parsed_arguments=parsed_arguments,
                        ):
                            tool_events += 1

                            tool_id = f'{uuid.uuid4()}'

                            stream_logger.info("tool_call_received",
                                               tool=name,
                                               tool_id=f'{tool_id}',
                                               has_parsed_args=parsed_arguments is not None)

                            await message_stream.emit(AssistantMessage(
                                content=ToolRequest(
                                    name=name,
                                    id=f'{tool_id}',
                                    arguments=dict(parsed_arguments) or arguments
                                )
                            ))

                        case _:
                            stream_logger.debug("unhandled_event_type", event_type=type(event).__name__)

                stream_logger.debug("stream_events_processed",
                                    total_events=event_count,
                                    content_events=content_events,
                                    tool_events=tool_events)

                if assistant_stream:
                    stream_logger.debug("closing_assistant_stream")
                    await assistant_stream.close()

                stream_logger.debug("closing_message_stream")
                await message_stream.close()

            except Exception as e:
                stream_logger.error("stream_processing_error",
                                    error=str(e),
                                    error_type=type(e).__name__)
                raise

        asyncio.create_task(consume())
        stream_logger.debug("stream_task_created")

        return message_stream


@register_provider
def openai_compatible(
    model: str,
    client: AsyncOpenAI = None,
    base_url: str = None,
    api_key: str = None,
    **kwargs
) -> Provider:
    factory_logger = log.bind(provider="openai", function="openai_compatible")

    factory_logger.info("creating_provider",
                        model=model,
                        has_client=client is not None,
                        has_base_url=base_url is not None,
                        has_api_key=api_key is not None,
                        kwargs=list(kwargs.keys()))

    if not client:
        factory_logger.debug("creating_client",
                             base_url=base_url or "default",
                             max_retries=5)

    provider = OpenAICompatible(
        client=client or AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=5
        ),
        model=model,
        **kwargs
    )

    factory_logger.debug("provider_created")
    return provider
