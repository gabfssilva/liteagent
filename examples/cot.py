from liteagents import Agent, tools, auditors, providers, reasoning
from liteagents.tools import wikipedia, py

agent = reasoning.chain_of_thought(
    tools=[py.evaluate],
    agents=[
        Agent(
            name="Web Searcher",
            description="An agent specialized in searching the web",
            provider=providers.openai(),
            tools=[
                wikipedia.search,
                wikipedia.get_complete_article
            ],
            intercept=auditors.console()
        )
    ]
)

*_, _ = agent.sync(
    """What's the fastest animal on earth? How long it would take cross the biggest bridge in the world?"""
)
