import httpx
from pydantic import Field

from bs4 import BeautifulSoup  # For parsing HTML
from markdownify import markdownify as md  # For converting HTML to Markdown
from liteagents import tool


@tool
async def search(
    query: str = Field(..., description="The search term."),
    limit: int = Field(5, description="Number of results to fetch (default is 5).")
) -> list[dict]:
    """Searches Wikipedia for a query and returns summaries of matching articles."""
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


@tool
async def get_complete_article(url: str = Field(..., description="The URL of the page")):
    """Fetches only the content body of a Wikipedia article as Markdown."""

    if not url.startswith("https://en.wikipedia.org/wiki/"):
        raise Exception("URL isn't from a Wikipedia page")

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        html_content = response.text

        soup = BeautifulSoup(html_content, 'html.parser')

        content_div = soup.find('div', id='bodyContent')

        if not content_div:
            raise Exception("Failed to locate the content body in the article")

        markdown_content = md(str(content_div), heading_style="ATX")
        return markdown_content
