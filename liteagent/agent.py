import asyncio
import itertools
from inspect import Signature
from typing import Callable, List, AsyncIterator, Type, Literal, overload

from pydantic import BaseModel

from liteagent.provider import Provider
from .logger import log
from .message import Message, UserMessage, AssistantMessage, ToolRequest, ToolMessage, SystemMessage, MessageContent, \
    ExecutionError
from .prompts import TOOL_AGENT_PROMPT
from .tool import Tool, ToolDef, Tools

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
    tools: List[Tool | Callable] = []
    team: List['Agent'] = []
    intercept: AsyncInterceptor = None,
    audit: List[Callable[['Agent', Message], None]] = []
    respond_as: Type[Out | Wrapped[Out]] = None
    signature: Signature = None
    user_prompt_template: str = None
    _as_dispatcher: Tool = None

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

    def stateful(self):
        from . import session

        return session(self)

    @property
    def __signature__(self):
        return self.signature

    def execution_count(
        self,
        messages: list[Message],
        tool: str
    ) -> int:
        tool_requests = filter(lambda m: m.role == "assistant" and isinstance(m.content, ToolRequest), messages)
        tool_request_size = len(list(filter(lambda m: m.content.name == tool, tool_requests)))

        tool_responses = filter(lambda m: m.role == "tool" and not isinstance(m.content, ExecutionError), messages)
        tool_response_size = len(list(filter(lambda m: m.name == tool, tool_responses)))

        return tool_request_size - tool_response_size

    def _as_tool(self) -> Tool:
        if not self._as_dispatcher:
            from .agent_dispatch import AgentDispatcher

            self._as_dispatcher = AgentDispatcher(self)

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
    async def __call__(
        self,
        *content: MessageContent | Message,
        stream: Literal[False] = False,
        **kwargs
    ) -> Out:
        ...

    @overload
    async def __call__(
        self,
        *content: MessageContent | Message,
        stream: Literal[True],
        **kwargs
    ) -> AsyncIterator[Message]:
        ...

    async def __call__(
        self,
        *content: MessageContent | Message,
        stream: bool = False,
        **kwargs,
    ) -> Out | AsyncIterator[Message]:
        agent_logger = log.bind(agent=self.name)
        agent_logger.info("agent_called", stream=stream)

        user_messages = self._build_user_messages(*content, **kwargs)
        agent_logger.debug("user_messages_built", messages_count=len(user_messages))

        stream_messages = self._intercepted_call(user_messages)

        if stream:
            agent_logger.debug("returning_stream_messages")
            return stream_messages

        agent_logger.debug("processing_stream_to_output")
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
        agent_logger = log.bind(agent=self.name)
        agent_logger.debug("calling_provider", messages_count=len(messages), tools_count=len(self._all_tools))

        response = self.provider.completion(
            messages=messages,
            tools=self._all_tools,
            respond_as=self._respond_as()
        )

        received = []
        answers = []

        async def promise(value):
            return value

        async for message in response:
            agent_logger.debug("received_message", role=message.role, message_type=type(message.content).__name__)
            yield message

            match message:
                case AssistantMessage(content=ToolRequest(
                    id=tool_id,
                    name=name,
                    arguments=arguments
                )):
                    execution_count = self.execution_count(messages, name)
                    agent_logger.info("tool_requested", tool=name, tool_id=tool_id, execution_count=execution_count)

                    if execution_count > 3:
                        agent_logger.error("tool_execution_limit_exceeded", tool=name)
                        raise Exception('could not finish the execution')

                    async def tool_msg(tool_id, name, arguments):
                        agent_logger.debug("running_tool", tool=name, tool_id=tool_id)
                        result = await self._run_tool(ToolRequest(
                            id=tool_id,
                            name=name,
                            arguments=arguments
                        ))
                        agent_logger.debug("tool_execution_complete", tool=name, tool_id=tool_id,
                                           result_type=type(result).__name__)
                        return ToolMessage(
                            id=tool_id,
                            content=result,
                            name=name,
                        )

                    answers.append(promise(message))
                    answers.append(tool_msg(tool_id, name, arguments))
                case _:
                    if not self.respond_as or (type(message.content) == self.respond_as):
                        agent_logger.debug("valid_response_received", content_type=type(message.content).__name__)
                        received.append(message)

        if len(answers) > 0:
            agent_logger.debug("processing_tool_responses", count=len(answers) // 2)
            answers_list = await asyncio.gather(*answers)

            for answer in answers_list:
                if answer.role == "tool":
                    agent_logger.debug("yielding_tool_response", tool=answer.name)
                    yield answer

            agent_logger.debug("recursive_call", messages_count=len(messages + received + answers_list))
            async for response in self._call(messages + received + answers_list):
                yield response

    async def _run_tool(self, tool_request: ToolRequest):
        agent_logger = log.bind(agent=self.name)
        agent_logger.debug("run_tool_called", tool=tool_request.name)

        chosen_tool = self._tools.get(tool_request.name, None)

        if not chosen_tool:
            agent_logger.error("tool_not_found", requested_tool=tool_request.name, available_tools=self._tool_names)
            raise Exception(f'tool with name {tool_request.name} not found')

        args = dict() if len(chosen_tool.input.__pydantic_fields__) == 0 else tool_request.arguments
        agent_logger.debug("tool_execution_started", tool=tool_request.name, args=str(args))

        try:
            result = await chosen_tool(**args)
            agent_logger.debug("tool_execution_successful", tool=tool_request.name)
            return result
        except Exception as e:
            agent_logger.error("tool_execution_failed", tool=tool_request.name, error=str(e),
                               error_type=type(e).__name__)
            raise

    async def _intercepted_call(self, messages: List[Message]) -> AsyncIterator[Message]:
        agent_logger = log.bind(agent=self.name)
        agent_logger.debug("intercepted_call_started")

        async def inner() -> AsyncIterator[Message]:
            agent_logger.debug("preparing_eager_tools")
            eagerly_invoked = await self._eagerly_invoked_tools()
            agent_logger.debug("eager_tools_executed", count=len(eagerly_invoked) // 2)

            prompt = self._system_prompt()

            message_list = [
                SystemMessage(content=prompt),
                *messages,
                *eagerly_invoked,
            ]

            agent_logger.debug("message_list_prepared",
                               system_count=1,
                               system_message=prompt,
                               user_count=len(messages),
                               eager_count=len(eagerly_invoked))

            for m in message_list:
                agent_logger.debug("yielding_message", role=m.role)
                yield m

            agent_logger.debug("starting_call")
            async for m in self._call(message_list):
                yield m

        agent_logger.debug("starting_intercept")
        async for m in self._intercept(inner()):
            yield m

    async def _stream_to_out(self, stream: AsyncIterator[Message]) -> Out:
        agent_logger = log.bind(agent=self.name)
        agent_logger.debug("stream_to_out_started",
                           respond_as=getattr(self.respond_as, "__name__", str(self.respond_as)))

        if self.respond_as == AsyncIterator[Message]:
            agent_logger.debug("returning_stream_directly")
            return stream

        if self.respond_as == List[Message]:
            agent_logger.debug("collecting_stream_to_list")
            result = [m async for m in stream]
            agent_logger.debug("stream_collected", message_count=len(result))
            return result

        if self.respond_as == str or not self.respond_as:
            agent_logger.debug("collecting_stream_to_string")

            collected = []

            async for message in stream:
                agent_logger.debug("collecting_message", role=message.role, content_type=type(message.content).__name__)
                collected.append(await message.acontent())
                agent_logger.debug("message_collected", role=message.role, content_type=type(message.content).__name__)

            content = collected[-1]

            agent_logger.debug("string_collected", length=len(content))
            return content

        agent_logger.debug("collecting_stream_to_model")
        response: Out | Wrapped[Out] = None

        async for message in stream:
            if type(message.content) == self.respond_as:
                agent_logger.debug("model_response_found", content_type=type(message.content).__name__)
                response = message.content

        match response:
            case Wrapped():
                agent_logger.debug("unwrapping_response")
                return response.value
            case _:
                agent_logger.debug("returning_response", found=response is not None)
                return response

    def __await__(self) -> Out:
        pass

    async def _eagerly_invoked_tools(self) -> List[Message]:
        agent_logger = log.bind(agent=self.name)
        agent_logger.debug("finding_eager_tools")

        eager_tools = list(filter(lambda t: t.eager, self._all_tools))
        agent_logger.debug("eager_tools_found", count=len(eager_tools))

        result = []

        for tool in eager_tools:
            agent_logger.info("invoking_eager_tool", tool=tool.name)

            result.append(AssistantMessage(
                content=ToolRequest(
                    id='0',
                    name=tool.name,
                    arguments={},
                    origin='local',
                ))
            )

            try:
                tool_result = await tool()
                agent_logger.debug("eager_tool_success", tool=tool.name, result_type=type(tool_result).__name__)

                result.append(ToolMessage(
                    id='0',
                    name=tool.name,
                    content=tool_result,
                ))
            except Exception as e:
                agent_logger.error("eager_tool_failed", tool=tool.name, error=str(e), error_type=type(e).__name__)
                raise

        agent_logger.debug("eager_tools_complete", message_count=len(result))
        return result

    @property
    def __name__(self) -> str:
        return self.name
