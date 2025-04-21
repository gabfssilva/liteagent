import asyncio

import httpx
from pydantic import Field

from liteagent import tool


@tool(name="wikipedia_search", emoji='🔎')
async def search(
    query: str = Field(..., description="The search term."),
    limit: int = Field(..., description="Number of results to fetch.")
) -> list[dict]:
    """ Searches Wikipedia for a query and returns summaries of matching articles. """
    url = f"https://en.wikipedia.org/w/rest.php/v1/search/page?q={query}&limit={limit}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        pages = data.get("pages", [])

        return list(map(lambda page: dict(
            title=page["title"],
            description=page.get("description", "No description available"),
            url=f"https://en.wikipedia.org/wiki/{page['title'].replace(' ', '_')}"
        ), pages))


@tool(name="wikipedia_get_complete_article", emoji='📄')
async def get_complete_article(url: str = Field(..., description="The URL of the page")):
    """ Fetches only the content body of a Wikipedia article as Markdown. """
    from bs4 import BeautifulSoup
    from markdownify import markdownify as md

    if not url.startswith("https://en.wikipedia.org/wiki/"):
        raise Exception("URL isn't from a Wikipedia page")

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()

        def find_content(html_content: str):
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.find('div', id='bodyContent')

        content_div = await asyncio.to_thread(find_content, response.text)

        if not content_div:
            raise Exception("Failed to locate the content body in the article")

        return await asyncio.to_thread(md, str(content_div), **dict(heading_style="ATX"))
