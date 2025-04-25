import asyncio
from typing import List

from textual.widget import Widget
from textual_plotext import PlotextPlot

from liteagent import tool


class StackedBarPlot(Widget):
    can_focus = False
    can_focus_children = False
    disabled = True

    def __init__(
        self,
        title: str,
        x_axis_labels: List[str],
        series_names: List[str],
        series_values: List[List[float]],
        *children: Widget
    ):
        super().__init__(*children)
        self.title = title
        self.x_axis_labels = x_axis_labels
        self.series_names = series_names
        self.series_values = series_values

    async def __json__(self):
        return f"StackedBarPlot(title={self.title})"

    def compose(self):
        yield PlotextPlot(disabled=True)

    def on_mount(self):
        plot = self.query_one(PlotextPlot)

        plot.auto_refresh = False
        plot.disabled = True
        plot.can_focus = False
        plot.can_focus_children = False

        plt = plot.plt
        plt.stacked_bar(
            self.x_axis_labels,
            self.series_values,
            labels=self.series_names
        )

        plt.title(self.title)

@tool(emoji='📊')
def plot_stacked_bar(
    title: str,
    x_axis_labels: List[str],
    series_names: List[str],
    series_values: List[List[float]]
) -> Widget:
    return StackedBarPlot(title, x_axis_labels, series_names, series_values)
