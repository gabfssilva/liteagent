from crawl4ai import AsyncWebCrawler

from liteagent import tool


@tool
async def crawl4ai(
    url: str
) -> str:
    """
    This tool craws information from the provided website and responds as markdown.
    """

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url, verbose=False)
        return result.markdown
