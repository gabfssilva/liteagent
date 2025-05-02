from typing import List

from textual.widget import Widget
from textual.widgets import DataTable

from liteagent import tool

class Table(Widget):
    def __init__(self, headers: List[str], values: List[List[str | float | int | bool | None]]):
        super().__init__()
        self.headers = headers
        self.values = values

    def compose(self):
        yield DataTable()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = 'cell'
        table.zebra_stripes = True
        table.add_columns(*self.headers)
        table.add_rows(self.values)

    async def __json__(self): return f"successfully plotted"

@tool(emoji="📊")
def plot_table(headers: List[str], values: List[List[str | float | int | bool | None]]) -> Widget:
    """ plots a Textual DataTable for the user """

    return Table(headers, values)
