import asyncio

from liteagent import agent, bus
from liteagent.events import ToolExecutionCompleteEvent
from liteagent.providers import openai
from liteagent.tools import wikipedia, python_runner


@agent(
    tools=[wikipedia.search, wikipedia.get_complete_article],
    provider=openai(model='gpt-4.1-mini'),
    description="""
        An agent specialized in searching the wikipedia.
        **ALWAYS** use your tools to fetch the requested information
    """,
)
def wikipedia_agent(query: str) -> str:
    """ Here's your query: {query} """


@agent(
    tools=[python_runner],
    provider=openai(model='gpt-4.1-mini'),
    description="An agent specialized in running python code.",
)
def code_runner(query: str) -> str:
    """ Here's your query: {query} """


@agent(
    team=[wikipedia_agent, code_runner],
    provider=openai(model='gpt-4o'))
def searcher() -> str:
    """
    Generate a table showing how long the **five fastest animals in the world** would take to cross the **five longest bridges in the world**.

    **Requirements:**
    - Use **meters (m) for distance** and **minutes (min) for time**.
    - When extracting values, **identify and convert all units correctly** to prevent errors.
    - **Units hierarchy for reference:**
    - **Meters (m) < Feet (ft) < Kilometers (km) < Miles (mi)**
    - Ensure all extracted values are in **consistent units** before calculations.


    **DO NOT FORGET:** At the end, redirect to `code_runner` to make your calculations as precise as possible.
    USE CODE RUNNER!!!!!!!!
    """


@bus.on(ToolExecutionCompleteEvent)
async def on_message(msg: ToolExecutionCompleteEvent):
    print(msg)


if __name__ == '__main__':
    print(asyncio.run(searcher()))