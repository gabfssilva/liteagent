from typing import AsyncIterator, Type

from pydantic import BaseModel, TypeAdapter

from liteagent import Tool
from liteagent.internal import register_provider
from liteagent.message import ToolRequest, Message, AssistantMessage
from liteagent.provider import Provider

from google import genai
from google.genai import types

class Gemini(Provider):
    name: str = "gemini"

    def __init__(self, client: genai.Client, model: str = "gemini-2.0-flash-exp", **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.model = model
        self.args = kwargs

    async def completion(
        self,
        messages: list[Message],
        tools: list[Tool] = None,
        respond_as: Type[BaseModel] = None,
    ) -> AsyncIterator[Message]:
        prompt = ""
        for message in messages:
            if message.role.lower() == "user":
                prompt += f"User: {message.content}\n"
            elif message.role.lower() == "assistant":
                prompt += f"Assistant: {message.content}\n"
            else:
                prompt += f"{message.role.capitalize()}: {message.content}\n"

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

        assistant_message = ""

        async for chunk in stream:
            if hasattr(chunk, "function_calls") and chunk.function_calls:
                for call in chunk.function_calls:
                    yield AssistantMessage(
                        content=ToolRequest(
                            id=str(call.id or "0"),
                            name=call.name,
                            arguments=call.args,
                        )
                    )

                    return


            if respond_as:
                assistant_message = assistant_message + chunk.text

                try:
                    parsed_content = respond_as.model_validate_json(assistant_message)
                    yield AssistantMessage(content=parsed_content)
                    return
                except Exception:
                    continue

            yield AssistantMessage(content=chunk.text)

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

@register_provider
def gemini(
    client: genai.Client = None,
    model: str = "gemini-2.0-flash"
) -> Provider: 
    return Gemini(client or genai.Client(), model)