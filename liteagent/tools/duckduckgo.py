from typing import Literal

from duckduckgo_search import DDGS
from pydantic import JsonValue

from liteagent import tool


@tool
def duckduckgo(
    keywords: str,
    region: str | None,
    safesearch: Literal['on', 'moderate', 'off'],
    timelimit: str | None,
    backend: Literal['auto', 'html', 'lite'],
    max_results: int | None,
) -> JsonValue:
    """ Use this tool for searching the internet. """

    return DDGS().text(
        keywords,
        region or "wt-wt",
        safesearch,
        timelimit,
        backend,
        max_results or 10
    )
