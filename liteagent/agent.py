import asyncio
import itertools
import json
import uuid
from inspect import Signature
from typing import Callable, List, AsyncIterable, Type, Literal, overload, Optional

from pydantic import BaseModel

from liteagent.provider import Provider
from .message import Message, UserMessage, Image, AssistantMessage, ToolMessage, SystemMessage
from .internal.atomic_string import AtomicString
from .prompts import TOOL_AGENT_PROMPT
from .tool import Tool, ToolDef
from .bus import EventBus, create_bus
from .events import (
    SystemMessageEvent,
    UserMessageEvent,
    AssistantMessageEvent,
    ToolMessageEvent,
    AgentCallEvent
)

ResponseMode = Literal["stream", "list", "last"] | Callable[[Message], bool]
AgentResponse = BaseModel | Message | List[Message] | AsyncIterable[Message]


class Wrapped[T](BaseModel):
    value: T


class Agent[Out]:
    name: str
    provider: Provider
    description: str = None
    system_message: str = None
    tools: List[Tool | Callable] = []
    team: List['Agent'] = []
    respond_as: Type[Out | Wrapped[Out]] = None
    signature: Signature = None
    user_prompt_template: str = None
    _as_dispatcher: ToolDef = None
    bus: EventBus = None

    def __init__(
        self,
        name: str,
        provider: Provider,
        description: str = None,
        system_message: str = None,
        tools: List[ToolDef | Callable] = None,
        team: List['Agent'] = None,
        respond_as: Type[Out | Wrapped[Out]] = None,
        signature: Signature = None,
        user_prompt_template: str = None,
        bus: Optional[EventBus] = None
    ):
        self.name = name
        self.provider = provider
        self.description = description
        self.tools = list(itertools.chain.from_iterable(map(lambda tool: tool.tools(), tools))) if tools else []
        self.team = team or []
        self._all_tools = self.tools + list(
            itertools.chain.from_iterable(map(lambda agent: agent.as_tool().tools(), self.team)))
        self._tool_by_name = {t.name: t for t in self._all_tools}
        self.signature = signature
        self.user_prompt_template = user_prompt_template

        # Use provided bus or create a new one if None
        self.bus = bus if bus is not None else create_bus()

        if respond_as and (isinstance(respond_as, type) and issubclass(respond_as, BaseModel) or respond_as == str):
            self.respond_as = respond_as
            self.respond_as_wrapped = False
        elif respond_as:
            self.respond_as_wrapped = True
            self.respond_as = Wrapped[respond_as]
            self.respond_as.__name__ = "Out"
        else:
            self.respond_as = AsyncIterable[Message]
            self.respond_as_wrapped = False

        self.system_message = system_message

    def __repr__(self):
        return f"🤖{self.name}"

    async def _emit_event(self, message: Message):
        loop_id = message.loop_id

        match message:
            case SystemMessage() as message:
                await self.bus.emit(SystemMessageEvent(
                    agent=self,
                    message=message,
                    loop_id=loop_id
                ))
            case UserMessage() as message:
                await self.bus.emit(UserMessageEvent(
                    agent=self,
                    message=message,
                    loop_id=loop_id
                ))
            case AssistantMessage() as message:
                await self.bus.emit(AssistantMessageEvent(
                    agent=self,
                    message=message,
                    loop_id=loop_id
                ))
            case ToolMessage() as message:
                tool_name = message.tool_name
                tool = self.tool_by_name(tool_name)
                
                await self.bus.emit(ToolMessageEvent(
                    agent=self,
                    message=message,
                    tool=tool,
                    tool_use_id=message.tool_use_id,
                    loop_id=loop_id
                ))

    def stateful(self):
        from . import session

        return session(self)

    @property
    def __signature__(self):
        return self.signature

    def with_tool(self, definition: ToolDef):
        for tool in definition.tools():
            self.tools.append(tool)

        self._all_tools = self.tools + list(
            itertools.chain.from_iterable(map(lambda agent: agent.as_tool().tools(), self.team)))

        self._tool_by_name = {t.name: t for t in self._all_tools}

    def as_tool(self) -> ToolDef:
        if not self._as_dispatcher:
            from .tool import AgentDispatcherTool

            self._as_dispatcher = AgentDispatcherTool(agent=self)

        return self._as_dispatcher

    def _system_prompt(self) -> str:
        return (self.system_message or TOOL_AGENT_PROMPT).replace(
            "{{tools}}",
            ", ".join(self._tool_names)
        ).replace(
            "{{team}}",
            ", ".join(self._team_names)
        ).replace(
            "{{name}}",
            self.name
        ).replace(
            "{{description}}",
            self.description or "A helpful assistant"
        )

    @property
    def _tool_names(self) -> List[str]:
        return list(map(lambda t: t.name, self._all_tools))

    @property
    def _team_names(self) -> List[str]:
        return list(map(lambda t: t.name, self.team))

    def tool_by_name(self, name: str) -> Tool | None:
        return self._tool_by_name.get(name, None)

    def _build_user_messages(
        self,
        *content: str | Image | Message,
        **kwargs,
    ) -> List[Message]:
        if len(content) == 0 and kwargs and len(kwargs) > 0 and self.user_prompt_template:
            bound = self.signature.bind(**kwargs)
            bound.apply_defaults()
            content = [self.user_prompt_template.format(**bound.arguments)]

        if len(content) == 0 and kwargs and len(kwargs) > 0:
            content = list(kwargs.values())

        if len(content) == 0 and self.user_prompt_template:
            content = [self.user_prompt_template]

        if not content:
            raise ValueError("No content provided to the agent.")

        def to_msg(c: str | Image | Message) -> Message:
            return c if isinstance(c, Message) else UserMessage(content=c)

        return list(map(to_msg, content))

    @overload
    async def __call__(
        self,
        *content: str | Image | Message,
        stream: Literal[False] = False,
        loop_id: str | None = None,
        **kwargs
    ) -> Out:
        ...

    @overload
    async def __call__(
        self,
        *content: str | Image | Message,
        stream: Literal[True],
        loop_id: str | None = None,
        **kwargs
    ) -> AsyncIterable[Message]:
        ...

    async def __call__(
        self,
        *content: str | Image | Message,
        stream: bool = False,
        loop_id: str | None = None,
        **kwargs,
    ) -> Out | AsyncIterable[Message]:
        user_messages = self._build_user_messages(*content, **kwargs)
        stream_messages = self._call(user_messages, loop_id)

        if stream:
            return stream_messages

        return await self._stream_to_out(stream_messages)

    def _respond_as(self):
        if not self.respond_as or self.respond_as == str or self.respond_as == AsyncIterable[Message]:
            return None

        return self.respond_as

    async def _call(self, messages: List[Message], loop_id: str | None) -> AsyncIterable[Message]:
        if not loop_id:
            loop_id = str(uuid.uuid4())

        await self.bus.emit(AgentCallEvent(
            agent=self,
            messages=messages,
            loop_id=loop_id
        ))

        eagerly_invoked = await self._eagerly_invoked_tools(loop_id)
        prompt = self._system_prompt()

        system_message = SystemMessage(content=prompt)
        object.__setattr__(system_message, 'loop_id', loop_id)

        for message in messages:
            object.__setattr__(message, 'loop_id', loop_id)

        message_list = [
            system_message,
            *messages,
            *eagerly_invoked,
        ]

        for message in message_list:
            await self._emit_event(message)

        async for message in self._inner_call(message_list, loop_id):
            yield message

    async def _inner_call(self, messages: List[Message], loop_id: str) -> AsyncIterable[Message]:
        response = self.provider.completion(
            messages=messages,
            tools=self._all_tools,
            respond_as=self._respond_as()
        )

        pending_tools = []
        accumulated = []

        async for message in response:
            object.__setattr__(message, 'loop_id', loop_id)

            if message.complete():
                accumulated.append(message)

            match message:
                case AssistantMessage(content=AssistantMessage.ToolUseStream()) as message:
                    message.content.tool = self.tool_by_name(message.content.name)

                    await self._emit_event(message)
                    yield message

                    pending_tools.append(self._run_tool(message.content, loop_id))
                case _:
                    await self._emit_event(message)
                    yield message

        if len(pending_tools) > 0:
            tool_responses = await asyncio.gather(*pending_tools)

            for tool_response in tool_responses:
                yield tool_response

            all_messages = messages + accumulated + tool_responses

            async for response in self._inner_call(all_messages, loop_id):
                yield response

    async def _run_tool(self, tool_request: AssistantMessage.ToolUseStream, loop_id: str) -> ToolMessage:
        chosen_tool = self.tool_by_name(tool_request.name)

        if not chosen_tool:
            raise Exception(f'tool with name {tool_request.name} not found')

        args_json = await tool_request.get_arguments_as_json()
        args = dict() if len(chosen_tool.input.__pydantic_fields__) == 0 else args_json

        try:
            from . import AgentDispatcherTool

            if isinstance(chosen_tool, AgentDispatcherTool):
                tool_result = await chosen_tool(
                    loop_id=tool_request.tool_use_id,
                    **args
                )
            else:
                tool_result = await chosen_tool(**args)

            message = ToolMessage(
                tool_use_id=tool_request.tool_use_id,
                tool_name=tool_request.name,
                arguments=args,
                content=tool_result,
                loop_id=loop_id,
            )

            await self._emit_event(message)

            return message
        except Exception as e:
            raise

    async def _stream_to_out(self, stream: AsyncIterable[Message]) -> Out:
        if self.respond_as == AsyncIterable[Message]:
            return stream

        if self.respond_as == List[Message]:
            result = [m async for m in stream]
            return result

        if self.respond_as == str or not self.respond_as:
            collected = []

            async for message in stream:
                collected.append(message)

            content = collected[-1]

            return content

        response: Out | Wrapped[Out] = None

        async for message in stream:
            if type(message.content) == self.respond_as:
                response = message.content

        match response:
            case Wrapped():
                return response.value
            case _:
                return response

    def __await__(self) -> Out:
        pass

    async def _eagerly_invoked_tools(self, loop_id: str) -> List[Message]:
        eager_tools = list(filter(lambda t: t.eager, self._all_tools))

        result = []

        for tool in eager_tools:
            tool_id = uuid.uuid4()

            # Use ToolUseStream instead of ToolUse
            tool_stream = AssistantMessage.ToolUseStream(
                tool_use_id=f'{tool_id}',
                name=tool.name,
                arguments=AtomicString(json.dumps({}))
            )
            await tool_stream.complete()  # Mark it as complete immediately

            assistant_message = AssistantMessage(
                content=tool_stream
            )

            # Set loop_id on the assistant message
            object.__setattr__(assistant_message, 'loop_id', loop_id)

            await self._emit_event(assistant_message)

            result.append(assistant_message)

            try:
                tool_result = await tool()

                tool_message = ToolMessage(
                    tool_use_id=f'{tool_id}',
                    content=tool_result,
                    tool_name=tool.name,
                    arguments={}
                )

                # Set loop_id on the tool message
                object.__setattr__(tool_message, 'loop_id', loop_id)

                await self._emit_event(tool_message)

                result.append(tool_message)
            except Exception as e:
                raise

        return result

    @property
    def __name__(self) -> str:
        return self.name
