import asyncio
import inspect
from inspect import Signature

from typing import Dict, List, Tuple, Type, Any, Callable, Awaitable, Coroutine

from openai import pydantic_function_tool
from pydantic import BaseModel, Field, create_model, ValidationError
from pydantic.fields import FieldInfo


class Tool:
    name: str
    description: str
    signature: Signature
    input_fields: List[Tuple[str, Any, Any]]
    function: Callable[..., Awaitable[str | dict | list | BaseModel]]
    retries: int

    def __init__(
        self,
        name: str,
        description: str,
        input_fields: List[Tuple[str, Any, Any]],
        function: Callable[..., Awaitable[str | dict | list | BaseModel]],
        retries: int,
        signature: Signature
    ):
        self.name = name
        self.description = description
        self.input_fields = input_fields
        self.function = function
        self.retries = retries
        self.signature = signature

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
    def pydantic_tool(self):
        return pydantic_function_tool(
            self.input_model,
            name=self.name,
            description=self.description
        )

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

    async def _call_with_retry(self, count: int = 0, **kwargs):
        try:
            # Validate input model
            try:
                input_data = self.input_model(**kwargs)
            except ValidationError as ve:
                # input_data = self.input_model(**kwargs['input'])
                raise

            if 'input' in self.signature.parameters:
                dump = dict(input=input_data.input)
            else:
                dump = input_data.model_dump()

            if inspect.iscoroutinefunction(self.function):
                return await self.function(**dump)
            else:
                return await asyncio.to_thread(self.function, **dump)
        except Exception as e:
            print(f"Exception occurred: {type(e).__name__} - {str(e)}")

            if isinstance(e, KeyError):
                return f"""
                Exception occurred: {type(e).__name__} - {str(e)}
                Are you sure this variable is defined in the code?
                """
            #
            # if count < self.retries:
            #     print(f"Retrying... Attempt {count + 1}/{self.retries}")
            #     return await self._call_with_retry(count + 1, **kwargs)
            #
            # raise

    async def __call__(self, **kwargs):
        return await self._call_with_retry(count=0, **kwargs)


def tool(function, retries: int = 2):
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
        function=function,
        retries=retries,
        signature=sig
    )


Tools = Dict[str, Tool]
