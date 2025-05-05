import uuid
from typing import AsyncIterable, Type

from pydantic import BaseModel, TypeAdapter
from google import genai
from google.genai import types

from liteagent import Tool
from liteagent.internal import register_provider
from liteagent.message import Message, AssistantMessage
from liteagent.provider import Provider


class Google(Provider):
    name: str = "gemini"

    def __init__(self, client: genai.Client, model: str = "gemini-2.0-flash-exp", **kwargs):
        self.client = client
        self.model = model
        self.args = kwargs

    async def completion(
        self,
        messages: list[Message],
        tools: list[Tool] = None,
        respond_as: Type[BaseModel] = None,
    ) -> AsyncIterable[Message]:
        prompt = ""
        for message in messages:
            prompt += f"{message.role.capitalize()}: {await message.content_as_string()}\n"

        tool_definitions = [self._tool_def(tool) for tool in tools] if tools else None

        response_format = None
        if respond_as:
            response_format = TypeAdapter(respond_as).json_schema()

        config = {}
        if response_format:
            config["response_mime_type"] = "application/json"
            config["response_schema"] = response_format
        if tool_definitions:
            config["tools"] = [types.Tool(function_declarations=tool_definitions)]

        stream = await self.client.aio.models.generate_content_stream(
            model=self.model,
            contents=prompt,
            config=config,
            **self.args
        )

        cache = {}
        
        async for chunk in stream:
            messages = self._from_google(chunk, cache, respond_as)
            for message in messages:
                yield message
    
    def _from_google(self, chunk, cache: dict, respond_as: Type[BaseModel] = None) -> list[Message]:
        """Convert Google API response chunk to liteagent message format"""
        messages = []
        
        # Handle tool calls
        if hasattr(chunk, "function_calls") and chunk.function_calls:
            # Check if we need to emit a final text complete message
            acc = cache.pop("last_assistant_message", None)
            if acc:
                messages.append(AssistantMessage(content=AssistantMessage.TextComplete(
                    accumulated=acc['accumulated'],
                    stream_id=acc['stream_id']
                )))
            
            # Clear any JSON accumulation
            cache.pop("json_accumulator", None)
            
            # Process all function calls
            for call in chunk.function_calls:
                tool_id = str(call.tool_use_id or uuid.uuid4())
                
                # Create tool use message
                messages.append(AssistantMessage(
                    content=AssistantMessage.ToolUse(
                        tool_use_id=tool_id,
                        name=call.name,
                        arguments=call.args,
                    )
                ))
            
            return messages
        
        # Handle JSON schema responses
        if respond_as and hasattr(chunk, "text") and chunk.text:
            json_acc = cache.get("json_accumulator", "")
            json_acc += chunk.text
            cache["json_accumulator"] = json_acc
            
            try:
                parsed_content = respond_as.model_validate_json(json_acc)
                # Clear any text accumulation and JSON accumulation
                cache.pop("last_assistant_message", None)
                cache.pop("json_accumulator", None)
                messages.append(AssistantMessage(content=parsed_content))
                return messages
            except Exception:
                # Continue accumulating
                pass
        
        # Handle text responses
        if hasattr(chunk, "text") and chunk.text:
            acc = cache.get("last_assistant_message", None)

            if not acc:
                acc = {
                    "accumulated": "",
                    "stream_id": f'{uuid.uuid4()}'
                }
                cache["last_assistant_message"] = acc

            acc['accumulated'] = acc['accumulated'] + chunk.text

            messages.append(AssistantMessage(content=AssistantMessage.TextChunk(
                value=chunk.text,
                accumulated=acc['accumulated'],
                stream_id=acc['stream_id']
            )))
        
        # Handle the end of the response
        if hasattr(chunk, "done") and chunk.done:
            # Check if we need to send a TextComplete for text content
            acc = cache.pop("last_assistant_message", None)
            if acc:
                messages.append(AssistantMessage(content=AssistantMessage.TextComplete(
                    accumulated=acc['accumulated'],
                    stream_id=acc['stream_id']
                )))
            
            # Clear JSON accumulation as well
            cache.pop("json_accumulator", None)
        
        return messages

    def _tool_def(self, tool: Tool) -> types.FunctionDeclaration:
        return types.FunctionDeclaration(
            name=tool.name,
            parameters=self._recursive_purge_dict_key(tool.input.model_json_schema(), 'title'),
            description=tool.description,
        )

    def _recursive_purge_dict_key(self, d: dict[str, any], k: str) -> None:
        if isinstance(d, dict):
            for key in list(d.keys()):
                if key == k and "type" in d.keys():
                    del d[key]
                else:
                    self._recursive_purge_dict_key(d[key], k)

    def __repr__(self):
        return f"Google({self.model})"


@register_provider
def google(
    client: genai.Client = None,
    model: str = "gemini-2.0-flash"
) -> Provider:
    return Google(client or genai.Client(), model)
