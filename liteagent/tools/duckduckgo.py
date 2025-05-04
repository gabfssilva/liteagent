from typing import Literal, TYPE_CHECKING

from liteagent.internal import depends_on

if TYPE_CHECKING:
    from duckduckgo_search import DDGS

from pydantic import Field

from liteagent import tool, Tools


class DuckDuckGo(Tools):
    def __init__(self, client: 'DDGS' = None):
        from duckduckgo_search import DDGS

        self.client = client or DDGS()

    @tool(emoji='🔎')
    def search(
        self,
        keywords: str,
        region: str | None,
        safesearch: Literal['on', 'moderate', 'off'],
        timelimit: str | None,
        backend: Literal['auto', 'html', 'lite'],
        max_results: int | None = Field(..., description="Number of results. Defaults to 100."),
    ):
        """ search for information on the internet using DuckDuckGo. """

        return self.client.text(
            keywords,
            region or "wt-wt",
            safesearch,
            timelimit,
            backend,
            max_results or 100
        )


@depends_on({"duckduckgo_search": "duckduckgo-search"})
def duckduckgo(client: 'DDGS' = None) -> DuckDuckGo:
    return DuckDuckGo(client=client)
