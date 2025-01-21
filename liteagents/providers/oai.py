import asyncio
import json
import os
from typing import AsyncIterator, Type

from openai.lib.streaming.chat import *
from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import ChoiceDelta, Choice

from liteagents import Tool
from liteagents.providers import Provider
from liteagents.message import ToolMessage, ToolRequest, Message, UserMessage, AssistantMessage, SystemMessage

from openai import OpenAI, AsyncOpenAI, BaseModel, NotGiven, NOT_GIVEN


class OpenAICompatible(Provider):
    name: str = "openai"

    def __init__(
        self,
        client: AsyncOpenAI,
        model: str = 'gpt-4o-mini',
        max_tokens: int = 4096,
        temperature: float = 0.7,
        top_p: float = 1,
        frequency_penalty: float = 0,
        presence_penalty: float = 0,
    ):
        self.client = client
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty

    async def completion(
        self,
        messages: list[Message],
        tools: list[Tool],
        respond_as: Type,
    ) -> AsyncIterator[Message]:
        # Prepare messages for OpenAI API
        def map_message(message: Message) -> dict:
            match message:
                case UserMessage(content=content):
                    return {
                        "role": "user",
                        "content": content,
                    }

                case AssistantMessage(content=str(content)):
                    return {
                        "role": "assistant",
                        "content": content,
                    }

                case AssistantMessage(content=ToolRequest(id=id, name=name, arguments=arguments)):
                    if isinstance(arguments, BaseModel):
                        arguments = arguments.model_dump_json()
                    elif isinstance(arguments, dict):
                        arguments = json.dumps(arguments)

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

                case ToolMessage(id=id, content=content):
                    if isinstance(content, BaseModel):
                        content = content.model_dump_json()
                    elif isinstance(content, dict):
                        content = json.dumps(content)
                    else:
                        content = f'{content}'

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

        tool_definitions = list(map(lambda tool: tool.pydantic_tool, tools)) if len(tools) > 0 else None
        parsed_messages = list(map(map_message, messages))

        async with self.client.beta.chat.completions.stream(
            model=self.model,
            messages=parsed_messages,
            tools=tool_definitions,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            frequency_penalty=self.frequency_penalty,
            presence_penalty=self.presence_penalty,
            response_format=respond_as or NOT_GIVEN,
        ) as stream:
            async for event in self._as_messages(stream):
                yield event

    @staticmethod
    async def _as_messages(stream) -> AsyncIterator[Message]:
        async for event in stream:
            match event:
                case ChunkEvent(
                    chunk=ChatCompletionChunk(
                        choices=[
                            Choice(delta=ChoiceDelta(tool_calls=None, content=str(content)))
                        ]
                    )
                ):
                    yield AssistantMessage(content=content)

                case ContentDoneEvent(parsed=parsed) if parsed is not None:
                    yield AssistantMessage(content=parsed)

                case FunctionToolCallArgumentsDoneEvent(
                    type="tool_calls.function.arguments.done",
                    name=name,
                    index=index,
                    arguments=arguments,
                    parsed_arguments=parsed_arguments,
                ):
                    yield AssistantMessage(
                        content=ToolRequest(
                            name=name,
                            id=f'{index}',
                            arguments=dict(parsed_arguments) or arguments
                        )
                    )

                case _:
                    # print(f"unexpected: {event}")
                    pass
