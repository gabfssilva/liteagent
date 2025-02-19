from crawl4ai import AsyncWebCrawler, BrowserConfig

from liteagent import tool


@tool(emoji='🔎')
async def crawl4ai(
    url: str
) -> str:
    """ this tool craws information from the provided website and responds as markdown. """

    config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        verbose=False
    )

    async with AsyncWebCrawler(config=config) as crawler:
        result = await crawler.arun(url=url, verbose=False)
        return result.markdown
