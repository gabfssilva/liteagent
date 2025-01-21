import asyncio

from liteagents import Agent
from liteagents.agent_decorator import agent, team
from liteagents.providers import deepseek, openai, ollama
from liteagents.tools import wikipedia, py


@agent(
    name="Wikipedia Searcher",
    tools=[wikipedia.search, wikipedia.get_complete_article],
    provider=openai()
    # provider=ollama(model='qwen2.5-coder:7b')
)
def wikipedia_agent() -> Agent:
    """
    An agent specialized in searching the wikipedia.
    **ALWAYS** use your tools to fetch the requested information
    """

    ...


@team(
    name="Searcher",
    team=[wikipedia_agent],
    tools=[py.runner],
    provider=openai()
    # provider=ollama(model='qwen2.5-coder:7b')
)
def searcher() -> Agent:
    """ An agent specialized in searching the web """
    ...


async def main():
    await searcher(
        """
        Provide a table for me containing how long 5 the fastest animals in the world would take to cross the 5 longgest bridges in the world.
        Use meters and minutes as units. Be aware of the units while extracting the values, as you may get the wrong ones.
        To avoid this, extract all units when available and, based on the content of each value, extract the correct unit. Once again, be careful while extracting.
        Meters are smaller than feet, which are smaller than kilimeters, which are smaller than miles. You get the idea.
        """
    )


if __name__ == '__main__':
    asyncio.run(main())
