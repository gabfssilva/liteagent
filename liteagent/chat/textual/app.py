import asyncio
import json
from typing import AsyncIterable

from pydantic import JsonValue
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.reactive import reactive, var
from textual.theme import Theme
from textual.widgets import Markdown, Input, Static, TabbedContent, Collapsible

from liteagent import AssistantMessage, UserMessage, ToolRequest, Agent, ToolMessage
from liteagent.internal.memoized import ContentStream
from liteagent.message import ExecutionError, Message


class AppendableMarkdown(Markdown):
    def __init__(self, content: str):
        super().__init__(markdown=content)
        self.content = content
        self._chunks = asyncio.Queue()

    def on_mount(self) -> None:
        self.run_worker(self.build())

    async def build(self) -> None:
        while True:
            chunk = await self._chunks.get()
            self.content += chunk
            self._chunks.task_done()
            await self.update(self.content)
            await asyncio.sleep(0.005)

    async def append(self, message: str) -> None:
        await self._chunks.put(message)


class UserMessageWidget(AppendableMarkdown):
    def __init__(self, content: str):
        super().__init__(content=f"👤 ▷ 🤖:\n{content}")


class AssistantMessageWidget(AppendableMarkdown):
    def __init__(self):
        super().__init__(content="🤖 ▷ 👤:\n")


class CollapsibleChatView(Static):
    state = reactive("waiting")
    frame = reactive(0)

    def __init__(
        self,
        id: str,
        name: str,
        prompt: str,
        agent: Agent,
    ):
        super().__init__(id=id)
        self.agent_name = name
        self.prompt = prompt
        self.agent = agent

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
        with Collapsible(title=f"🤖 ▷ 🤖 {self.agent_name} ⚪", collapsed=True):
            with ChatView(self.agent):
                yield UserMessageWidget(self.prompt)

    def watch_frame(self, frame):
        collapsible = self.query_one(Collapsible)
        emoji = "⚪" if frame == 0 else " "
        collapsible.title = f"🤖 ▷ 🤖 {self.agent_name} {emoji}"

    def watch_state(self, state: str) -> None:
        collapsible = self.query_one(Collapsible)

        if state == "completed":
            self._timer.stop()
            collapsible.title = f"🤖 ▷ 🤖 {self.agent_name} 🟢"
        elif state == "failed":
            self._timer.stop()
            collapsible.title = f"🤖 ▷ 🤖 {self.agent_name} 🔴"

    async def process(self, messages) -> None:
        async def do_process():
            try:
                await self.query_one(ChatView).process(messages)
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

    def __init__(self, id: str, name: str, emoji: str, arguments: dict):
        super().__init__(id=id)
        self.tool_name = name
        self.tool_emoji = emoji
        self.tool_args = arguments

    def compose(self) -> ComposeResult:
        with Collapsible(title=f"🤖 ▷ {self.tool_emoji} {self.tool_name} ⚪", collapsed=True):
            with TabbedContent("Arguments", "Result"):
                yield Markdown(f"""```json\n{json.dumps(self.tool_args, indent=2)}\n```""")
                yield AppendableMarkdown(content="")

    def on_mount(self) -> None:
        self.state = "waiting"
        self._timer = self.set_interval(0.5, self._blink)

    def _blink(self) -> None:
        if self.state == "waiting":
            if self.frame == 0:
                self.frame = 1
            else:
                self.frame = 0

    def watch_frame(self, frame):
        collapsible = self.query_one(Collapsible)
        emoji = "⚪" if frame == 0 else " "
        collapsible.title = f"🤖 ▷ {self.tool_emoji} {self.tool_name} {emoji}"

    def watch_state(self, state: str) -> None:
        collapsible = self.query_one(Collapsible)

        if state == "completed":
            self._timer.stop()
            collapsible.title = f"🤖 ▷ {self.tool_emoji} {self.tool_name} 🟢"
        elif state == "failed":
            self._timer.stop()
            collapsible.title = f"🤖 ▷ {self.tool_emoji} {self.tool_name} 🔴"

    def complete(self, failed: bool) -> None:
        self.state = "failed" if failed else "completed"

    async def append_result(self, chunk: str) -> None:
        if len(chunk) > 250:
            chunk = chunk[:250] + "\n...[omitted]"

        result = self.query_one(AppendableMarkdown)
        await result.append(chunk)

    async def append_json(self, chunk: JsonValue) -> None:
        result = self.query_one(AppendableMarkdown)
        await result.append(f"""```json\n{json.dumps(chunk, indent=2)}\n```""")


