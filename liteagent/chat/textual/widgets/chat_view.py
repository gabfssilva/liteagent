"""Chat view widget for displaying the full conversation in the chat interface."""

from textual.containers import VerticalScroll

from liteagent import Agent, AssistantMessage, ToolMessage
from liteagent.codec import to_json_str
from liteagent.events import (
    AssistantMessagePartialEvent,
    ToolRequestPartialEvent,
    TeamDispatchPartialEvent,
    TeamDispatchFinishedEvent,
    ToolExecutionCompleteEvent,
    AssistantMessageCompleteEvent,
    TeamDispatchedEvent
)
from liteagent.chat.textual.plotext import plot_stacked_bar
from liteagent.chat.textual.table import plot_table
from liteagent.chat.textual.helpers import pretty_incomplete_json
from .assistant_message import AssistantMessageWidget
from .tool_use import ToolUseWidget
from .internal_chat import InternalChatWidget


class ChatWidget(VerticalScroll):
    """The main chat view that displays conversation and manages event handlers."""

    def __init__(
        self,
        agent: Agent,
        loop_id: str | None = None,
        refresh_rate: float = 0.5,
        follow: bool = False,
        id: str = None,
        parent_id: str = None,
    ):
        super().__init__(id=id)
        agent.with_tool(plot_stacked_bar)
        agent.with_tool(plot_table)
        self._agent = agent
        self._parent_id = parent_id
        self._completed = False
        self.refresh_rate = refresh_rate
        self.follow = follow
        self.loop_id = loop_id
        self.bus = agent.bus

    def on_mount(self) -> None:
        @self.bus.on(AssistantMessagePartialEvent)
        async def handle_assistant_message_partial(event: AssistantMessagePartialEvent):
            if self._parent_id and self._completed:
                return False

            if event.agent != self._agent:
                return True

            if self.loop_id and self.loop_id != event.loop_id:
                return True

            message: AssistantMessage = event.message
            stream_id = message.content.stream_id

            widget_id = f"assistant_{stream_id}"

            try:
                widget = self.query_one(f"#{widget_id}", AssistantMessageWidget)
            except Exception:
                widget = AssistantMessageWidget(
                    id=widget_id,
                    agent=event.agent,
                    refresh_rate=self.refresh_rate,
                    follow=self.follow,
                    classes="assistant-message" if not self._parent_id else "assistant-message-inner",
                )

                await self.mount(widget)

            widget.assistant_content = message.content.accumulated
            return True

        @self.bus.on(AssistantMessageCompleteEvent)
        async def handle_assistant_message(event: AssistantMessageCompleteEvent):
            if self._parent_id and self._completed:
                return False

            if event.agent != self._agent:
                return True

            if self.loop_id and self.loop_id != event.loop_id:
                return True

            message: AssistantMessage = event.message
            stream_id = message.content.stream_id
            widget_id = f"assistant_{stream_id}"

            try:
                widget = self.query_one(f"#{widget_id}", AssistantMessageWidget)
            except Exception:
                widget = AssistantMessageWidget(
                    id=widget_id,
                    agent=event.agent,
                    refresh_rate=self.refresh_rate,
                    follow=self.follow,
                    classes="assistant-message" if not self._parent_id else "assistant-message-inner",
                )
                await self.mount(widget)
                widget.assistant_content = message.content.accumulated
            
            widget.finish()
            return True

        @self.bus.on(ToolRequestPartialEvent)
        async def handle_tool_request_partial(event: ToolRequestPartialEvent):
            if self._parent_id and self._completed:
                return False

            if event.agent != self._agent:
                return True

            if self.loop_id and self.loop_id != event.loop_id:
                return True

            chunk = event.chunk
            tool = event.tool
            tool_id = event.tool_id

            tool_widget_id = f"{tool.name}_{tool_id}"
            try:
                widget = self.query_one(f"#{tool_widget_id}", ToolUseWidget)
                widget.append_args(await to_json_str(chunk.accumulated_arguments, indent=2))
            except Exception:
                await self.mount(ToolUseWidget(
                    tool_widget_id,
                    tool,
                    chunk.accumulated_arguments,
                    classes="tool-message" if not self._parent_id else "tool-message-inner",
                    refresh_rate=self.refresh_rate,
                    follow=self.follow,
                ))

            return True

        @self.bus.on(TeamDispatchPartialEvent)
        async def handle_team_dispatch_start(event: TeamDispatchPartialEvent):
            if self._parent_id and self._completed:
                return False

            if event.agent != self._agent:
                return True

            if self.loop_id and self.loop_id != event.loop_id:
                return True

            widget_id = f"{event.target_agent.name}_{event.tool_id}"

            try:
                widget = self.query_one(f"#{widget_id}", InternalChatWidget)
            except Exception:
                name = event.tool.name
                arguments = event.accumulated_arguments
                agent = event.target_agent

                try:
                    widget = InternalChatWidget(
                        id=widget_id,
                        name=name,
                        prompt=arguments,
                        agent=agent,
                        loop_id=event.loop_id,
                        refresh_rate=self.refresh_rate,
                        classes="tool-message"
                    )

                    await self.mount(widget)
                except Exception as e:
                    return

            try:
                prompt = await to_json_str(event.accumulated_arguments)
                prompt = f'```json\n{pretty_incomplete_json(prompt)}\n```'
                widget.update_prompt(prompt)
            except Exception as e:
                self.notify(message=str(e), timeout=5, severity="error")

            return True

        @self.bus.on(TeamDispatchedEvent)
        async def handle_team_dispatch_complete(event: TeamDispatchedEvent):
            if self._parent_id and self._completed:
                return False

            if event.agent != self._agent:
                return True

            if self.loop_id and self.loop_id != event.loop_id:
                return True

            widget_id = f"{event.target_agent.name}_{event.tool_id}"

            try:
                widget = self.query_one(f"#{widget_id}", InternalChatWidget)
                widget.args_completed()
            except Exception as e:
                name = event.tool.name
                agent = event.target_agent
                prompt = f'```json\n{await to_json_str(event.arguments, indent=2)}\n```'

                try:
                    widget = InternalChatWidget(
                        id=widget_id,
                        name=name,
                        prompt=prompt,
                        agent=agent,
                        loop_id=event.loop_id,
                        refresh_rate=self.refresh_rate,
                        classes="tool-message"
                    )

                    await self.mount(widget)
                    widget.args_completed()
                except Exception as e:
                    self.notify(message=str(e), timeout=5, severity="error")

            return False

        @self.bus.on(TeamDispatchFinishedEvent)
        async def handle_team_dispatch_finished(event: TeamDispatchFinishedEvent):
            if self._parent_id and self._completed:
                return False

            if event.agent != self._agent:
                return True

            if self.loop_id and self.loop_id != event.loop_id:
                return True

            widget_id = f"{event.target_agent.name}_{event.tool_id}"
            
            try:
                widget = self.query_one(f"#{widget_id}", InternalChatWidget)
            except Exception:
                try:
                    prompt = f'```json\n{await to_json_str(event.arguments, indent=2)}\n```'
                    widget = InternalChatWidget(
                        id=widget_id,
                        name=event.tool.name,
                        prompt=prompt,
                        agent=event.target_agent,
                        loop_id=event.loop_id,
                        refresh_rate=self.refresh_rate,
                        classes="tool-message"
                    )
                    await self.mount(widget)
                except Exception as e:
                    self.notify(message=str(e), timeout=5, severity="error")
                    return True
            
            try:
                widget.complete(False)
            except Exception as e:
                self.notify(message=str(e), timeout=5, severity="error")

            return True

        @self.bus.on(ToolExecutionCompleteEvent)
        async def handle_tool_exec_complete(event: ToolExecutionCompleteEvent):
            if self._parent_id and self._completed:
                return False

            if event.agent != self._agent:
                return True

            if self.loop_id and self.loop_id != event.loop_id:
                return True

            tool = event.tool
            tool_id = event.tool_id

            tool_widget_id = f"{tool.name}_{tool_id}"

            try:
                widget = self.query_one(f"#{tool_widget_id}", ToolUseWidget)
            except Exception:
                widget = ToolUseWidget(
                    id=tool_widget_id,
                    tool=tool,
                    initial_args=await to_json_str(event.arguments, indent=2),
                    classes="tool-message" if not self._parent_id else "tool-message-inner",
                    refresh_rate=self.refresh_rate,
                    follow=self.follow,
                )
                await self.mount(widget)
            
            widget.append_result(await to_json_str(event.result, indent=2))
            widget.complete(isinstance(event.result, ToolMessage.ExecutionError))
            self.scroll_end()

    def mark_completed(self):
        self._completed = True
