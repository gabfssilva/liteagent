import json
import os
from functools import partial
from typing import AsyncIterator, Type, Any, Optional

import azure.ai.inference.models as azure
from azure.ai.inference.aio import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential

from liteagent import Tool
from liteagent.internal.cleanup import register_provider
from liteagent.message import ToolMessage, ToolRequest, Message, UserMessage, AssistantMessage, SystemMessage
from liteagent.provider import Provider


class AzureAI(Provider):
    name: str = "azure_ai"
    args: dict = {}

    def __init__(
        self,
        client: Optional[ChatCompletionsClient] = None,
        model: str = "gpt-4o-mini",
        base_url: str = "https://models.inference.ai.azure.com",
        api_key: str = None,
        **kwargs
    ):
        self.client = client or ChatCompletionsClient(
            endpoint=base_url,
            credential=AzureKeyCredential(api_key),
            api_version="2024-08-01-preview"
        )
        self.model = model
        self.args = kwargs

    async def completion(
        self,
        messages: list[Message],
        tools: list[Tool],
        respond_as: Type,
    ) -> AsyncIterator[Message]:
        # Convert tools to Azure format
        azure_tools = None

        if tools:
            azure_tools = [self._tool_to_function(tool) for tool in tools]

        response_format = None

        if respond_as:
            response_format = azure.JsonSchemaFormat(
                name=respond_as.__name__,
                schema=respond_as.model_json_schema()
            )

        # Stream response
        mapped_messages = [await self._map_message_to_azure(msg) for msg in messages]
        completion_stream = await self.client.complete(
            model=self.model,
            messages=mapped_messages,
            tools=azure_tools,
            response_format=response_format,
            stream=True,
            **self.args
        )

        on_going_function = {"name": None, "arguments": ""}
        on_going_response = "" if respond_as else None

        async for response_chunk in completion_stream:
            if response_chunk.choices:
                choice = response_chunk.choices[0]
                if choice.delta.content and on_going_response is None:
                    yield AssistantMessage(content=choice.delta.content)
                elif choice.delta.content:
                    on_going_response = on_going_response + choice.delta.content

                    try:
                        parsed_response = json.loads(on_going_response)
                    except json.JSONDecodeError:
                        continue

                    yield AssistantMessage(content=respond_as(**parsed_response))
                elif choice.delta.tool_calls:
                    tool_call = choice.delta.tool_calls[0]

                    if tool_call.function.name and '' != tool_call.function.name.strip():
                        on_going_function = {
                            "name": tool_call.function.name,
                            "arguments": ""
                        }

                    if tool_call.function.arguments:
                        on_going_function['arguments'] = on_going_function['arguments'] + tool_call.function.arguments

                        try:
                            args = json.loads(on_going_function['arguments'])
                        except json.JSONDecodeError:
                            continue

                        yield AssistantMessage(
                            content=ToolRequest(
                                name=on_going_function['name'],
                                id=tool_call.id or "0",
                                arguments=args
                            )
                        )

                        on_going_function = {
                            "name": None,
                            "arguments": ""
                        }

    async def _map_message_to_azure(self, message: Message):
        match message:
            case UserMessage(content=content):
                return azure.UserMessage(
                    content=self._convert_content(content)
                )

            case AssistantMessage(content=ToolRequest(id=id, name=name, arguments=arguments)):
                call = azure.ChatCompletionsToolCall(
                    id=id,
                    function=azure.FunctionCall(
                        name=name,
                        arguments=self._serialize_arguments(arguments)
                    ),
                )

                return azure.AssistantMessage(
                    tool_calls=[call]
                )

            case AssistantMessage(content=content):
                return azure.AssistantMessage(
                    content=self._convert_content(content)
                )

            case ToolMessage(id=id, content=content) as message:
                return azure.ToolMessage(
                    tool_call_id=id,
                    content=await message.content_as_string()
                )

            case SystemMessage(content=content):
                return azure.SystemMessage(
                    content=self._convert_content(content)
                )

            case _:
                raise ValueError(f"Invalid message type: {type(message)}")

    @staticmethod
    def _convert_content(content: Any) -> str:
        if isinstance(content, str):
            return content
        elif hasattr(content, "model_dump_json"):
            return content.model_dump_json()
        elif isinstance(content, dict) or isinstance(content, list):
            return json.dumps(content)
        else:
            return str(content)

    @staticmethod
    def _serialize_arguments(arguments: Any) -> str:
        if hasattr(arguments, "model_dump_json"):
            return arguments.model_dump_json()
        elif isinstance(arguments, dict):
            return json.dumps(arguments)
        elif isinstance(arguments, str):
            return arguments
        else:
            return json.dumps(str(arguments))

    @staticmethod
    def _tool_to_function(tool: Tool) -> azure.ChatCompletionsToolDefinition:
        return azure.ChatCompletionsToolDefinition(
            function=azure.FunctionDefinition(
                name=tool.name,
                description=tool.description,
                parameters=tool.input_schema
            )
        )

    async def destroy(self):
        if self.client:
            await self.client.close()


@register_provider
def azureai(
    model: str = 'gpt-4o-mini',
    base_url: str = 'https://models.inference.ai.azure.com',
    api_key: str = None,
    **kwargs
) -> Provider:
    return AzureAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        **kwargs
    )


# Shorthand for GitHub Copilot
github = partial(azureai, api_key=os.getenv('GITHUB_TOKEN'))
