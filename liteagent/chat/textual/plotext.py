import asyncio
from typing import List

from textual.widget import Widget
from textual_plotext import PlotextPlot

from liteagent import tool


class StackedBarPlot(PlotextPlot):
    def __init__(
        self,
        title: str,
        x_axis_labels: List[str],
        series_names: List[str],
        series_values: List[List[float]],
    ):
        super().__init__()
        self.plt.title(title)
        self.x_axis_labels = x_axis_labels
        self.series_names = series_names
        self.series_values = series_values

    async def __json__(self): return f"successfully plotted"

    def on_mount(self):
        self.plt.stacked_bar(
            self.x_axis_labels,
            self.series_values,
            labels=self.series_names
        )

@tool(emoji='📊')
def plot_stacked_bar(
    title: str,
    x_axis_labels: List[str],
    series_names: List[str],
    series_values: List[List[float]]
) -> Widget:
    return StackedBarPlot(title, x_axis_labels, series_names, series_values)
