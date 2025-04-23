import asyncio
import json
import re
import time
from typing import AsyncIterable, AsyncIterator

from pydantic import JsonValue
from rich.errors import MarkupError
from textual import on
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.content import Content
from textual.reactive import reactive, var
from textual.widgets import Markdown, Input, Static, Pretty, TabbedContent

from liteagent import AssistantMessage, UserMessage, ToolRequest, Agent, ToolMessage, Tool, AgentDispatcherTool
from liteagent.internal.memoized import ContentStream
from liteagent.message import ExecutionError, Message


class AppendableMarkdown(Static):
    def __init__(self, content: str, refresh_rate: float = 0.5):
        super().__init__(markup=False)
        self._chunks = asyncio.Queue()
        self._refresh_rate = refresh_rate
        self._finished = False
        self._content = content

    def compose(self) -> ComposeResult:
        yield Markdown(self._content)

    async def on_mount(self) -> None:
        self.run_worker(self._watch_content())

    async def _watch_content(self):
        while not self._finished:
            try:
                await self.query_one(Markdown).update(self._content)
                await asyncio.sleep(self._refresh_rate)
            except MarkupError:
                continue

        await self.query_one(Markdown).update(self._content)

    async def append(self, message: str) -> None:
        self._content += message

    def finish(self) -> None:
        self._finished = True


class UserMessageWidget(Static):
    def __init__(self, content: str, classes: str = "user-message"):
        super().__init__(classes=classes)
        self.markdown = AppendableMarkdown(content=f"{content}")
        self.border_title = "👤"

    def compose(self) -> ComposeResult:
        yield self.markdown


class AssistantMessageWidget(Static):
    def __init__(
        self,
        name: str,
        classes: str = "assistant-message",
        refresh_rate: float = 0.5,
    ):
        super().__init__(classes=classes)
        self.markdown = AppendableMarkdown(content="", refresh_rate=refresh_rate)
        self.border_title = "🤖"
        self.border_subtitle = name

    def compose(self) -> ComposeResult:
        yield self.markdown


class CollapsibleChatView(Static):
    state = reactive("waiting")
    frame = reactive(0)

    def __init__(
        self,
        *,
        id: str,
        name: str,
        prompt: str,
        agent: Agent,
        classes: str = "tool-message"
    ):
        super().__init__(
            id=id,
            classes=classes
        )

        self.agent_name = name
        self.pretty_name = name.replace("redirection", "").replace("_", " ").title()
        self.prompt = prompt
        self.agent = agent
        self.border_title = f"🤖 {self.pretty_name} ⚪"

    def on_mount(self) -> None:
        self.state = "waiting"
        self._timer = self.set_interval(0.5, self._blink)

    def _blink(self) -> None:
        if self.state == "waiting":
            if self.frame == 0:
                self.frame = 1
            else:
                self.frame = 0

    def compose(self) -> ComposeResult:
        with TabbedContent("Prompt", "Result", classes="internal-chat-view"):
            yield Pretty(self.prompt)
            yield ChatView(self.agent)

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

    async def process(self, messages) -> None:
        async def do_process():
            try:
                if isinstance(messages, ExecutionError):
                    raise Exception(messages)

                await self.query_one(ChatView).process(messages, True)
                self.state = "completed"
            except Exception as e:
                self.state = "failed"
                await self.query_one(ChatView).mount(Markdown(f"error: {e}"))

        self.run_worker(do_process())


