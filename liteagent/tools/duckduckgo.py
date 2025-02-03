from duckduckgo_search import DDGS
from pydantic import JsonValue

from liteagent import tool


@tool
def duckduckgo(
    keywords: str,
    region: str | None,
    safesearch: str | None,
    timelimit: str | None,
    backend: str | None,
    max_results: int | None,
) -> JsonValue:
    """ Use this tool for searching the internet. """

    return DDGS().text(
        keywords,
        region or "wt-wt",
        safesearch or "moderate",
        timelimit,
        backend or "auto",
        max_results or 10
    )
