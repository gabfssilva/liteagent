"""Style definitions for the Textual UI."""
from textual.theme import Theme

light_theme = Theme(
    name="light",
    primary="#004578",
    secondary="#0178D4",
    accent="#ffa62b",
    warning="#ffa62b",
    error="#ba3c5b",
    success="#4EBF71",
    surface="#D8D8D8",
    panel="#D0D0D0",
    background="#FFFFFF",
    dark=False,
    variables={
        "footer-key-foreground": "#0178D4",
    },
)

CHAT_CSS = """
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

Screen {
    layout: vertical;
    background: $background;
}

ToolCallWidget, PythonRunnerWidget {
    padding: 0 0 -1 0;
    background: $background;
}

ToolCallWidget > .tool-use, PythonRunnerWidget > .tool-use {
    layout: grid;
    grid-size: 2 1;
    grid-columns: 2% 98%;
    height: auto;
    background: $background;
}

#app {
    grid-size: 1 2;
    grid-rows: 90% auto;
    # padding: 0 0 0 0;
}

ToolCallWidget VerticalScroll, PythonRunnerWidget VerticalScroll {
    max-height: 10;
    height: auto;
    overflow-y: auto;
    # border: round $primary;
    padding: 0 2 -1 2;
    width: 100%;
    margin-top: 0;
    background: $background;
}

ToolCallWidget #tool-use, PythonRunnerWidget #tool-use {
    background: $background;
}

ToolCallWidget VerticalScroll, PythonRunnerWidget VerticalScroll {
    max-height: 20; /* More space for tool content */
}

ToolCallWidget Static, PythonRunnerWidget Static {
    margin: 1 0;
    padding: 0;
}

#tool-grid, #py-runner-grid {
    layout: grid;
    grid-size: 1 2;
    grid-rows: auto 1fr;
    height: auto;
    background: $background;
}

#tool-tab-buttons, #tab-buttons {
    width: 100%;
    height: auto;
    align: center top;
    background: $background;
    padding: 1 0;
}

#tool-tab-buttons Button, #tab-buttons Button {
    margin: 0 1;
    padding: 1 3;
    min-width: 6;
    width: 50%;
}

#tool-content-switcher {
    width: 100%;
    height: auto;
}

.chat-title {
    content-align: center middle;
    background: $background;
    text-style: bold;
}

#chat-container {
    padding: 0;
    overflow-y: auto;
    background: $background;
    margin: 0;
}

#message-input {
    background: $background;
    border: round $primary;
    align: left bottom;
    padding: 0;
}

.chat-box {
    height: auto;
    padding: 1 2 -1 2;
    layout: vertical;
    background: $background;
    overflow-y: auto;

    &:focus {
        background-tint: $foreground 5%;
    }
}

#tool-use {
    background: $background;
}

#chat-art {
    content-align: center middle;
}
"""