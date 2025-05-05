import json
import os
import uuid
from functools import partial
from typing import AsyncIterable, Type, Any, Optional

import azure.ai.inference.models as azure
from azure.ai.inference.aio import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential

from liteagent import Tool
from liteagent.internal.cleanup import register_provider
from liteagent.message import ToolMessage, Message, UserMessage, AssistantMessage, SystemMessage
from liteagent.provider import Provider


class AzureAI(Provider):
    name: str
    args: dict = {}

    def __init__(
        self,
        name: str = "AzureAI",
        client: Optional[ChatCompletionsClient] = None,
        model: str = "gpt-4.1-mini",
        base_url: str = "https://models.inference.ai.azure.com",
        api_key: str = None,
        **kwargs
    ):
        self.name = name
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
    ) -> AsyncIterable[Message]:
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

        cache = {}
        
        async for response_chunk in completion_stream:
            messages = self._from_azure(response_chunk, cache, respond_as)
            for message in messages:
                yield message
                
    def _from_azure(self, response_chunk, cache: dict, respond_as: Type = None) -> list[Message]:
        """Convert Azure API response chunk to liteagent message format"""
        messages = []
        
        if not response_chunk.choices:
            return messages
            
        choice = response_chunk.choices[0]
        
        # Handle text content
        if choice.delta.content:
            if respond_as is None:
                # Normal text response
                acc = cache.get("last_assistant_message", None)
    
                if not acc:
                    acc = {
                        "accumulated": "",
                        "stream_id": f'{uuid.uuid4()}'
                    }
                    cache["last_assistant_message"] = acc
    
                acc['accumulated'] = acc['accumulated'] + choice.delta.content
    
                messages.append(AssistantMessage(content=AssistantMessage.TextChunk(
                    value=choice.delta.content,
                    accumulated=acc['accumulated'],
                    stream_id=acc['stream_id']
                )))
            else:
                # JSON schema response
                json_acc = cache.get("json_accumulator", "")
                json_acc += choice.delta.content
                cache["json_accumulator"] = json_acc
                
                try:
                    parsed_response = json.loads(json_acc)
                    # Clear accumulations
                    cache.pop("json_accumulator", None)
                    cache.pop("last_assistant_message", None)
                    
                    messages.append(AssistantMessage(content=respond_as(**parsed_response)))
                except json.JSONDecodeError:
                    # Continue accumulating
                    pass
                
        # Handle tool calls
        elif choice.delta.tool_calls:
            tool_call = choice.delta.tool_calls[0]
            tool_id = tool_call.tool_use_id or f'{uuid.uuid4()}'
            
            # Handle tool call name
            if tool_call.function.name and tool_call.function.name.strip():
                tool_key = f"tool-{tool_id}"
                cache[tool_key] = {
                    "name": tool_call.function.name,
                    "arguments": cache.get(tool_key, {}).get("arguments", "")
                }
            
            # Handle accumulating arguments
            if tool_call.function.accumulated_arguments:
                tool_key = f"tool-{tool_id}"
                
                # Make sure we have an entry for this tool
                if tool_key not in cache:
                    cache[tool_key] = {
                        "name": "unknown", # Will be set properly when name comes in
                        "arguments": ""
                    }
                
                # Update accumulated arguments
                tool_acc = cache[tool_key]
                tool_acc["arguments"] = tool_call.function.accumulated_arguments
                
                # Send a ToolUseChunk for the incremental update
                messages.append(AssistantMessage(content=AssistantMessage.ToolUseChunk(
                    tool_use_id=tool_id,
                    name=tool_acc["name"],
                    accumulated_arguments=tool_acc["arguments"]
                )))
                
                # Try to parse as complete JSON to see if we're done
                try:
                    args = json.loads(tool_acc["arguments"])
                    # If we get here, JSON parsing succeeded, so arguments are complete
                    
                    # Remove from cache and send complete tool use
                    cache.pop(tool_key, None)
                    
                    messages.append(AssistantMessage(content=AssistantMessage.ToolUse(
                        tool_use_id=tool_id,
                        name=tool_acc["name"],
                        arguments=args
                    )))
                except json.JSONDecodeError:
                    # Arguments aren't complete JSON yet, keep accumulating
                    pass
        
        # Handle finish events
        if choice.finish_reason:
            # Finalize any text in progress
            acc = cache.pop("last_assistant_message", None)
            if acc:
                messages.append(AssistantMessage(content=AssistantMessage.TextComplete(
                    accumulated=acc['accumulated'],
                    stream_id=acc['stream_id']
                )))
                
            # Finalize any JSON responses
            json_acc = cache.pop("json_accumulator", None)
            if json_acc and respond_as:
                try:
                    parsed_response = json.loads(json_acc)
                    messages.append(AssistantMessage(content=respond_as(**parsed_response)))
                except:
                    # Failed to parse final JSON
                    pass
                
            # Finalize any tools in progress
            for key in list(cache.keys()):
                if key.startswith("tool-"):
                    tool_acc = cache.pop(key)
                    tool_id = key.replace("tool-", "")
                    
                    try:
                        # Try to parse as JSON
                        args = json.loads(tool_acc["arguments"])
                    except:
                        # Use as string if not valid JSON
                        args = tool_acc["arguments"]
                        
                    messages.append(AssistantMessage(
                        content=AssistantMessage.ToolUse(
                            tool_use_id=tool_id,
                            name=tool_acc["name"],
                            arguments=args
                        )
                    ))
                
        return messages

    async def _map_message_to_azure(self, message: Message):
        match message:
            case UserMessage(content=content):
                return azure.UserMessage(
                    content=self._convert_content(content)
                )

            case AssistantMessage(content=ToolRequest(id=id, name=name, arguments=arguments)):
                return azure.AssistantMessage(
                    tool_calls=[azure.ChatCompletionsToolCall(
                        id=id,
                        function=azure.FunctionCall(
                            name=name,
                            arguments=self._serialize_arguments(arguments)
                        ),
                    )]
                )

            case AssistantMessage() as message:
                return azure.AssistantMessage(
                    content=await message.content_as_string()
                )

            case ToolMessage(tool_use_id=id) as message:
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

    def __repr__(self):
        return f"{self.name}({self.model})"


@register_provider
def azureai(
    model: str = 'gpt-4.1-mini',
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


github = partial(azureai, api_key=os.getenv('GITHUB_TOKEN'))
