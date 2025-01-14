from liteagents import Agent, tools, auditors, providers
from liteagents.tools import websearch, wikipedia, py

wikipedia_agent = Agent(
    name="Wikipedia Agent",
    description="An agent specialized in searching the wikipedia",
    provider=providers.openai(),
    tools=[
        wikipedia.search,
        wikipedia.get_complete_article
    ],
    # intercept=auditors.console()
)

agent = Agent(
    name="Web Searcher",
    description="An agent specialized in searching the web",
    provider=providers.openai(),
    tools=[py.evaluate],
    intercept=auditors.console(),
    team=[wikipedia_agent]
)

*_, _ = agent.sync(
    """
    How long would it take for the fastest animal in the world to cross the biggest bridge in the world?
    """
)
