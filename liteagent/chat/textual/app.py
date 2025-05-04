import asyncio
import re
import time

from textual import on, events
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.content import Content
from textual.markup import MarkupError
from textual.reactive import reactive, var
from textual.widget import Widget
from textual.widgets import Markdown, Input, Static, TabbedContent

from liteagent import AssistantMessage, Agent, ToolMessage, Tool
from liteagent.bus.eventbus import bus
from liteagent.chat.textual.table import plot_table
from liteagent.codec import to_json_str
from liteagent.events import (
    AssistantMessagePartialEvent,
    ToolRequestPartialEvent,
    TeamDispatchPartialEvent,
    TeamDispatchFinishedEvent,
    ToolExecutionCompleteEvent, AssistantMessageCompleteEvent
)
from liteagent.chat.textual.plotext import plot_stacked_bar


class ReactiveMarkdown(Static):
    def __init__(
        self,
        markdown: str = "",
        refresh_rate: float = 0.5,
        finished: bool = False,
        follow: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.markdown = markdown
        self.refresh_rate = refresh_rate
        self.finished = finished
        self.follow = follow

    def compose(self) -> ComposeResult:
        yield Markdown(self.markdown)

    async def on_mount(self) -> None:
        self.run_worker(self._watch_content())

    async def _watch_content(self):
        while not self.finished:
            try:
                await self.query_one(Markdown).update(self.markdown)

                if self.follow:
                    chat_view = self.query_ancestor(ChatView)
                    if chat_view:
                        chat_view.scroll_end()

                await asyncio.sleep(self.refresh_rate)
            except MarkupError:
                continue

        await self.query_one(Markdown).update(self.markdown)

    def update(self, markdown: str) -> None:
        self.markdown = markdown

    def finish(self) -> None:
        self.finished = True


class UserMessageWidget(Static):
    def __init__(self, content: str, classes: str = "user-message"):
        super().__init__(classes=classes)
        self.markdown = ReactiveMarkdown(markdown=f"{content}", finished=True)
        self.border_title = "👤"

    def compose(self) -> ComposeResult:
        yield self.markdown


class AssistantMessageWidget(Static):
    assistant_content = reactive("")
    finished = reactive(False)

    def __init__(
        self,
        id: str,
        agent: Agent,
        refresh_rate: float = 0.5,
        follow: bool = False,
        classes: str = "assistant-message",
    ):
        super().__init__(classes=classes, id=id)

        self.border_title = "🤖"
        self.border_subtitle = f"{agent.name.replace('_', ' ').title()}"
        self.tooltip = f"{agent.provider.name}"
        self.refresh_rate = refresh_rate
        self.follow = follow

    def compose(self) -> ComposeResult:
        yield ReactiveMarkdown(refresh_rate=self.refresh_rate, follow=self.follow)

    def watch_assistant_content(self, assistant_content: str):
        self.query_one(ReactiveMarkdown).update(assistant_content)

    def watch_finished(self, finished: bool):
        if finished:
            self.query_one(ReactiveMarkdown).finish()

    def finish(self):
        self.finished = True

    async def on_mouse_down(self, event: events.MouseDown) -> None:
        if event.button == 3:  # Right click
            self.app.copy_to_clipboard(self.assistant_content)
            self.notify("Copied to clipboard! ✅", severity="information")


class InternalChatView(Static):
    prompt = reactive("")
    state = reactive("waiting")
    frame = reactive(0)

    def __init__(
        self,
        *,
        id: str,
        name: str,
        prompt: dict | list | str | None,
        agent: Agent,
        loop_id: str | None = None,
        classes: str = "tool-message"
    ):
        super().__init__(
            id=id,
            classes=classes
        )

        self.agent_name = name
        self.pretty_name = name.replace("redirection", "").replace("_", " ").title()

        if prompt and isinstance(prompt, dict) and len(prompt) == 1 and "prompt" in prompt:
            prompt = prompt["prompt"]

        self._prompt = prompt or ""
        self.agent = agent
        self.border_title = f"🤖 {self.pretty_name} ⚪"
        self.loop_id = loop_id

    def compose(self) -> ComposeResult:
        with TabbedContent("Prompt", "Result", classes="internal-chat-view"):
            yield ReactiveMarkdown(self._prompt)
            yield ChatView(
                agent=self.agent,
                parent_id=self.id,
                refresh_rate=1 / 3,
                follow=False,
                loop_id=self.loop_id,
            )

    def on_mount(self) -> None:
        self.state = "waiting"
        self._timer = self.set_interval(0.5, self._blink)
        self._chat_view = None

    def _blink(self) -> None:
        if self.state == "waiting":
            if self.frame == 0:
                self.frame = 1
            else:
                self.frame = 0

    def update_prompt(self, prompt):
        self.query_one(ReactiveMarkdown).update(prompt)

    def watch_frame(self, frame):
        emoji = "⚪" if frame == 0 else "  "
        self.border_title = f"🤖 {self.pretty_name} {emoji}"

    def watch_state(self, state: str) -> None:
        if state == "completed":
            self._timer.stop()
            self.border_title = f"🤖 {self.pretty_name} 🟢"
        elif state == "failed":
            self._timer.stop()
            self.border_title = f"🤖 {self.pretty_name} 🔴"

    def complete(self, failed: bool) -> None:
        self.state = "failed" if failed else "completed"

        if not self._chat_view:
            try:
                self._chat_view = self.query_one(ChatView)
                if self._chat_view:
                    self._chat_view.mark_completed()
            except Exception:
                pass

    async def handle_error(self, error) -> None:
        self.state = "failed"
        error_message = f"error: {error}"
        await self.query_one(ChatView).mount(ReactiveMarkdown(error_message))


class WidgetRenderer(Widget):
    def __init__(self, message: AssistantMessage, *children: Widget):
        super().__init__(*children, classes="tool-message")
        self._message = message
        self._tool_use: AssistantMessage.ToolUseChunk = self._message.content
        self.border_title = f"{self._tool_use.tool.emoji} {self._tool_use.name}"
        self.tooltip = Content.from_text(self._tool_use.tool.description, markup=False)
        self.id = f"{self._tool_use.name}_{self._tool_use.tool_use_id}"
        self.set_styles(border_title=self._tool_use.tool.emoji)

    async def do_render(self, message: ToolMessage) -> None:
        await self.mount(message.content)


class ToolUseWidget(Static):
    tool_name = var("")
    tool_emoji = var("")
    state = reactive("waiting")
    frame = reactive(0)
    start = reactive(0)
    elapsed = reactive(0)

    def __init__(
        self,
        id: str,
        tool: Tool,
        initial_args: str | None,
        refresh_rate: float = 1 / 3,
        follow: bool = False,
        classes: str = "tool-message"
    ):
        super().__init__(id=id, classes=classes)
        self.tool_name = self._camel_to_words(tool.name.replace("__", ": ").replace("_", " ")).title()
        self.tool_emoji = tool.emoji
        self.set_styles(border_title=tool.emoji)
        self.title_template = f"{self.tool_emoji} {self.tool_name}" + " {emoji}"
        self.border_title = self.title_template.format(emoji="⚪")
        self.tooltip = Content.from_text(tool.description, markup=False)
        self.initial_args = initial_args
        self.refresh_rate = refresh_rate
        self.follow = follow

    @staticmethod
    def _camel_to_words(text: str) -> str:
        return re.sub(r'(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', ' ', text)

    def compose(self) -> ComposeResult:
        with TabbedContent("Arguments", "Result"):
            yield ReactiveMarkdown(
                markdown=self.initial_args or "👻",
                id=f"{self.id}_args",
                refresh_rate=self.refresh_rate,
                follow=self.follow,
            )

            yield ReactiveMarkdown(
                markdown="",
                id=f"{self.id}_result",
                refresh_rate=self.refresh_rate,
                follow=self.follow,
            )

    def on_mount(self) -> None:
        self.state = "waiting"
        self.start = time.perf_counter()
        self._blink_timer = self.set_interval(0.5, self._blink)
        self._elapsed_timer = self.set_interval(0.1, self._elapsed)

    def _elapsed(self):
        self.elapsed = time.perf_counter() - self.start

    def _blink(self) -> None:
        if self.state == "waiting":
            if self.frame == 0:
                self.frame = 1
            else:
                self.frame = 0

    def watch_frame(self, frame):
        emoji = "⚪" if frame == 0 else "  "
        self.border_title = self.title_template.format(emoji=emoji)

    def watch_elapsed(self, elapsed):
        self.border_subtitle = f"{elapsed:.1f}s"

    def watch_state(self, state: str) -> None:
        if state == "completed":
            self._blink_timer.stop()
            self._elapsed_timer.stop()
            self.query_one(f"#{self.id}_result", ReactiveMarkdown).finish()
            self.query_one(f"#{self.id}_args", ReactiveMarkdown).finish()
            self.border_title = self.title_template.format(emoji="🟢")
        elif state == "failed":
            self._blink_timer.stop()
            self._elapsed_timer.stop()
            self.query_one(f"#{self.id}_result", ReactiveMarkdown).finish()
            self.query_one(f"#{self.id}_args", ReactiveMarkdown).finish()
            self.border_title = self.title_template.format(emoji="🔴")

    def complete(self, failed: bool) -> None:
        self.state = "failed" if failed else "completed"

    def append_args(self, accumulated: str) -> None:
        try:
            args = self.query_one(f"#{self.id}_args", ReactiveMarkdown)
            args.update('```json\n' + accumulated + '\n```')
        except Exception as e:
            self.app.exit(message=str(e))

    def append_result(self, json_result: str) -> None:
        try:
            self.query_one(f"#{self.id}_result", ReactiveMarkdown).update('```json\n' + json_result + '\n```')
        except Exception as e:
            self.app.exit(message=str(e))


class ChatView(VerticalScroll):
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

    def on_mount(self) -> None:
        @bus.on(AssistantMessagePartialEvent)
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
                    classes="assistant-message",
                )

                await self.mount(widget)

            widget.assistant_content = message.content.accumulated

        @bus.on(AssistantMessageCompleteEvent)
        async def handle_assistant_message(event: AssistantMessageCompleteEvent):
            if self._parent_id and self._completed:
                return False

            if event.agent != self._agent:
                return True

            if self.loop_id and self.loop_id != event.loop_id:
                return True

            message: AssistantMessage = event.message
            stream_id = message.content.stream_id

            widget = self.query_one(f"#assistant_{stream_id}", AssistantMessageWidget)
            widget.finish()
            return True

        @bus.on(ToolRequestPartialEvent)
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
                    classes="tool-message",
                    refresh_rate=self.refresh_rate,
                    follow=self.follow,
                ))

        @bus.on(TeamDispatchPartialEvent)
        async def handle_team_dispatch_start(event: TeamDispatchPartialEvent):
            if self._parent_id and self._completed:
                return False

            if event.agent != self._agent:
                return True

            if self.loop_id and self.loop_id != event.loop_id:
                return True

            widget_id = f"{event.target_agent.name}_{event.tool_id}"

            try:
                widget = self.query_one(f"#{widget_id}", InternalChatView)
            except Exception:
                name = event.tool.name
                arguments = event.accumulated_arguments
                agent = event.target_agent

                try:
                    widget = InternalChatView(
                        id=widget_id,
                        name=name,
                        prompt=arguments,
                        agent=agent,
                        loop_id=event.loop_id,
                        classes="tool-message"
                    )

                    await self.mount(widget)
                except Exception as e:
                    self.app.exit(message=str(e))
                    return

            widget.update_prompt(await to_json_str(event.accumulated_arguments, indent=2))

        @bus.on(TeamDispatchFinishedEvent)
        async def handle_team_dispatch_complete(event: TeamDispatchFinishedEvent):
            if self._parent_id and self._completed:
                return False

            if event.agent != self._agent:
                return True

            if self.loop_id and self.loop_id != event.loop_id:
                return True

            widget_id = f"{event.target_agent.name}_{event.tool_id}"
            widget = self.query_one(f"#{widget_id}", InternalChatView)
            widget.complete(False)

        @bus.on(ToolExecutionCompleteEvent)
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

            widget = self.query_one(f"#{tool_widget_id}", ToolUseWidget)
            widget.append_result(await to_json_str(event.result, indent=2))
            widget.complete(isinstance(event.result, ToolMessage.ExecutionError))
            self.scroll_end()

    def mark_completed(self):
        self._completed = True


