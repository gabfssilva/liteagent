"""Chat view widget for displaying the full conversation in the chat interface."""
from typing import Type

from textual.containers import VerticalScroll
from textual.widget import Widget

from liteagent import Agent, AssistantMessage, ToolMessage
from liteagent.codec import to_json_str
from liteagent.events import (
    AssistantMessageEvent,
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

    async def retrieve_or_mount[W: Widget](self, widget_id: str, widget_class: Type[W], **kwargs) -> W:
        try:
            return self.query_one(f"#{widget_id}", widget_class)
        except Exception:
            widget = widget_class(id=widget_id, **kwargs)
            await self.mount(widget)
            return widget

    def on_mount(self) -> None:
        @self.bus.on(AssistantMessageEvent)
        async def handle_assistant_message_partial(event: AssistantMessageEvent):
            if self._parent_id and self._completed:
                return False

            if event.agent != self._agent:
                return True

            if self.loop_id and self.loop_id != event.loop_id:
                return True

            message: AssistantMessage = event.message

            text_stream = message.content
            stream_id = text_stream.stream_id
            widget_id = f"assistant_{stream_id}"

            widget = await self.retrieve_or_mount(
                widget_id=widget_id,
                widget_class=AssistantMessageWidget,
                agent=event.agent,
                refresh_rate=self.refresh_rate,
                follow=self.follow,
                classes="assistant-message" if not self._parent_id else "assistant-message-inner",
            )

            widget.assistant_content = await text_stream.get()

            async def process():
                async for content in text_stream.content:
                    widget.assistant_content = content

                widget.complete()

            self.run_worker(process())

            return True

        # @self.bus.on(AssistantMessageCompleteEvent)
        async def handle_assistant_message(event: AssistantMessageCompleteEvent):
            if self._parent_id and self._completed:
                return False

            if event.agent != self._agent:
                return True

            if self.loop_id and self.loop_id != event.loop_id:
                return True

            message: AssistantMessage = event.message

            # Handle different types of content
            match message.content:
                case AssistantMessage.TextStream() as text_stream:
                    stream_id = text_stream.stream_id
                    widget_id = f"assistant_{stream_id}"

                    widget = await self.retrieve_or_mount(
                        widget_id=widget_id,
                        widget_class=AssistantMessageWidget,
                        agent=event.agent,
                        refresh_rate=self.refresh_rate,
                        follow=self.follow,
                        classes="assistant-message" if not self._parent_id else "assistant-message-inner",
                    )

                    # Get completed content from the TextStream
                    content = await text_stream.get()
                    widget.assistant_content = content
                    widget.finish()
                case _:
                    # Legacy or unknown content type
                    self.notify("Unknown message content type", severity="warning")

            return True

        @self.bus.on(ToolRequestPartialEvent)
        async def handle_tool_request_partial(event: ToolRequestPartialEvent):
            if self._parent_id and self._completed:
                return False

            if event.agent != self._agent:
                return True

            if self.loop_id and self.loop_id != event.loop_id:
                return True

            message: AssistantMessage = event.message
            tool = event.tool

            match message.content:
                case AssistantMessage.ToolUseStream() as tool_stream:
                    tool_id = tool_stream.tool_use_id
                    tool_widget_id = f"{tool.name}_{tool_id}"

                    # Get current arguments
                    args_str = await tool_stream.get_arguments()
                    args_display = await to_json_str(await tool_stream.get_arguments_as_json(), indent=2)

                    widget = await self.retrieve_or_mount(
                        widget_id=tool_widget_id,
                        widget_class=ToolUseWidget,
                        tool=tool,
                        initial_args=args_display,
                        classes="tool-message" if not self._parent_id else "tool-message-inner",
                        refresh_rate=self.refresh_rate,
                        follow=self.follow,
                    )

                    widget.append_args(args_display)
                case _:
                    # Legacy or unknown content type
                    self.notify("Unknown tool message content type", severity="warning")

            return True

        @self.bus.on(TeamDispatchPartialEvent)
        async def on_team_message(event: TeamDispatchPartialEvent):
            if self._parent_id and self._completed:
                return False

            if event.agent != self._agent:
                return True

            if self.loop_id and self.loop_id != event.loop_id:
                return True

            widget_id = f"{event.target_agent.name}_{event.tool_id}"
            name = event.tool.name
            arguments = event.accumulated_arguments
            agent = event.target_agent

            try:
                widget = await self.retrieve_or_mount(
                    widget_id=widget_id,
                    widget_class=InternalChatWidget,
                    name=name,
                    prompt=arguments,
                    agent=agent,
                    loop_id=event.loop_id,
                    refresh_rate=self.refresh_rate,
                    classes="tool-message"
                )

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
            name = event.tool.name
            agent = event.target_agent
            prompt = f'```json\n{await to_json_str(event.arguments, indent=2)}\n```'

            try:
                widget = await self.retrieve_or_mount(
                    widget_id=widget_id,
                    widget_class=InternalChatWidget,
                    name=name,
                    prompt=prompt,
                    agent=agent,
                    loop_id=event.loop_id,
                    refresh_rate=self.refresh_rate,
                    classes="tool-message"
                )
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
            prompt = f'```json\n{await to_json_str(event.arguments, indent=2)}\n```'

            try:
                widget = await self.retrieve_or_mount(
                    widget_id=widget_id,
                    widget_class=InternalChatWidget,
                    name=event.tool.name,
                    prompt=prompt,
                    agent=event.target_agent,
                    loop_id=event.loop_id,
                    refresh_rate=self.refresh_rate,
                    classes="tool-message"
                )
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

            message: AssistantMessage = event.message
            tool = event.tool

            match message.content:
                case AssistantMessage.ToolUseStream() as tool_stream:
                    tool_id = tool_stream.tool_use_id
                    tool_widget_id = f"{tool.name}_{tool_id}"

                    # Get completed arguments
                    args_display = await to_json_str(await tool_stream.get_arguments_as_json(), indent=2)

                    widget = await self.retrieve_or_mount(
                        widget_id=tool_widget_id,
                        widget_class=ToolUseWidget,
                        tool=tool,
                        initial_args=args_display,
                        classes="tool-message" if not self._parent_id else "tool-message-inner",
                        refresh_rate=self.refresh_rate,
                        follow=self.follow,
                    )

                    result_display = await to_json_str(event.result, indent=2)
                    widget.append_result(result_display)
                    widget.complete(isinstance(event.result, ToolMessage.ExecutionError))
                case _:
                    # Legacy or unknown content type
                    self.notify("Unknown tool message content type", severity="warning")
            self.scroll_end()

    def mark_completed(self):
        self._completed = True
