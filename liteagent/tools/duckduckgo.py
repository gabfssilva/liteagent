from typing import Literal

from pydantic import Field

from liteagent import tool
from liteagent.internal import depends_on


@tool(emoji='🔎')
@depends_on({
    "duckduckgo_search": "duckduckgo-search"
})
def duckduckgo(
    keywords: str,
    region: str | None,
    safesearch: Literal['on', 'moderate', 'off'],
    timelimit: str | None,
    backend: Literal['auto', 'html', 'lite'],
    max_results: int | None = Field(...,
                                    description="The maximum number of results to return. Defaults to 100. Recommended >= 50 and <= 250"),
):
    """ search for information on the internet using DuckDuckGo. """

    from duckduckgo_search import DDGS

    return DDGS().text(
        keywords,
        region or "wt-wt",
        safesearch,
        timelimit,
        backend,
        max_results or 100
    )
