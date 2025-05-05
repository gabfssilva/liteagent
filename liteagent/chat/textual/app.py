"""Textual app for the chat interface."""

from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Input, Static

from liteagent import Agent
from liteagent.chat.textual.widgets import *


class ChatApp(App):
    """Main chat application for the Textual interface."""

    CSS = """
    MyApp {
        height: 100%;
    }
    
    Tooltip {
        background: $background;
        color: auto 90%;
        border: round $primary;
    }
    
    ReactiveMarkdown > Markdown {
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
    
    UserMessageWidget > ReactiveMarkdown > Markdown {
        color: $foreground-darken-3;
    } 
    
    AssistantMessageWidget > ReactiveMarkdown > Markdown {
        color: $foreground-lighten-3;
    }
    
    .user-message {
        margin: 0 0 1 10;
        align: left middle;
        border: panel $secondary;
        background: $background;
        padding: 1;
        border-title-align: left;
        border-subtitle-align: right;
        border-bottom: panel $secondary;
        border-right: panel $secondary;
        border-left: panel $secondary;
        border-subtitle-background: $secondary;
        border-subtitle-color: $background;
    }

    .assistant-message {
        margin: 0 10 1 0;
        align: right middle;
        border: panel $secondary;
        background: $background;
        padding: 1 1 1 1;
        color: $foreground-darken-3;
        border-title-align: left;
        border-subtitle-align: right;
        border-bottom: panel $secondary;
        border-right: panel $secondary;
        border-left: panel $secondary;
        border-subtitle-background: $secondary;
        border-subtitle-color: $background;
    }
    
    .assistant-message-inner {
        margin: 0 0 1 0;
        align: left middle;
        border: panel $secondary;
        background: $background;
        padding: 1 1 1 1;
        border-title-align: left;
        border-subtitle-align: right;
        border-bottom: panel $secondary;
        border-right: panel $secondary;
        border-left: panel $secondary;
        border-subtitle-background: $secondary;
        border-subtitle-color: $background;
    }

    .tool-message {
        margin: 0 10 1 0;
        align: right middle;
        padding: 1 1 1 1;
        border: panel $accent;
        background: $background;
        border-title-align: left;
        border-subtitle-align: right;
        border-bottom: panel $accent;
        border-right: panel $accent;
        border-left: panel $accent;
        border-subtitle-background: $accent;
        border-subtitle-color: $background;
    }
    
    .tool-message-inner {
        margin: 0 0 1 0;
        padding: 1 1 1 1;
        align: left middle;
        border: panel $accent;
        background: $background;
        border-title-align: left;
        border-subtitle-align: right;
        border-subtitle-align: right;
        border-bottom: panel $accent;
        border-right: panel $accent;
        border-left: panel $accent;
        border-subtitle-background: $accent;
        border-subtitle-color: $background;
    }
 
    .internal-chat-view {
        align: left middle;
    }
    
    InternalChatView {
        overflow-y: auto;
        max-height: 20;
        background: $background;
        padding: 0;
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
