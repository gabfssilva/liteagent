"""Chat view widget for displaying the full conversation in the chat interface."""
from typing import Type

from textual.containers import VerticalScroll
from textual.widget import Widget

from liteagent import Agent, AssistantMessage, ToolMessage
from liteagent.codec import to_json_str
from liteagent.events import (
    AssistantMessageEvent,
    ToolMessageEvent
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
        async def handle_assistant_message(event: AssistantMessageEvent):
            if self._parent_id and self._completed:
                return False

            if event.agent != self._agent:
                return True

            if self.loop_id and self.loop_id != event.loop_id:
                return True

            message: AssistantMessage = event.message

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

                    async def process():
                        async for content in text_stream.content:
                            widget.assistant_content = content

                        widget.finish()

                    self.run_worker(process())

                case AssistantMessage.ToolUseStream() as tool_stream:
                    tool = tool_stream.tool
                    tool_id = tool_stream.tool_use_id
                    
                    if tool.type == 'agent':
                        widget_id = f"{tool.agent.name}_{tool_id}"
                        initial_args = await tool_stream.get_arguments()

                        agent_widget = await self.retrieve_or_mount(
                            widget_id=widget_id,
                            widget_class=InternalChatWidget,
                            name=tool.name,
                            prompt=initial_args,
                            agent=tool.agent,
                            loop_id=tool_id,
                            refresh_rate=self.refresh_rate,
                            classes="tool-message"
                        )

                        async def process_agent_args():
                            async for current_args in tool_stream.arguments:
                                prompt = f'```json\n{current_args}\n```'
                                agent_widget.update_prompt(prompt)

                            agent_widget.args_completed()

                        self.run_worker(process_agent_args())
                    else:
                        tool_widget_id = f"{tool.name}_{tool_id}"
                        initial_args = await tool_stream.get_arguments()

                        widget = await self.retrieve_or_mount(
                            widget_id=tool_widget_id,
                            widget_class=ToolUseWidget,
                            tool=tool,
                            initial_args=initial_args,
                            classes="tool-message" if not self._parent_id else "tool-message-inner",
                            refresh_rate=self.refresh_rate,
                            follow=self.follow,
                        )
                        
                    async def process_tool_args():
                        async for args in tool_stream.arguments:
                            widget.append_args(args)

                        widget.finished_arguments = True

                    self.run_worker(process_tool_args())
                case _:
                    self.notify("Unknown message content type", severity="warning")

            return True

        @self.bus.on(ToolMessageEvent)
        async def handle_tool_message(event: ToolMessageEvent):
            if self._parent_id and self._completed:
                return False

            if event.agent != self._agent:
                return True

            if self.loop_id and self.loop_id != event.loop_id:
                return True

            message: ToolMessage = event.message
            tool = event.tool
            
            if not tool:
                self.notify(f"Tool '{message.tool_name}' not found", severity="error")
                return True
            
            tool_id = message.tool_use_id
            
            if tool.type == 'agent':
                widget_id = f"{tool.agent.name}_{tool_id}"
                
                try:
                    widget = await self.retrieve_or_mount(
                        widget_id=widget_id,
                        widget_class=InternalChatWidget,
                        name=tool.name,
                        prompt=message.arguments,
                        agent=tool.agent,
                        loop_id=tool_id,
                        refresh_rate=self.refresh_rate,
                        classes="tool-message"
                    )
                    widget.complete(False)
                except Exception as e:
                    self.notify(message=str(e), timeout=5, severity="error")
            else:
                tool_widget_id = f"{tool.name}_{tool_id}"

                widget = await self.retrieve_or_mount(
                    widget_id=tool_widget_id,
                    widget_class=ToolUseWidget,
                    tool=tool,
                    initial_args=await to_json_str(message.arguments, indent=2),
                    classes="tool-message" if not self._parent_id else "tool-message-inner",
                    refresh_rate=self.refresh_rate,
                    follow=self.follow,
                )
                
                result_display = await to_json_str(message.content, indent=2)
                widget.append_result(result_display)
                widget.complete(isinstance(message.content, ToolMessage.ExecutionError))
                
            self.scroll_end()

    def mark_completed(self):
        self._completed = True
