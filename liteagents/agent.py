import asyncio
import json

from typing import Callable, List, Iterator, AsyncIterator, Type, Literal, Union

from liteagents import Tool, TOOL_AGENT_PROMPT

from pydantic import BaseModel, Field, ValidationError

from liteagents.message import Message, UserMessage, AssistantMessage, ToolRequest, ToolMessage, SystemMessage
from liteagents.providers import Provider

import inspect

AsyncInterceptor = Callable[['Agent', AsyncIterator[Message]], AsyncIterator[Message]]

ResponseMode = Literal["stream", "list", "last"] | Callable[[Message], bool]


class Agent:
    name: str
    provider: Provider
    description: str = None
    system_message: str = None
    tools: List[Tool | Callable] = []
    team: List['Agent'] = []
    intercept: AsyncInterceptor = None,
    audit: List[Callable[['Agent', Message], None]] = []
    respond_as: Type = None

    def __init__(
        self,
        name: str,
        provider: Provider,
        description: str = None,
        system_message: str = None,
        tools: List[Tool | Callable] = None,
        team: List['Agent'] = None,
        intercept: AsyncInterceptor = None,
        audit: List[Callable[['Agent', Message], None]] = None,
        respond_as: Type = None
    ):
        self.name = name
        self.provider = provider
        self.description = description
        self.system_message = system_message
        self.tools = tools or []
        self.team = team or []
        self.audit = audit or []
        self.intercept = intercept or None
        self.respond_as = respond_as

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

        async def agent_function(
            prompt: str = prompt_field
        ) -> str:
            messages = []

            async for message in await self(prompt, respond='stream'):
                if message.role == "assistant" and isinstance(message.content, str):
                    messages.append(message.content)

            return "".join(messages)

        return Tool(
            name=f'{self.name.replace(" ", "_").lower()}_redirection',
            description=self.description or f"Redirect to the {self.name} agent",
            input_fields=[("prompt", str, Field(..., description="The input prompt for the agent."))],
            function=agent_function,
            retries=1,
            signature=inspect.signature(agent_function)
        )

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

                    args, chosen_tool_output = await self._run_tool(ToolRequest(
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
                        arguments=args.model_dump() if args else arguments
                    )))

                    answers.append(tool_message)
                case _:
                    received.append(message)

        if len(answers) > 0:
            async for answer in self._call(messages + received + answers):
                yield answer

    async def _run_tool(self, tool_request: ToolRequest):
        chosen_tool = self._tools.get(tool_request.name, None)

        if not chosen_tool:
            raise Exception(f'tool with name {tool_request.name} not found')

        # try:
        model = chosen_tool.input_model(**tool_request.arguments)
        return model, await chosen_tool(**tool_request.arguments)
        # except ValidationError as e:
        #     return None, f'{e}'

    def _convert_content(self, content) -> str:
        match content:
            case str():
                return content
            case dict():
                return json.dumps(content)
            case BaseModel():
                return content.model_dump_json()
            case list():
                return f"[{",".join(list(map(self._convert_content, content)))}]"
            case _:
                raise Exception(f"tool output must be str, dict, list or BaseModel, got {type(content)}")

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
            messages = [
                SystemMessage(content=self._system_prompt()),
                UserMessage(content=prompt)
            ]

            for m in messages:
                yield m

            async for m in self._call(messages):
                yield m

        async for m in self._intercept(inner()):
            yield m

    async def __call__(
        self,
        prompt: str,
        respond: ResponseMode = "last"
    ) -> Message | List[Message] | AsyncIterator[Message]:
        match respond:
            case 'list':
                all = []

                async for message in self._intercepted_call(prompt):
                    all.append(message)

                return all
            case 'last':
                last: Message | None = None

                async for message in self._intercepted_call(prompt):
                    last = message

                return last
            case 'stream':
                return self._intercepted_call(prompt)
            case callable:
                return filter(callable, self._intercepted_call(prompt))

    def __await__(self) -> Message | List[Message] | AsyncIterator[Message]:
        pass
