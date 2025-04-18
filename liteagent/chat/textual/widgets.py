"""Widget components for the Textual UI."""
import json

import rich.markdown
from pydantic import BaseModel
from rich.syntax import Syntax
from textual.containers import VerticalScroll, Grid, Horizontal
from textual.widgets import Collapsible, Static, Button, Pretty, ContentSwitcher, Markdown

from ...message import MessageContent, ImageURL, ImageBase64
from ...tools.py import PythonScriptResult


class ToolCallWidget(Static):
    """Widget to display tool calls and their results."""

    _frames = ["🕛", "🕐", "🕑", "🕒", "🕓", "🕔", "🕕", "🕖", "🕗", "🕘", "🕙", "🕚"]

    def __init__(self, *, emoji: str, name: str, args: dict, theme: str = "nord"):
        super().__init__()
        self._name = name
        self._emoji = emoji
        self._args = args
        self._frame = 0
        self._spinner_running = True
        self._collapsible = None
        self._theme = theme

    def compose(self):
        with Collapsible(title=self.make_title(), collapsed=True, id='tool-use'):
            with Grid(id="tool-grid"):
                with Horizontal(id="tool-tab-buttons"):
                    yield Button("Args", id="first-tab", variant="primary")
                    yield Button("Result", id="second-tab", variant="default")

                with ContentSwitcher(id="tool-content-switcher", initial="args-content"):
                    with VerticalScroll(id="args-content"):
                        # Arguments will be added here
                        args_widget = Static()
                        if isinstance(self._args, (dict, list)):
                            json_str = json.dumps(self._args, indent=2, ensure_ascii=False)
                            args_widget.update(Syntax(json_str, "json", theme=self._theme, word_wrap=True))
                        else:
                            args_widget.update(str(self._args))
                        yield args_widget
                    with VerticalScroll(id="result-content"):
                        # Result will be added here later
                        pass

        self.set_interval(0.05, self._next_frame)

    def on_mount(self):
        self._collapsible = self.query_one('#tool-use', Collapsible)
        self._first_tab = self.query_one("#first-tab", Button)
        self._second_tab = self.query_one("#second-tab", Button)
        self._content_switcher = self.query_one("#tool-content-switcher", ContentSwitcher)
        self._args_content = self.query_one("#args-content", VerticalScroll)
        self._result_content = self.query_one("#result-content", VerticalScroll)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "first-tab":
            self._first_tab.variant = "primary"
            self._second_tab.variant = "default"
            self._content_switcher.current = "args-content"
        elif button_id == "second-tab":
            self._first_tab.variant = "default"
            self._second_tab.variant = "primary"
            self._content_switcher.current = "result-content"

    def make_title(self) -> str:
        spinner_char = self._frames[self._frame] if self._spinner_running else "✅"
        return f"{spinner_char} 🤖 ▷ {self._emoji} {self._name}"

    def _next_frame(self) -> None:
        if self._spinner_running and self._collapsible:
            self._frame = (self._frame + 1) % len(self._frames)
            self._collapsible.title = self.make_title()

    async def set_response(self, content: MessageContent):
        self._spinner_running = False
        self._collapsible.title = self.make_title()

        # Automatically switch to result tab when result arrives
        self._first_tab.variant = "default"
        self._second_tab.variant = "primary"
        self._content_switcher.current = "result-content"

        result_widget = Static()

        match content:
            case BaseModel():
                json_str = json.dumps(content.model_dump(), indent=2, ensure_ascii=False)
                result_widget.update(Syntax(json_str, "json", theme=self._theme, word_wrap=True))

            case dict() | list():
                json_str = json.dumps(content, indent=2, ensure_ascii=False)
                result_widget.update(Syntax(json_str, "json", theme=self._theme, word_wrap=True))

            case str() as raw_str:
                try:
                    parsed = json.loads(raw_str)
                    json_str = json.dumps(parsed, indent=2, ensure_ascii=False)
                    result_widget.update(Syntax(json_str, "json", theme=self._theme, word_wrap=True))
                except Exception:
                    result_widget.update(rich.markdown.Markdown(raw_str))

            case ImageURL(url=url):
                result_widget.update(f"[Image URL]\n{url}")

            case ImageBase64():
                result_widget.update("[Image] base64 content received.")

            case _:
                result_widget.update(str(content))

        await self._result_content.mount(result_widget)


class PythonRunnerWidget(ToolCallWidget):
    """Widget specifically for Python runner tool calls."""
    
    def compose(self):
        with Collapsible(title=self.make_title(), collapsed=True, id='tool-use'):
            with Grid(id="py-runner-grid"):
                with Horizontal(id="tab-buttons"):
                    yield Button("Code", id="first-tab", variant="primary")
                    yield Button("Result", id="second-tab", variant="default")

                with ContentSwitcher(id="tool-content-switcher", initial="args-content"):
                    with VerticalScroll(id="args-content"):
                        pass
                    with VerticalScroll(id="result-content"):
                        pass

        self.set_interval(0.05, self._next_frame)

    def on_mount(self):
        self._collapsible = self.query_one('#tool-use', Collapsible)
        self._first_tab = self.query_one("#first-tab", Button)
        self._second_tab = self.query_one("#second-tab", Button)
        self._content_switcher = self.query_one("#tool-content-switcher", ContentSwitcher)
        self._args_content = self.query_one("#args-content", VerticalScroll)
        self._result_content = self.query_one("#result-content", VerticalScroll)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "first-tab":
            self._first_tab.variant = "primary"
            self._second_tab.variant = "default"
            self._content_switcher.current = "args-content"
        elif button_id == "second-tab":
            self._first_tab.variant = "default"
            self._second_tab.variant = "primary"
            self._content_switcher.current = "result-content"

    def make_title(self) -> str:
        spinner_char = self._frames[self._frame] if self._spinner_running else "✅"
        return f"{spinner_char} 🤖 ▷ 🐍 Python Runner"

    async def set_response(self, content: MessageContent):
        self._spinner_running = False
        self._collapsible.title = self.make_title()

        self._first_tab.variant = "default"
        self._second_tab.variant = "primary"
        self._content_switcher.current = "result-content"

        match content:
            case PythonScriptResult(script=script, result=result):
                await self._args_content.mount(Markdown(f"""```python\n{script}\n```"""))

                match result:
                    case str():
                        await self._result_content.mount(Static(result))
                    case _:
                        await self._result_content.mount(Pretty(result))
            case _:
                await super().set_response(content)