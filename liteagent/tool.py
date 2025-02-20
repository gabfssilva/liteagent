import asyncio
import inspect
import typing

from dataclasses import dataclass
from functools import partial
from inspect import Signature
from typing import Type, Callable, Awaitable, Protocol, runtime_checkable

from pydantic import BaseModel, JsonValue, create_model
from pydantic.fields import FieldInfo, Field


@dataclass
class Tool:
    name: str
    description: str
    input: Type[BaseModel]
    handler: Callable[[...], Awaitable[str | dict | BaseModel]]
    eager: bool = False
    emoji: str = '🔧'

    def _prepare(self, schema):
        """Recursively modifies schema to enforce 'strict': True and 'additionalProperties': False."""
        if isinstance(schema, dict):
            if schema.get("type") == "object":
                schema["strict"] = True
                schema["additionalProperties"] = False
            
            # Recursively process nested properties
            if "properties" in schema:
                for key, sub_schema in schema["properties"].items():
                    schema["properties"][key] = self._prepare(sub_schema)
            
            # Handle 'items' if this is an array
            if "items" in schema:
                schema["items"] = self._prepare(schema["items"])
            
            # Handle `$defs` (reusable schemas)
            if "$defs" in schema:
                for key, sub_schema in schema["$defs"].items():
                    schema["$defs"][key] = self._prepare(sub_schema)

        return schema

    @property
    def definition(self):
        schema = self.input.model_json_schema()
        modified_schema = self._prepare(schema)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "strict": True,
                "parameters": modified_schema,
            }
        }
    
    async def _unsafe_call(self, **kwargs):
        input_data = self.input(**kwargs)

        def shallow_dump(self) -> dict:
            keys = self.model_dump().keys()
            get_attr = partial(getattr, self)
            return {key: get_attr(key) for key in keys}

        dump = shallow_dump(input_data)

        if inspect.iscoroutinefunction(self.handler):
            if inspect.ismethod(self.handler):
                return await self.handler(self, **dump)
            else:
                return await self.handler(**dump)
        else:
            if inspect.ismethod(self.handler):
                return await asyncio.to_thread(self.handler, self, **dump)
            else:
                return await asyncio.to_thread(self.handler, **dump)

    async def __call__(self, **kwargs):
        try:
            return await self._unsafe_call(**kwargs)
        except Exception as e:
            return f"The function called returned an error. Evaluate if you need to retry: {e}"


class Tools:
    def tools(self):
        for _, tool in inspect.getmembers(self.__class__, predicate=lambda m: self.predicate(m)):
            tool.handler = partial(tool.handler, self)
            yield tool

    @staticmethod
    def predicate(member):
        return isinstance(member, Tool)


ToolDef = Tool | typing.List[Tool] | Callable[[...], Awaitable[str | dict | BaseModel]]


@runtime_checkable
class ToolResponse(Protocol):
    def __tool_response__(self) -> JsonValue:
        pass

def parse_tool(
    function: Callable,
    name: str = None,
    signature: Signature | None = None,
    description: str | None = None,
    eager: bool = False,
    emoji: str = '🔧'
):
    if name is None:
        name = function.__name__

    if signature is None:
        signature = inspect.signature(function)

    if description is None:
        description = inspect.getdoc(function)

    input_fields = [
        (n,
         param.annotation,
         param.default if param.default != param.empty else Field(...))
        for n, param in signature.parameters.items() if n != 'self'
    ]

    field_definitions = {}

    for field_name, field_type, field_default in input_fields:
        if isinstance(field_default, FieldInfo):
            field_definitions[field_name] = (field_type, field_default)
        else:
            field_definitions[field_name] = (field_type, Field(default=field_default))

    return Tool(
        name=name,
        description=description.strip(),
        input=create_model(name.capitalize(), **field_definitions),
        handler=function,
        eager=eager,
        emoji=emoji
    )
