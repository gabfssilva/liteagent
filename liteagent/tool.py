import asyncio
import inspect
import typing
from dataclasses import dataclass
from functools import partial
from typing import Type, Callable, Awaitable

from pydantic import BaseModel


@dataclass
class Tool:
    name: str
    description: str
    input: Type[BaseModel]
    handler: Callable[[...], Awaitable[str | dict | BaseModel]]

    @property
    def definition(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "strict": True,
                "parameters": {
                    **self.input.model_json_schema(),
                    "additionalProperties": False
                },
            }
        }

    async def _unsafe_call(self, **kwargs):
        input_data = self.input(**kwargs)
        dump = input_data.model_dump()

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
