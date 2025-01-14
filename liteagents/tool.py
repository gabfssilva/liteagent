import asyncio
import inspect

from typing import List, Tuple, Type, Any, Callable, Awaitable, Coroutine

from pydantic import BaseModel, Field, create_model
from pydantic.fields import FieldInfo


class Tool:
    name: str
    description: str
    input_fields: List[Tuple[str, Any, Any]]
    function: Callable[..., Awaitable[str | dict | list | BaseModel]]

    def __init__(
        self,
        name: str,
        description: str,
        input_fields: List[Tuple[str, Any, Any]],
        function: Callable[..., Awaitable[str | dict | list | BaseModel]]
    ):
        self.name = name
        self.description = description
        self.input_fields = input_fields
        self.function = function

    @property
    def input_model(self) -> Type[BaseModel]:
        field_definitions = {}

        for field_name, field_type, field_default in self.input_fields:
            if isinstance(field_default, FieldInfo):
                field_definitions[field_name] = (field_type, field_default)
            else:
                field_definitions[field_name] = (field_type, Field(default=field_default))

        return create_model(f"{self.name.capitalize()}Input", **field_definitions)

    @property
    def json_schema(self):
        return self.input_model.model_json_schema()

    @property
    def definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.json_schema,
            }
        }

    async def __call__(self, **kwargs):
        input_data = self.input_model(**kwargs)

        if inspect.iscoroutinefunction(self.function):
            return await self.function(**input_data.model_dump())
        else:
            return await asyncio.to_thread(self.function, **input_data.model_dump())


def tool(function):
    sig = inspect.signature(function)
    input_fields = [
        (
            name,
            param.annotation,
            param.default if param.default != param.empty else Field(...)
        )
        for name, param in sig.parameters.items()
    ]

    return Tool(
        name=function.__name__,
        description=function.__doc__,
        input_fields=input_fields,
        function=function
    )
