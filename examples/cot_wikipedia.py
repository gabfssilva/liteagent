import asyncio

from liteagent import Agent, tools, auditors, providers, reasoning
from liteagent.tools import wikipedia, py

agent = reasoning.chain_of_thought(
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
        ),
        Agent(
            name="Calculator",
            description="An agent specialized in doing math",
            provider=providers.openai(),
            tools=[py.python_runner],
            intercept=auditors.console()
        )
    ]
)


async def main():
    await agent(
        """What's the fastest animal on earth? How long it would take cross the biggest bridge in the world?"""
    )


if __name__ == '__main__':
    asyncio.run(main())