class AgentRedirectionWidget(AppendableMarkdown):
    def __init__(self, to_agent: str):
        super().__init__(content=f"🤖 ▷ 🤖 {to_agent}:\n")


class ChatView(VerticalScroll):
    def __init__(self, agent: Agent, id: str = None):
        super().__init__(id=id)
        self._agent = agent

    async def process(self, messages: AsyncIterable[Message]) -> None:
        async for message in messages:
            match message:
                case UserMessage():
                    pass

                case AssistantMessage(content=ContentStream() as stream):
                    assistant_widget = AssistantMessageWidget()
                    await self.mount(assistant_widget)

                    async def append_stream(stream: ContentStream):
                        async for chunk in stream:
                            await assistant_widget.append(chunk)

                    self.run_worker(append_stream(stream))

                case AssistantMessage(content=ToolRequest() as tool_request) if "_redirection" in tool_request.name:
                    tool_widget = CollapsibleChatView(
                        f"{tool_request.name}_{tool_request.id}",
                        tool_request.name,
                        tool_request.arguments,
                        self._agent
                    )

                    await self.mount(tool_widget)

                case AssistantMessage(content=ToolRequest() as tool_request):
                    tool = self._agent.tool_by_name(tool_request.name)
                    emoji = '🔧' if not tool else tool.emoji

                    tool_widget = ToolUseWidget(f"{tool_request.name}_{tool_request.id}", tool_request.name, emoji,
                                                tool_request.arguments)
                    await self.mount(tool_widget)

                case ToolMessage(content=ContentStream()) as tool_message if "_redirection" in tool_message.name:
                    widget = self.query_one(f"#{tool_message.name}_{tool_message.id}", CollapsibleChatView)
                    await widget.process(tool_message.content)

                case ToolMessage() as message:
                    async def process_result():
                        widget = self.query_one(f"#{message.name}_{message.id}", ToolUseWidget)

                        result = await message.content_as_json()
                        is_error = isinstance(message.content, ExecutionError)

                        if isinstance(result, str):
                            await widget.append_result(result)
                        else:
                            await widget.append_json(result)

                        widget.complete(is_error)

                    await process_result()


class ChatWidget(Container):
    def __init__(self, agent: Agent, logo: str, theme: str) -> None:
        super().__init__()
        self._agent = agent
        self._session = agent.stateful()
        self._logo = logo
        self.theme = theme

    def compose(self) -> ComposeResult:
        with ChatView(self._agent):
            from art import text2art
            yield Static(text2art(self._logo, font='tarty2'), id="chat-art")
        yield Input(placeholder="How can I help you?")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

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
        await chat_view.process(self._session(prompt))


