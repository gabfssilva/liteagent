import asyncio

from liteagent import agent
from liteagent.providers import openai
from liteagent.tools import duckduckgo, crawl4ai, clock


@agent(
    tools=[clock, duckduckgo, crawl4ai],
    provider=openai(model='gpt-4o')
)
async def news(country: str) -> str:
    """
    What did happen in the past week in {country}?
    Search for the news and, based on that, I want you to select by yourself the most interesting ones.
    Once you get these, get more details about each and provide your own take on each.
    Use a critical tone.
    """

asyncio.run(news(country='USA'))
