import asyncio
import itertools
from inspect import Signature
from typing import Callable, List, AsyncIterator, Type, Literal, overload

from pydantic import  BaseModel

from .message import Message, UserMessage, AssistantMessage, ToolRequest, ToolMessage, SystemMessage, MessageContent
from .tool import Tool, ToolDef, parse_tool, Tools
from liteagent.provider import Provider
from .prompts import TOOL_AGENT_PROMPT

AsyncInterceptor = Callable[['Agent', AsyncIterator[Message]], AsyncIterator[Message]]

ResponseMode = Literal["stream", "list", "last"] | Callable[[Message], bool]

AgentResponse = BaseModel | Message | List[Message] | AsyncIterator[Message]


class Wrapped[T](BaseModel):
    value: T


class Agent[Out]:
    name: str
    provider: Provider
    description: str = None
    system_message: str = None
    initial_messages: List[Message] = []
    tools: List[Tool | Callable] = []
    team: List['Agent'] = []
    intercept: AsyncInterceptor = None,
    audit: List[Callable[['Agent', Message], None]] = []
    respond_as: Type[Out | Wrapped[Out]] = None
    signature: Signature = None
    user_prompt_template: str = None

    def __init__(
        self,
        name: str,
        provider: Provider,
        description: str = None,
        system_message: str = None,
        initial_messages: List[Message] = None,
        tools: List[ToolDef | Callable] = None,
        team: List['Agent'] = None,
        intercept: AsyncInterceptor = None,
        audit: List[Callable[['Agent', Message], None]] = None,
        respond_as: Type[Out | Wrapped[Out]] = None,
        signature: Signature = None,
        user_prompt_template: str = None
    ):
        self.name = name
        self.provider = provider
        self.description = description
        self.tools = list(itertools.chain.from_iterable(
            map(lambda tool: tool.tools() if isinstance(tool, Tools) else [tool], tools))) if tools else []
        self.team = team or []
        self.audit = audit or []
        self.intercept = intercept or None
        self.signature = signature
        self.user_prompt_template = user_prompt_template

        if respond_as and (isinstance(respond_as, type) and issubclass(respond_as, BaseModel) or respond_as == str):
            self.respond_as = respond_as
            self.respond_as_wrapped = False
        elif respond_as:
            self.respond_as_wrapped = True
            self.respond_as = Wrapped[respond_as]
            self.respond_as.__name__ = "Out"
        else:
            self.respond_as = AsyncIterator[Message]
            self.respond_as_wrapped = False

        self.system_message = system_message
        self.initial_messages = initial_messages or []

    @property
    def __signature__(self):
        return self.signature

    def execution_count(
        self,
        messages: list[Message],
        tool: str
    ) -> int:
        tool_requests = filter(lambda m: m.role == "assistant" and isinstance(m.content, ToolRequest), messages)
        return len(list(filter(lambda m: m.content.name == tool, tool_requests)))

    def _as_tool(self) -> Tool:
        """ convert the agent to a tool. """
        from .agent_dispatch import AgentDispatch
        return AgentDispatch(self)

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
    def _all_tools(self) -> List[Tool]:
        return self.tools + list(map(lambda a: a._as_tool(), self.team))

    @property
    def _tool_names(self) -> List[str]:
        return list(map(lambda t: t.name, self._all_tools))

    @property
    def _team_names(self) -> List[str]:
        return list(map(lambda t: t.name, self.team))

    @property
    def _tools(self) -> dict[str, Tool]:
        all_tools = self._all_tools
        return {t.name: t for t in all_tools}

    def tool_by_name(self, name: str) -> Tool | None:
        return self._tools.get(name, None)

    def _build_user_messages(
        self,
        *content: MessageContent | Message,
        **kwargs,
    ) -> List[Message]:
        if kwargs:
            if not self.signature or not self.user_prompt_template:
                raise ValueError("Agent missing signature or prompt template.")
            bound = self.signature.bind(**kwargs)
            bound.apply_defaults()
            content = [self.user_prompt_template.format(**bound.arguments)]
        elif not content and self.user_prompt_template:
            content = [self.user_prompt_template]
        elif not content:
            raise ValueError("No content provided to the agent.")

        def to_msg(c: MessageContent | Message) -> Message:
            return c if isinstance(c, Message) else UserMessage(content=c)

        return list(map(to_msg, content))

    @overload
    async def __call__(self, *content: MessageContent | Message, stream: Literal[False] = False, **kwargs) -> Out: ...
    @overload
    async def __call__(self, *content: MessageContent | Message, stream: Literal[True], **kwargs) -> AsyncIterator[Message]: ...

    async def __call__(
        self,
        *content: MessageContent | Message,
        stream: bool = False,
        **kwargs,
    ) -> Out | AsyncIterator[Message]:
        user_messages = self._build_user_messages(*content, **kwargs)
        stream_messages = self._intercepted_call(user_messages)

        if stream:
            return stream_messages

        return await self._stream_to_out(stream_messages)

    async def _intercept(self, iterator: AsyncIterator[Message]) -> AsyncIterator[Message]:
        if not self.intercept:
            async for message in iterator:
                yield message
        else:
            async for message in self.intercept(self, iterator):
                yield message

    def _respond_as(self):
        if not self.respond_as or self.respond_as == str or self.respond_as == AsyncIterator[Message]:
            return None

        return self.respond_as

    async def _call(self, messages: List[Message]) -> AsyncIterator[Message]:
        response = self.provider.completion(
            messages=messages,
            tools=self._all_tools,
            respond_as=self._respond_as()
        )

        received = []
        answers = []

        async def promise(value): return value

        async for message in response:
            yield message

            match message:
                case AssistantMessage(content=ToolRequest(
                    id=tool_id,
                    name=name,
                    arguments=arguments
                )):
                    if self.execution_count(messages, name) > 3:
                        raise Exception('could not finish the execution')

                    async def tool_msg(tool_id, name, arguments):
                        return ToolMessage(
                            id=tool_id,
                            content=await self._run_tool(ToolRequest(
                                id=tool_id,
                                name=name,
                                arguments=arguments
                            )),
                            name=name,
                        )

                    answers.append(promise(message))
                    answers.append(tool_msg(tool_id, name, arguments))
                case _:
                    if not self.respond_as or (type(message.content) == self.respond_as):
                        received.append(message)

        if len(answers) > 0:
            answers_list = await asyncio.gather(*answers)

            for answer in answers_list:
                if answer.role == "tool":
                    yield answer

            async for response in self._call(messages + received + answers_list):
                yield response

    async def _run_tool(self, tool_request: ToolRequest):
        chosen_tool = self._tools.get(tool_request.name, None)

        if not chosen_tool:
            raise Exception(f'tool with name {tool_request.name} not found')

        args = dict() if len(chosen_tool.input.model_fields) == 0 else tool_request.arguments
        
        return await chosen_tool(**args)

    async def _intercepted_call(self, messages: List[Message]) -> AsyncIterator[Message]:
        async def inner() -> AsyncIterator[Message]:
            eagerly_invoked = await self._eagerly_invoked_tools()

            message_list = [
                SystemMessage(content=self._system_prompt()),
                *messages,
                *eagerly_invoked,
            ]

            for m in message_list:
                yield m

            async for m in self._call(messages):
                yield m

        async for m in self._intercept(inner()):
            yield m

    async def _stream_to_out(self, stream: AsyncIterator[Message]) -> Out:
        if self.respond_as == AsyncIterator[Message]:
            return stream
        if self.respond_as == List[Message]:
            return [m async for m in stream]
        if self.respond_as == str or not self.respond_as:
            current = ''

            async for message in stream:
                if message.role == "assistant" and isinstance(message.content, str):
                    current = current + message.content
                else:
                    current = ''

            return current

        response: Out | Wrapped[Out] = None

        async for message in stream:
            if type(message.content) == self.respond_as:
                response = message.content

        match response:
            case Wrapped():
                return response.value
            case _:
                return response

    def __await__(self) -> Out: pass

    async def _eagerly_invoked_tools(self) -> List[Message]:
        eager = filter(lambda t: t.eager, self._all_tools)

        result = []

        for tool in eager:
            result.append(AssistantMessage(
                content=ToolRequest(
                    id='0',
                    name=tool.name,
                    arguments={},
                    origin='local',
                ))
            )

            result.append(ToolMessage(
                id='0',
                name=tool.name,
                content=await tool(),
            ))

        return result

    @property
    def __name__(self) -> str:
        return self.name
