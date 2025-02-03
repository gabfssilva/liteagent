import asyncio

from docutils.nodes import description

from liteagent import Agent, agent, team
from liteagent.providers import openai
from liteagent.tools import wikipedia, py


@agent(
    name="Wikipedia Searcher",
    tools=[wikipedia.search, wikipedia.get_complete_article],
    provider=openai(model='o3-mini'),
    description="""
        An agent specialized in searching the wikipedia.
        **ALWAYS** use your tools to fetch the requested information
    """,
)
def wikipedia_agent() -> str: ...


@team(
    name="Searcher",
    agents=[wikipedia_agent],
    tools=[py.python_runner],
    provider=openai(model='gpt-4o'),
    description="An agent specialized in searching the web"
)
def searcher() -> str: ...


async def main():
    await searcher(
        """
        Use your tools and agents for this:

        Provide a table for me containing how long 5 the fastest animals in the world would take to cross the 5 longgest bridges in the world.
        Use meters and minutes as units. Be aware of the units while extracting the values, as you may get the wrong ones.
        To avoid this, extract all units when available and, based on the content of each value, extract the correct unit. Once again, be careful while extracting.
        Meters are smaller than feet, which are smaller than kilimeters, which are smaller than miles. You get the idea.
        """
    )


if __name__ == '__main__':
    asyncio.run(main())
