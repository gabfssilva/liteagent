import asyncio

from liteagent import Agent, agent, team
from liteagent.providers import openai
from liteagent.tools import wikipedia, python_runner


@agent(
    tools=[wikipedia.search, wikipedia.get_complete_article],
    provider=openai(model='gpt-4o-mini'),
    description="""
        An agent specialized in searching the wikipedia.
        **ALWAYS** use your tools to fetch the requested information
    """,
)
def wikipedia_agent(query: str) -> str:
    """ Here's your query: {query} """


@agent(
    tools=[python_runner],
    provider=openai(model='gpt-4o-mini'),
    description="An agent specialized in running python code.",
)
def code_runner(query: str) -> str:
    """ Here's your query: {query} """


@agent(
    team=[wikipedia_agent, code_runner],
    provider=openai(model='gpt-4o'),
    description="An agent specialized in searching the web"
)
def searcher() -> str:
    """
    Generate a table showing how long the **five fastest animals in the world** would take to cross the **five longest bridges in the world**.

    **Requirements:**
    - Use **meters (m) for distance** and **minutes (min) for time**.
    - When extracting values, **identify and convert all units correctly** to prevent errors.
      - **Units hierarchy for reference:**
        - **Meters (m) < Feet (ft) < Kilometers (km) < Miles (mi)**
      - Ensure all extracted values are in **consistent units** before calculations.
    - Use the `code_runner` tool for any necessary calculations.
    """

if __name__ == '__main__':
    asyncio.run(searcher())
