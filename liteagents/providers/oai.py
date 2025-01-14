import json
import os
from typing import AsyncIterator

from liteagents import Tool
from liteagents.providers import Provider
from liteagents.message import ToolMessage, ToolRequest, Message, UserMessage, AssistantMessage, SystemMessage

from openai import OpenAI, AsyncOpenAI, BaseModel


class OpenAICompatible(Provider):
    name: str = "openai"

    def __init__(
        self,
        client: AsyncOpenAI = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")),
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
    ) -> AsyncIterator[Message]:
        # Prepare messages for OpenAI API
        def map_message(message: Message) -> dict:
            match message:
                case UserMessage(role='user', content=content):
                    return {
                        "role": "user",
                        "content": content,
                    }

                case AssistantMessage(role=role, content=str(content)):
                    return {
                        "role": "assistant",
                        "content": content,
                    }

                case AssistantMessage(role=role, content=ToolRequest(id=id, name=name, arguments=arguments)):
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

                case ToolMessage(role=role, id=id, content=BaseModel() as content):
                    return {
                        "tool_call_id": id,
                        "role": "tool",
                        "content": content.model_dump_json(),
                        "type": "function"
                    }

                case ToolMessage(role=role, id=id, content=str(content)):
                    return {
                        "tool_call_id": id,
                        "role": "tool",
                        "content": content,
                        "type": "function"
                    }

                case ToolMessage(role=role, id=id, content=content):
                    return {
                        "tool_call_id": id,
                        "role": "tool",
                        "content": json.dumps(content),
                        "type": "function"
                    }

                case Message(role=role, content=content):
                    return {
                        "role": role,
                        "content": content,
                    }

                # case dict() as raw:
                #     return raw

                case _:
                    raise ValueError(f"Invalid message type: {type(message)}")

        tool_definitions = list(map(lambda tool: tool.definition, tools)) if len(tools) > 0 else None
        parsed_messages = list(map(map_message, messages))

        # Initialize streaming response
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=parsed_messages,
            tools=tool_definitions,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            frequency_penalty=self.frequency_penalty,
            presence_penalty=self.presence_penalty,
            stream=True,  # Stream responses
        )

        current_tool_request = {
            "id": None,
            "name": None,
            "arguments": None,
        }

        async for chunk in response:
            for choice in chunk.choices:
                delta = choice.delta

                if delta.content and delta.content != "":
                    yield AssistantMessage(content=delta.content)

                if not delta.tool_calls:
                    continue

                for tool_call in delta.tool_calls:
                    if not current_tool_request["id"]:
                        current_tool_request["id"] = tool_call.id

                    if not current_tool_request["name"]:
                        current_tool_request["name"] = tool_call.function.name

                    if not current_tool_request["arguments"]:
                        current_tool_request["arguments"] = ""

                    if tool_call.function.arguments:
                        current_tool_request["arguments"] += tool_call.function.arguments

                        try:
                            arguments = json.loads(current_tool_request["arguments"])

                            yield AssistantMessage(
                                content=ToolRequest(
                                    name=current_tool_request["name"],
                                    id=current_tool_request["id"],
                                    arguments=arguments,
                                )
                            )

                            current_tool_request = {
                                "id": None,
                                "name": None,
                                "arguments": None,
                            }

                        except json.JSONDecodeError:
                            continue
