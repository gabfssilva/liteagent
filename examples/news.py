import asyncio

from liteagent import agent
from liteagent.providers import google
from liteagent.tools import duckduckgo, clock, browser


@agent(
    tools=[clock, duckduckgo, browser],
    provider=google()
)
async def news(country: str) -> str:
    """
    What did happen in the past week in {country}?
    Search for the news and, based on that, I want you to select by yourself the most interesting ones.
    Once you get these, get more details about each and provide your own take on each.
    Use browser.
    Use a critical tone.
    """


if __name__ == "__main__":
    print(asyncio.run(news(country='USA')))
