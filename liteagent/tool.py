import asyncio
import inspect
import re
from abc import ABC
from dataclasses import dataclass
from functools import partial
from inspect import Signature
from typing import List, AsyncIterator
from typing import Type, Callable, Awaitable, Protocol, runtime_checkable

from pydantic import BaseModel, JsonValue, create_model
from pydantic.fields import FieldInfo, Field

from liteagent.logger import log

Out = str | dict | BaseModel

Handler = Callable[..., Awaitable[Out | AsyncIterator[Out]]]


@dataclass
class Tool:
    name: str
    description: str
    input: Type[BaseModel]
    handler: Handler
    eager: bool = False
    emoji: str = '🔧'

    def _prepare(self, schema):
        """Recursively modifies schema to enforce 'strict': True and 'additionalProperties': False."""
        if isinstance(schema, dict):
            if schema.get("type") == "object":
                schema["strict"] = True
                schema["additionalProperties"] = False

            if "properties" in schema:
                for key, sub_schema in schema["properties"].items():
                    schema["properties"][key] = self._prepare(sub_schema)

            if "items" in schema:
                schema["items"] = self._prepare(schema["items"])

            if "$defs" in schema:
                for key, sub_schema in schema["$defs"].items():
                    schema["$defs"][key] = self._prepare(sub_schema)

        return schema

    def _make_all_fields_required(self, schema):
        """Recursively makes all fields required in the schema."""
        if not isinstance(schema, dict):
            return

        if "properties" in schema:
            schema["required"] = list(schema["properties"].keys())

            for property_schema in schema["properties"].values():
                self._make_all_fields_required(property_schema)

        if "items" in schema:
            self._make_all_fields_required(schema["items"])

        if "$defs" in schema:
            for def_schema in schema["$defs"].values():
                self._make_all_fields_required(def_schema)

    @property
    def input_schema(self):
        schema = self._prepare(self.input.model_json_schema())
        self._remove_defaults(schema)
        self._make_all_fields_required(schema)
        return schema

    @property
    def definition(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "strict": True,
                "parameters": self.input_schema,
            }
        }

    def _remove_defaults(self, schema):
        """Recursively removes default values from the schema."""
        if not isinstance(schema, dict):
            return

        if "default" in schema:
            del schema["default"]

        if "properties" in schema:
            for property_schema in schema["properties"].values():
                self._remove_defaults(property_schema)

        if "items" in schema:
            self._remove_defaults(schema["items"])

        if "$defs" in schema:
            for def_schema in schema["$defs"].values():
                self._remove_defaults(def_schema)

    async def _unsafe_call(self, **kwargs):
        tool_logger = log.bind(tool=self.name)
        tool_logger.debug("validating_input")

        try:
            input_data = self.input(**kwargs)
            tool_logger.debug("input_validation_successful")
        except Exception as e:
            tool_logger.error("input_validation_failed", error=str(e))
            raise

        def shallow_dump(self) -> dict:
            keys = self.model_dump().keys()
            get_attr = partial(getattr, self)
            return {key: get_attr(key) for key in keys}

        dump = shallow_dump(input_data)
        tool_logger.debug("input_processed", fields=list(dump.keys()))

        is_coroutine = inspect.iscoroutinefunction(self.handler)
        is_method = inspect.ismethod(self.handler)
        tool_logger.debug("handler_analysis", is_coroutine=is_coroutine, is_method=is_method)

        try:
            if is_coroutine and is_method:
                tool_logger.debug("executing_async_method")
                return await self.handler(self, **dump)
            elif is_coroutine:
                tool_logger.debug("executing_async_function")
                return await self.handler(**dump)
            elif is_method:
                tool_logger.debug("executing_sync_method_in_thread")
                return await asyncio.to_thread(self.handler, self, **dump)
            else:
                tool_logger.debug("executing_sync_function_in_thread")
                return await asyncio.to_thread(self.handler, **dump)
        except Exception as e:
            tool_logger.error("handler_execution_failed", error=str(e))
            raise

    async def __call__(self, **kwargs):
        from liteagent.message import ExecutionError

        tool_logger = log.bind(tool=self.name)
        tool_logger.info("tool_called", args=str(kwargs))

        try:
            tool_logger.debug("executing_tool")
            result = await self._unsafe_call(**kwargs)

            match result:
                case BaseModel():
                    tool_logger.debug("converting_basemodel_to_dict")
                    result = result.model_dump()

            tool_logger.info("tool_execution_successful", result_type=type(result).__name__)
            return result or "function finished successfully"
        except ImportError as e:
            tool_logger.error("import_error", module=e.name, msg=e.msg)
            return ExecutionError(
                exception='ImportError',
                error=e.msg,
                should_retry='no',
                should_tell_user=True
            )
        except Exception as e:
            tool_logger.error("tool_execution_error",
                              error_type=type(e).__name__,
                              error=str(e),
                              traceback=True)
            return ExecutionError(
                exception=e.__class__.__name__,
                error=f"The function called returned an error. Evaluate if you need to retry: {e}",
                should_retry='maybe',
                should_tell_user=True
            )


class Tools(ABC):
    def tools(self):
        for _, tool in inspect.getmembers(self.__class__, predicate=lambda m: self.predicate(m)):
            tool.handler = partial(tool.handler, self)
            tool.name = f"{self.base_name()}__{tool.name}"
            yield tool

    @staticmethod
    def predicate(member):
        return isinstance(member, Tool)

    def base_name(self) -> str:
        return re.sub(r'(?<!^)(?=[A-Z])', '_', self.__class__.__name__).lower()


ToolDef = Tool | List[Tool] | Tools | Callable[[...], Awaitable[str | dict | BaseModel]] | Awaitable['ToolDef']


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

    if description is None:
        description = f"Tool {name}"

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
