"""Widget renderer for displaying tool content in the chat interface."""

from textual.widget import Widget
from textual.content import Content

from liteagent import AssistantMessage, ToolMessage


class WidgetRenderer(Widget):
    """Widget that renders custom tool outputs."""
    
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