class ChatApp(App):
    CSS = """
    MyApp {
        height: 100%;
    }
    
    Tooltip {
        background: $background;
        color: auto 90%;
        border: round $primary;
    }
    
    Markdown {
        height: auto;
        padding: 0 2 -1 2;
        layout: vertical;
        color: $foreground;
        background: $background;
        overflow-y: auto;
    
        &:focus {
            background-tint: $foreground 5%;
        }
    }
    
    TabbedContent {
        background: $background;
    }
    
    Tab {
        background: $background;
        
        padding: 0 2 -1 2;
    }
    
    #chat-view {
      height: 1fr;
      overflow-y: auto;
      padding: 0;
      margin: 0;
    }
    
    UserMessageWidget > Markdown {
        color: $foreground-darken-3;
    } 
    
    AssistantMessageWidget > Markdown {
        color: $foreground-lighten-3;
    } 
    
    .user-message {
        margin: 0 10 1 0;
        align: left middle;
        border: round $secondary;
        background: $background;
        padding: 1;
    }

    .assistant-message {
        margin: 0 0 1 10;
        align: right middle;
        border: round $secondary;
        background: $background;
        padding: 1;
        color: $foreground-darken-3;
    }
    
    .assistant-message-inner {
        margin: 0 0 1 0;
        align: left middle;
        border: round $secondary;
        background: $background;
        padding: 1;
    }

    .tool-message {
        margin: 0 0 1 10;
        align: right middle;
        border: round $accent;
        background: $background;
    }
    
    .tool-message-inner {
        margin: 0 0 1 0;
        align: left middle;
        border: round $accent;
        background: $background;
    }
 
    ToolUseWidget Collapsible {
        background: $background;
    }
    
    .internal-chat-view {
        align: left middle;
    }
    
    CollapsibleChatView Collapsible {
        # border: round $accent;
        background: $background;
        padding: 0;
    }
    
    TabbedContent > ContentSwitcher {
        height: auto;
        background: $background;
    }

    Collapsible {
        overflow-y: auto;
        max-height: 25;
        background: $background;
    }
    
    CollapsibleChatView {
        overflow-y: auto;
        max-height: 20;
        background: $background;
    }
    
    Collapsible > .collapsible--content {
        background: $background;
    }
  
    #chat-art {
       text-align: center;
    }

    Input {
        border: round $background;
        align: left bottom;
        padding: 0;
    }
    """

    def __init__(self, agent: Agent, logo: str = None, theme: str = "ivory-paper"):
        super().__init__()

        self._agent = agent
        self._session = agent.stateful()
        self._logo = agent.name.replace("_", "").title() if logo is None else logo
        self._theme = theme

    def compose(self) -> ComposeResult:
        with ChatView(agent=self._agent, refresh_rate=1 / 30, follow=True):
            from art import text2art
            yield Static(text2art(self._logo, font='tarty2'), id="chat-art")
        yield Input(placeholder="How can I help you?")

    def on_mount(self) -> None:
        self.run_worker(self.monitor_blocking())
        self.query_one(Input).focus()
        self.theme = self._theme

    @on(Input.Submitted)
    def on_input(self, event: Input.Submitted) -> None:
        prompt = event.value
        chat_view = self.query_one(ChatView)
        chat_view.mount(UserMessageWidget(prompt))
        chat_view.scroll_end()
        event.input.clear()
        self.run_worker(self._process_input(prompt))
        self.query_one(Input).focus()

    async def _process_input(self, prompt: str):
        async for _ in self._session(prompt):
            pass

    async def monitor_blocking(self, threshold=0.1):
        import asyncio
        import time

        while True:
            before = time.perf_counter()
            await asyncio.sleep(0)
            after = time.perf_counter()
            delta = after - before
            if delta > threshold:
                self.notify(f"The coroutine was blocked for {delta:.3f} seconds", severity="error", timeout=10)
            await asyncio.sleep(0.01)
