"""Reactive markdown widget that updates content in real-time."""

import asyncio

from textual.widgets import Markdown, Static
from textual.app import ComposeResult
from textual.markup import MarkupError


class ReactiveMarkdown(Static):
    """A markdown widget that automatically updates its content."""

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
                    chat_view = self.query_ancestor("ChatView")
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
