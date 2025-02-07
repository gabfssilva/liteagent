import asyncio

import itertools
from inspect import Signature
from typing import Callable, List, Iterator, AsyncIterator, Type, Literal

from pydantic import Field, BaseModel, create_model

from liteagent import Message, UserMessage, AssistantMessage, ToolRequest, ToolMessage, SystemMessage, Provider, \
    TOOL_AGENT_PROMPT, Tools
from .tool import Tool, ToolDef

AsyncInterceptor = Callable[['Agent', AsyncIterator[Message]], AsyncIterator[Message]]

ResponseMode = Literal["stream", "list", "last"] | Callable[[Message], bool]

AgentResponse = BaseModel | Message | List[Message] | AsyncIterator[Message]


class Agent:
    name: str
    provider: Provider
    description: str = None
    system_message: str = None
    initial_messages: List[Message] = []
    tools: List[Tool | Callable] = []
    team: List['Agent'] = []
    intercept: AsyncInterceptor = None,
    audit: List[Callable[['Agent', Message], None]] = []
    respond_as: Type = None
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
        respond_as: Type = None,
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

        self.respond_as_wrapped = False

        if respond_as and isinstance(respond_as, type) and issubclass(respond_as, BaseModel):
            self.respond_as = respond_as
        elif respond_as:
            self.respond_as_wrapped = True
            self.respond_as = create_model(f'{type(respond_as).__qualname__}', **{
                "value": (respond_as, Field(...))
            })

        self.system_message = system_message
        self.initial_messages = initial_messages or []

    def execution_count(
        self,
        messages: list[Message],
        tool: str
    ) -> int:
        tool_requests = filter(lambda m: m.role == "assistant" and isinstance(m.content, ToolRequest), messages)
        return len(list(filter(lambda m: m.content.name == tool, tool_requests)))

    def _as_tool(self) -> Tool:
        """Expose the agent as a tool."""

        prompt_field = Field(
            default=...,
            description="The input prompt for the agent. Consider adding all the context needed for this specific agent."
        )

        tool_name = f'{self.name.replace(" ", "_").lower()}_redirection'

        from .decorators import tool

        @tool
        async def agent_function(
            prompt: str = prompt_field
        ) -> str:
            f""" Redirect to the {self.name} agent """

            messages = []

            async for message in await self(prompt, respond='stream'):
                if message.role == "assistant" and isinstance(message.content, str):
                    messages.append(message.content)

            return "".join(messages)

        af = agent_function
        af.name = tool_name
        return af

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

    async def _audit(self, iterator: AsyncIterator[Message]) -> AsyncIterator[Message]:
        async for message in iterator:
            for audit in self.audit:
                audit(self, message)

            yield message

    async def _intercept(self, iterator: AsyncIterator[Message]) -> AsyncIterator[Message]:
        if not self.intercept:
            async for message in iterator:
                yield message
        else:
            async for message in self.intercept(self, iterator):
                yield message

    async def _call(self, messages: List[Message]) -> AsyncIterator[Message]:
        response = self.provider.completion(
            messages=messages,
            tools=self._all_tools,
            respond_as=self.respond_as
        )

        received = []
        answers = []

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

                    chosen_tool_output = await self._run_tool(ToolRequest(
                        id=tool_id,
                        name=name,
                        arguments=arguments
                    ))

                    tool_message = ToolMessage(
                        id=tool_id,
                        content=chosen_tool_output,
                        name=name,
                    )

                    yield tool_message

                    answers.append(AssistantMessage(content=ToolRequest(
                        id=tool_id,
                        name=name,
                        arguments=arguments
                    )))

                    answers.append(tool_message)
                case _:
                    if not self.respond_as or (isinstance(message.content, self.respond_as)):
                        received.append(message)

        if len(answers) > 0:
            async for answer in self._call(messages + received + answers):
                yield answer

    async def _run_tool(self, tool_request: ToolRequest):
        chosen_tool = self._tools.get(tool_request.name, None)

        if not chosen_tool:
            raise Exception(f'tool with name {tool_request.name} not found')

        args = dict() if len(chosen_tool.input.model_fields) == 0 else tool_request.arguments

        return await chosen_tool(**args)

    async def run(self, prompt: str):
        results = []

        async for message in self(prompt):
            results.append(message)

        return results[:-1]

    def run_sync(self, prompt: str):
        return asyncio.run(self.run(prompt))

    def async_iterable_to_sync_iterable(self, iterator: AsyncIterator) -> Iterator:
        with asyncio.Runner() as runner:
            try:
                while True:
                    result = runner.run(anext(iterator))
                    yield result
            except StopAsyncIteration as e:
                pass

    def sync(self, prompt: str) -> Iterator[Message]:
        return self.async_iterable_to_sync_iterable(self(prompt))

    async def _intercepted_call(self, prompt: str) -> AsyncIterator[Message]:
        async def inner() -> AsyncIterator[Message]:
            eagerly_invoked = await self._eagerly_invoked_tools()

            messages = [
                SystemMessage(content=self._system_prompt()),
                UserMessage(content=prompt),
                *eagerly_invoked,
            ]

            for m in messages:
                yield m

            async for m in self._call(messages):
                yield m

        async for m in self._intercept(inner()):
            yield m

    async def __call__(
        self,
        *args,
        respond: ResponseMode = "last",
        **kwargs
    ) -> AgentResponse:
        if (args or kwargs) and not (len(args) == 1 and isinstance(args[0], str) and not kwargs):
            if not self.signature or not self.user_prompt_template:
                raise ValueError("Agent missing signature or prompt template information.")
            bound = self.signature.bind(*args, **kwargs)
            bound.apply_defaults()
            prompt = self.user_prompt_template.format(**bound.arguments)
        elif args:
            prompt = args[0]
        elif self.user_prompt_template:
            prompt = self.user_prompt_template
        else:
            raise ValueError("No prompt provided to the agent.")

        match respond:
            case 'list':
                messages = []
                async for message in self._intercepted_call(prompt):
                    messages.append(message)
                return messages
            case 'last':
                last = None
                async for message in self._intercepted_call(prompt):
                    last = message
                if self.respond_as and self.respond_as_wrapped:
                    return last.content.value
                elif self.respond_as:
                    return last.content
                return last
            case 'stream':
                return self._intercepted_call(prompt)
            case _ if callable(respond):
                return filter(respond, self._intercepted_call(prompt))

    def __await__(self) -> Message | List[Message] | AsyncIterator[Message]:
        pass

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
