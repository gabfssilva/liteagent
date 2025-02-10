import asyncio

from liteagent import agent
from liteagent.providers import openai
from liteagent.tools import duckduckgo, crawl4ai


@agent(
    tools=[duckduckgo, crawl4ai],
    provider=openai(model='gpt-4o-mini')
)
async def news(year: int, country: str) -> str:
    """
    It's {year}. What's currently happening in {country}?
    Search for the news and, based on that, I want you to select by yourself the most interesting ones.
    Once you get these, get more details about each and provide your own take on each.
    Use a critial tone.
    """


asyncio.run(news(year=2025, country='USA'))
