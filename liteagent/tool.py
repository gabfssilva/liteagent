import asyncio
import inspect
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import partial
from typing import List, AsyncIterable, Any, Coroutine, Literal, override
from typing import Type, Callable, Awaitable
from typing import TYPE_CHECKING

from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo, Field

from .codec import JsonLike

if TYPE_CHECKING:
    from .agent import Agent
    from . import ToolMessage

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
        try:
            input_data = self.input(**kwargs)
        except Exception as e:
            raise

        def shallow_dump(self) -> dict:
            keys = self.model_dump().keys()
            get_attr = partial(getattr, self)
            return {key: get_attr(key) for key in keys}

        dump = shallow_dump(input_data)

        self.is_coroutine = inspect.iscoroutinefunction(self.handler)

        if isinstance(self, AgentDispatcherTool):
            dump['loop_id'] = kwargs.pop("loop_id", None)

        try:
            if self.is_coroutine:
                return await self.handler(**dump)
            else:
                result = await asyncio.to_thread(self.handler, **dump)

                if inspect.isgenerator(result):
                    return self._gen_to_async(result)

                return result
        except Exception as e:
            raise

    @property
    def type(self) -> Literal['agent', 'tool']:
        return 'tool'

    async def __call__(self, **kwargs) -> JsonLike:
        try:
            result = await self._unsafe_call(**kwargs)

            match result:
                case BaseModel():
                    result = result.model_dump()

            return result or "function finished successfully"
        except ImportError as e:
            from . import ToolMessage

            return ToolMessage.ExecutionError(
                exception='ImportError',
                message=e.msg,
                should_retry='no',
            )
        except Exception as e:
            from . import ToolMessage

            return ToolMessage.ExecutionError(
                exception=e.__class__.__name__,
                message=f"The function called returned an error. Evaluate if you need to retry: {e}",
                should_retry='maybe',
            )

    @staticmethod
    async def _gen_to_async(generator):
        while True:
            try:
                item = await asyncio.to_thread(next, generator)
                yield item
            except StopIteration:
                break

    def __repr__(self):
        return f"{self.emoji} {self.name}"


class Tools(ToolDef, ABC):
    def tools(self) -> List[Tool]:
        tools = []

        for _, tool_def in inspect.getmembers(self.__class__, predicate=lambda m: self.predicate(m)):
            for tool in tool_def.tools():
                tools.append(Tool(
                    name=f"{self.base_name()}__{tool.name}",
                    description=tool.description,
                    input=tool.input,
                    handler=partial(tool.handler, self),
                    eager=tool.eager,
                    emoji=tool.emoji,
                ))

        return tools

    @staticmethod
    def predicate(member):
        return isinstance(member, ToolDef)

    def base_name(self) -> str:
        return re.sub(r'(?<!^)(?=[A-Z])', '_', self.__class__.__name__).lower()


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

    def tools(self) -> List[Tool]:
        return [
            self.tool
        ]


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

    @override
    def type(self) -> Literal['agent', 'tool']:
        return 'agent'

    async def _dispatch(self, *args, **kwargs):
        args = filter(lambda arg: arg is not self, args)

        last_assistant_message = None

        loop_id = kwargs.pop('loop_id', None)

        async for message in await self.agent(*list(args), stream=True, loop_id=loop_id, **kwargs):
            if message.complete() and message.role == 'assistant':
                last_assistant_message = message

        return last_assistant_message

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
