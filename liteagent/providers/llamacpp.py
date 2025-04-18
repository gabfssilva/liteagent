import asyncio
import json
from abc import ABC
from typing import AsyncIterator, Type

from llama_cpp import Llama
from pydantic import BaseModel, TypeAdapter

from liteagent.internal import register_provider
from liteagent.tool import Tool
from liteagent.provider import Provider
from liteagent.message import Message, UserMessage, AssistantMessage, ToolRequest, ToolMessage

class LlamaCpp(Provider, ABC):
    llm: Llama

    def __init__(self, llm: Llama):
        self.llm = llm

    async def completion(
        self,
        messages: list[Message],
        tools: list[Tool] = None,
        respond_as: Type[BaseModel] = None,
    ) -> AsyncIterator[Message]:
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
                        arguments = arguments.model_dump()

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

        tool_definitions = list(map(lambda tool: tool.definition, tools)) if tools and len(tools) > 0 else None
        parsed_messages = list(map(map_message, messages))

        response_format = None if respond_as is None else {
            "type": "json_object",
            "schema": TypeAdapter(respond_as).json_schema()
        }

        # print(tool_definitions)

        response = self.llm.create_chat_completion(
            messages=parsed_messages,
            tools=tool_definitions,
            response_format=response_format,
            max_tokens=8192,
            stream=True
        )

        expected_output: str = ""

        for chunk in response:
            # print(chunk)

            if 'choices' not in chunk:
                continue

            for choice in chunk['choices']:
                if 'delta' not in choice:
                    continue

                if 'content' not in choice['delta']:
                    continue

                if not respond_as:
                    # print(choice['delta']['content'], end="", flush=True)
                    yield AssistantMessage(
                        content=choice['delta']['content']
                    )
                else:
                    expected_output = expected_output + choice['delta']['content']

                continue

        if respond_as:
            yield AssistantMessage(
                content=respond_as.model_validate_json(expected_output)
            )
