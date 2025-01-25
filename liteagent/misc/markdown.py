from typing import Iterator, List
from rich.console import Console, RenderableType
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text
import re

# Mapping of markdown delimiters to Rich styles
inline_styles = {
    "**": "bold",
    "*": "italic",
    "~~": "strike",
}

# Dynamically build the regex pattern from the delimiters
delimiters = "|".join(re.escape(k) for k in inline_styles.keys())
inline_pattern = re.compile(rf"({delimiters})(.+?)\1")


# Tokenizer Function
def tokenize_inline(text: str) -> List[Text]:
    elements = []
    remaining = text

    while remaining:
        match = inline_pattern.search(remaining)
        if match:
            start, end = match.span()
            # Add plain text before the match
            if start > 0:
                elements.append(Text(remaining[:start]))

            # Add styled text
            style = inline_styles[match.group(1)]
            elements.append(Text(match.group(2), style=style))

            # Move past the match
            remaining = remaining[end:]
        else:
            # Add any remaining plain text
            elements.append(Text(remaining))
            break

    return elements


# Renderer Function
def render_inline(elements: List[Text]) -> Text:
    inline_buffer = Text()
    for element in elements:
        inline_buffer.append(element)
    return inline_buffer


# Markdown Parser
def parse(input: Iterator[str]) -> Iterator[RenderableType]:
    inside_code_block = False
    code_language = None
    code_lines = []

    for token in input:
        # Handle code block markers (```language)
        if token.strip().startswith("```"):
            if not inside_code_block:
                inside_code_block = True
                code_language = token.strip()[3:].strip() or "text"
                code_lines = []
            else:
                inside_code_block = False
                joined = "\n".join(filter(lambda s: s != "", code_lines))
                yield Syntax(joined, code_language, theme="ancii-light", line_numbers=False)
            continue

        if inside_code_block:
            code_lines.append(token.rstrip("\n"))
            continue

        # Handle headings
        if token.startswith("#"):
            level = len(token.split(" ")[0])
            content = token[level:].strip()
            color = ["yellow", "cyan", "magenta", "green", "blue", "white"]
            yield Text(content, style=f"bold {color[level - 1]}")
            continue

        # Handle list items
        if token.strip().startswith(("- ", "* ", "1. ")):
            yield Text(f"• {token[2:].strip()}")
            continue

        # Handle inline styles
        inline_elements = tokenize_inline(token)
        yield render_inline(inline_elements)
