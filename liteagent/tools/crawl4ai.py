from liteagent import tool
from liteagent.internal import depends_on


@tool(emoji='🔎')
@depends_on({"crawl4ai": "crawl4ai"})
async def crawl4ai(
    url: str
) -> str:
    """ this tool craws information from the provided website and responds as markdown. """
    from crawl4ai import BrowserConfig
    from crawl4ai import AsyncWebCrawler

    config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        verbose=False
    )

    async with AsyncWebCrawler(config=config) as crawler:
        result = await crawler.arun(url=url)
        return result.markdown