class ChatApp(App):
    CSS = """
    MyApp {
        height: 100%;
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
    
    #chat-view {
      height: 1fr;
      overflow-y: auto;
      padding: 0;
      margin: 0;
    }
    
    ToolUseWidget > CollapsibleChatView {
        height: auto;
        border: solid red;
    }
    
      TabbedContent > ContentSwitcher {
          height: auto;
      }

  Collapsible {
      overflow-y: auto;
      max-height: 25;
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

        # Light Themes
        self.register_theme(Theme(
            name="aurora-mist",
            primary="#A8E6CF",
            secondary="#DCEDC2",
            accent="#FFD3B5",
            warning="#FFAAA6",
            error="#FF8C94",
            success="#4ECDC4",
            foreground="#2E2E2E",
            background="#FFFFFF",
            surface="#F0F0F0",
            panel="#E0E0E0",
            dark=False,
        ))

        self.register_theme(Theme(
            name="ivory-paper",
            primary="#F9F6EE",
            secondary="#EDE8D8",
            accent="#C4B59C",
            warning="#E0B080",
            error="#BA3C5B",
            success="#4EBF71",
            foreground="#2E2E2E",
            background="#FFF8E1",
            surface="#F6F2E4",
            panel="#F1ECD8",
            dark=False,
        ))

        self.register_theme(Theme(
            name="coastal-breeze",
            primary="#A2D5F2",
            secondary="#07689F",
            accent="#FFE1A8",
            warning="#F4A261",
            error="#E76F51",
            success="#2A9D8F",
            foreground="#2E2E2E",
            background="#EAF6F6",
            surface="#D9F1F1",
            panel="#C8EAEF",
            dark=False,
        ))

        self.register_theme(Theme(
            name="lemon-sorbet",
            primary="#FFF176",
            secondary="#FFEE58",
            accent="#FFF59D",
            warning="#FDD835",
            error="#E53946",
            success="#43A047",
            foreground="#2E2E2E",
            background="#FFFDE7",
            surface="#FFF9C4",
            panel="#FFF8E1",
            dark=False,
        ))

        self.register_theme(Theme(
            name="nordic-snow",
            primary="#ECEFF4",
            secondary="#E5E9F0",
            accent="#8FBCBB",
            warning="#EBCB8B",
            error="#BF616A",
            success="#A3BE8C",
            foreground="#2E3440",
            background="#ECEFF4",
            surface="#E5E9F0",
            panel="#D8DEE9",
            dark=False,
        ))

        self.register_theme(Theme(
            name="sunlit-garden",
            primary="#A8D5BA",
            secondary="#FFD8BE",
            accent="#FFAEBC",
            warning="#FF8B94",
            error="#FF5E5B",
            success="#8ACB88",
            foreground="#2E2E2E",
            background="#FCFAF8",
            surface="#F8F4F0",
            panel="#F4EFE9",
            dark=False,
        ))

        self.register_theme(Theme(
            name="peach-milk",
            primary="#FFDAB9",
            secondary="#FFEFD5",
            accent="#FFC8A2",
            warning="#FFA07A",
            error="#FF6F61",
            success="#AFD275",
            foreground="#2E2E2E",
            background="#FFF5E6",
            surface="#FFEFD9",
            panel="#FFEAD1",
            dark=False,
        ))

        self.register_theme(Theme(
            name="cotton-sky",
            primary="#E0ECFF",
            secondary="#BFD7FF",
            accent="#A6C8FF",
            warning="#FFEC99",
            error="#FFADAD",
            success="#C1E1C1",
            foreground="#2E2E2E",
            background="#F4FBFF",
            surface="#E8F7FF",
            panel="#DCF3FF",
            dark=False,
        ))

        self.register_theme(Theme(
            name="minimal-quartz",
            primary="#CCCCCC",
            secondary="#E0E0E0",
            accent="#B0B0B0",
            warning="#FFD54F",
            error="#E57373",
            success="#81C784",
            foreground="#2E2E2E",
            background="#F9F9F9",
            surface="#F0F0F0",
            panel="#E8E8E8",
            dark=False,
        ))

        self.register_theme(Theme(
            name="champagne-glow",
            primary="#F7E7CE",
            secondary="#FAF0E6",
            accent="#FAD6A5",
            warning="#FFD700",
            error="#E57373",
            success="#AED581",
            foreground="#2E2E2E",
            background="#FEF9EF",
            surface="#FEF5E7",
            panel="#FEEFE0",
            dark=False,
        ))

        # Dark Themes
        self.register_theme(Theme(
            name="obsidian-night",
            primary="#0D0D0D",
            secondary="#1A1A1A",
            accent="#BB86FC",
            warning="#FFAB00",
            error="#CF6679",
            success="#03DAC6",
            foreground="#E0E0E0",
            background="#0D0D0D",
            surface="#1C1C1C",
            panel="#272727",
            dark=True,
        ))

        self.register_theme(Theme(
            name="midnight-forest",
            primary="#0B3D0B",
            secondary="#1A5326",
            accent="#3B8D3B",
            warning="#FFB703",
            error="#D00000",
            success="#3A5F0B",
            foreground="#E0E0E0",
            background="#081008",
            surface="#102010",
            panel="#1A321A",
            dark=True,
        ))

        self.register_theme(Theme(
            name="neon-matrix",
            primary="#00FF00",
            secondary="#0AFF0A",
            accent="#39FF14",
            warning="#FFFF00",
            error="#FF0000",
            success="#00FF00",
            foreground="#00FF00",
            background="#000000",
            surface="#111111",
            panel="#222222",
            dark=True,
        ))

        self.register_theme(Theme(
            name="ashfall",
            primary="#2E2E2E",
            secondary="#4A4A4A",
            accent="#D1495B",
            warning="#F77F00",
            error="#D32F2F",
            success="#66BB6A",
            foreground="#E0E0E0",
            background="#212121",
            surface="#2E2E2E",
            panel="#3C3C3C",
            dark=True,
        ))

        self.register_theme(Theme(
            name="starfall-indigo",
            primary="#282C34",
            secondary="#3E4451",
            accent="#C678DD",
            warning="#E5C07B",
            error="#E06C75",
            success="#98C379",
            foreground="#ABB2BF",
            background="#1F2227",
            surface="#2C313C",
            panel="#3B3F4B",
            dark=True,
        ))

        self.register_theme(Theme(
            name="driftwood-smoke",
            primary="#3B3A36",
            secondary="#55534C",
            accent="#A8A798",
            warning="#CCB000",
            error="#A17C7C",
            success="#7A9C7C",
            foreground="#EDEDED",
            background="#2B2A26",
            surface="#3B3A36",
            panel="#4A4946",
            dark=True,
        ))

        self.register_theme(Theme(
            name="deep-space",
            primary="#0A0A23",
            secondary="#1A1A40",
            accent="#586BA4",
            warning="#FCD34D",
            error="#EF4444",
            success="#10B981",
            foreground="#E0E0E0",
            background="#000010",
            surface="#10001E",
            panel="#1A1A33",
            dark=True,
        ))

        self.register_theme(Theme(
            name="noir-film",
            primary="#1C1C1C",
            secondary="#2E2E2E",
            accent="#F0F0F0",
            warning="#B0B0B0",
            error="#FFFFFF",
            success="#A0A0A0",
            foreground="#FFFFFF",
            background="#000000",
            surface="#1F1F1F",
            panel="#2A2A2A",
            dark=True,
        ))

        self.register_theme(Theme(
            name="molten-core",
            primary="#382110",
            secondary="#4E2A0A",
            accent="#FF4500",
            warning="#FF8C00",
            error="#FF0000",
            success="#228B22",
            foreground="#EDEDED",
            background="#1F1309",
            surface="#2C1E13",
            panel="#392C1D",
            dark=True,
        ))

        self.register_theme(Theme(
            name="cyber-eclipse",
            primary="#2E003E",
            secondary="#5700A5",
            accent="#FF00FF",
            warning="#FF0099",
            error="#FF0066",
            success="#00FFAA",
            foreground="#F0F0F0",
            background="#1A001A",
            surface="#2E002E",
            panel="#3F003F",
            dark=True,
        ))

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
        await chat_view.process(self._session(prompt))

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