class ToolUseWidget(Static):
    tool_name = var("")
    tool_emoji = var("")
    tool_args = var({})
    state = reactive("waiting")
    frame = reactive(0)
    start = reactive(0)
    elapsed = reactive(0)

    def __init__(
        self,
        id: str,
        arguments: dict,
        tool: Tool,
        classes: str = "tool-message"
    ):
        super().__init__(id=id, classes=classes)
        self.tool_name = self._camel_to_words(tool.name.replace("__", ": ").replace("_", " ")).title()
        self.tool_emoji = tool.emoji
        self.tool_args = arguments
        self.set_styles(border_title=tool.emoji)
        self.title_template = f"{self.tool_emoji} {self.tool_name}" + " {emoji}"
        self.border_title =  self.title_template.format(emoji="⚪")
        self.tooltip = Content.from_text(tool.description, markup=False)

    @staticmethod
    def _camel_to_words(text: str) -> str:
        return re.sub(r'(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', ' ', text)

    def compose(self) -> ComposeResult:
        with TabbedContent("Arguments", "Result"):
            yield Pretty(self.tool_args)
            yield AppendableMarkdown(content="", refresh_rate=1)

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
            self.border_title = self.title_template.format(emoji="🟢")
        elif state == "failed":
            self._blink_timer.stop()
            self._elapsed_timer.stop()
            self.border_title = self.title_template.format(emoji="🔴")

    def complete(self, failed: bool) -> None:
        self.state = "failed" if failed else "completed"
        self.query_one(AppendableMarkdown).finish()

    async def append_result(self, chunk: str) -> None:
        if len(chunk) > 250:
            chunk = chunk[:250] + "\n...[omitted]"

        result = self.query_one(AppendableMarkdown)
        await result.append(chunk)

    async def append_json(self, chunk: JsonValue) -> None:
        result = self.query_one(AppendableMarkdown)
        await result.append(f"""```json\n{json.dumps(chunk, indent=2)}\n```""")


class ChatView(VerticalScroll):
    def __init__(self, agent: Agent, id: str = None):
        super().__init__(id=id)
        self._agent = agent

    async def process(self, messages: AsyncIterable[Message], inner: bool) -> None:
        async for message in messages:
            match message:
                case UserMessage():
                    pass

                case AssistantMessage(content=ContentStream() as stream):
                    assistant_widget = AssistantMessageWidget(
                        message.agent.replace("_", " ").title(),
                        "assistant-message" if not inner else "assistant-message-inner", 1 if inner else 1 / 30
                    )

                    await self.mount(assistant_widget)

                    async def append_stream(s: ContentStream):
                        async for chunk in s:
                            await assistant_widget.markdown.append(chunk)

                        assistant_widget.markdown.finish()

                    self.run_worker(append_stream(stream))

                case AssistantMessage(content=ToolRequest(id=tool_id,arguments=arguments, tool=AgentDispatcherTool() as tool)):
                    await self.mount(CollapsibleChatView(
                        id=f"{tool.name}_{tool_id}",
                        name=tool.name,
                        prompt=arguments,
                        agent=self._agent,
                        classes="tool-message-inner" if inner else "tool-message",
                    ))

                case AssistantMessage(content=ToolRequest(id=tool_id,arguments=arguments, tool=tool)):
                    await self.mount(ToolUseWidget(
                        id=f"{tool.name}_{tool_id}",
                        arguments=arguments,
                        tool=tool,
                        classes="tool-message" if not inner else "tool-message-inner"
                    ))

                case ToolMessage(tool=AgentDispatcherTool()) as tool_message:
                    widget = self.query_one(f"#{tool_message.name}_{tool_message.id}", CollapsibleChatView)
                    self.run_worker(widget.process(tool_message.content))

                case ToolMessage() as message:
                    async def process_result(m):
                        tool_use_widget = self.query_one(f"#{m.name}_{m.id}", ToolUseWidget)

                        result = await m.content_as_json()
                        is_error = isinstance(m.content, ExecutionError)

                        if isinstance(result, str):
                            await tool_use_widget.append_result(result)
                        else:
                            await tool_use_widget.append_json(result)

                        tool_use_widget.complete(is_error)

                    self.run_worker(process_result(message))


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
    
    UserMessageWidget > AppendableMarkdown > Markdown {
        color: $foreground-darken-3;
    } 
    
    AssistantMessageWidget > AppendableMarkdown > Markdown {
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
        with ChatView(self._agent):
            from art import text2art
            yield Static(text2art(self._logo, font='tarty2'), id="chat-art")
        yield Input(placeholder="How can I help you?")

    def on_mount(self) -> None:
        self.run_worker(self.monitor_blocking())
        self.query_one(Input).focus()
        self.theme = self._theme

    @on(Input.Submitted)
    def on_input(self, event: Input.Submitted) -> None:
        chat_view = self.query_one(ChatView)
        event.input.clear()
        prompt = event.value
        chat_view.mount(UserMessageWidget(prompt))
        self.run_worker(self.inference(prompt))
        self.query_one(Input).focus()

    async def inference(self, prompt: str):
        chat_view = self.query_one(ChatView)
        await chat_view.process(self.send(prompt), False)

    async def send(self, prompt: str) -> AsyncIterator[Message]:
        async for message in self._session(prompt):
            yield message

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
