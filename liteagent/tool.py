import asyncio
import inspect
import typing

from dataclasses import dataclass
from functools import partial
from typing import Type, Callable, Awaitable, Protocol, runtime_checkable

from pydantic import BaseModel, JsonValue


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
