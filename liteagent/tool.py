import asyncio
import inspect
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import partial
from typing import List, AsyncIterable, Any, Coroutine, overload
from typing import Type, Callable, Awaitable, Protocol, runtime_checkable

from pydantic import BaseModel, JsonValue, create_model
from pydantic.fields import FieldInfo, Field

from liteagent.logger import log

Out = str | dict | BaseModel | Coroutine[Any, Any, 'Out']

Handler = Callable[..., Out | Awaitable[Out | AsyncIterable[Out]] | AsyncIterable[Out]]


class ToolDef(ABC):
    @abstractmethod
    def tools(self) -> List['Tool']:
        raise NotImplementedError


@dataclass(kw_only=True)
class Tool(ToolDef):
    name: str
    description: str
    input: Type[BaseModel]
    handler: Handler
    eager: bool = False
    emoji: str = '🔧'

    def tools(self) -> List['Tool']:
        return [self]

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
    def response_type(self):
        return inspect.signature(self.handler).return_annotation

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
                result = await asyncio.to_thread(self.handler, self, **dump)

                if inspect.isgenerator(result):
                    return self._gen_to_async(result)

                return result
            else:
                tool_logger.debug("executing_sync_function_in_thread")
                result = await asyncio.to_thread(self.handler, **dump)

                if inspect.isgenerator(result):
                    return self._gen_to_async(result)

                return result
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

    @staticmethod
    async def _gen_to_async(generator):
        while True:
            try:
                item = await asyncio.to_thread(next, generator)
                yield item
            except StopIteration:
                break

class Tools(ToolDef, ABC):
    def tools(self) -> List[Tool]:
        tools = []

        for _, tool_def in inspect.getmembers(self.__class__, predicate=lambda m: self.predicate(m)):
            for tool in tool_def.tools():
                tool.handler = partial(tool.handler, self)
                tool.name = f"{self.base_name()}__{tool.name}"
                tools.append(tool)

        return tools

    @staticmethod
    def predicate(member):
        return isinstance(member, ToolDef)

    def base_name(self) -> str:
        return re.sub(r'(?<!^)(?=[A-Z])', '_', self.__class__.__name__).lower()


@runtime_checkable
class ToolResponse(Protocol):
    def __tool_response__(self) -> JsonValue:
        pass


class FunctionToolDef(ToolDef):
    tool: Tool

    def __init__(self, function: Callable, name: str = None, description: str = None, eager: bool = False, emoji='🔧'):
        self.function = function
        self.name = name or function.__name__
        self.description = description or inspect.getdoc(function) or f"Tool {self.name}"
        self.eager = eager
        self.emoji = emoji

        signature = inspect.signature(self.function)

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

        self.tool = Tool(
            name=self.name,
            description=self.description,
            input=create_model(self.name.capitalize(), **field_definitions),
            handler=self.function,
            emoji=self.emoji,
            eager=self.eager
        )

    def tools(self) -> List[Tool]:  return [self.tool]


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .agent import Agent
    from . import Message


@dataclass(kw_only=True)
class AgentDispatcherTool(Tool):
    agent: 'Agent'

    name: str = field(init=False)
    description: str = field(init=False)
    input: Type[BaseModel] = field(init=False)
    handler: Handler = field(init=False)
    eager: bool = field(default=False, init=False)
    emoji: str = field(default='🤖', init=False)

    def __post_init__(self):
        self.name = f"{self.agent.name.replace(' ', '_').lower()}_redirection"
        self.description = f"Dispatch to the {self.agent.name} agent: {self.agent.description or ''}"
        self.input = self._create_input_model()
        self.handler = self._dispatch

    async def _dispatch(self, *args, **kwargs) -> AsyncIterable['Message']:
        args = filter(lambda arg: arg is not self, args)
        return await self.agent(*list(args), stream=True, **kwargs)

    def _create_input_model(self):
        if not self.agent.signature:
            return create_model(
                f"{self.agent.name.capitalize()}Input",
                query=(str, Field(..., description="Query to send to the agent"))
            )

        parameters = {}
        for name, param in self.agent.signature.parameters.items():
            annotation = param.annotation if param.annotation != inspect.Parameter.empty else Any
            default = param.default if param.default != inspect.Parameter.empty else ...
            parameters[name] = (annotation, Field(default=default))

        return create_model(
            f"{self.agent.name.capitalize()}Input",
            **parameters
        )


class ToolOut(Protocol):
    async def __json__(self) -> JsonValue: pass


@overload
async def to_json(value: ToolOut) -> JsonValue:
    return await value.__json__()


@overload
async def to_json[T: str | int | float | bool | None](value: T) -> JsonValue:
    return value


@overload
async def to_json(value: list) -> JsonValue:
    return [await to_json(value) for value in value]


class JsonConverter[I]:
    def __init__(self, value: I, converter: Callable[[I], Awaitable[JsonValue]]):
        self.value = value
        self.converter = converter

    async def __json__(self) -> JsonValue:
        return await self.converter(self.value)


class TypeConverter[I, O](ABC):
    @abstractmethod
    async def convert(self, value: I) -> O:
        pass


class BaseModelToJson(TypeConverter[BaseModel, JsonValue]):
    async def convert(self, value: BaseModel) -> JsonValue:
        return value.model_dump()


class SimpleValueToJson(TypeConverter[str | int | float | bool, JsonValue]):
    async def convert(self, value: str | int | float | bool) -> JsonValue:
        return value


class ListToJson(TypeConverter[list, JsonValue]):
    async def convert(self, value: list) -> JsonValue:
        return value


class DictToJson(TypeConverter[dict, JsonValue]):
    async def convert(self, value: dict) -> JsonValue:
        pass
