import asyncio

from liteagent import reasoning, Agent, auditors
from liteagent.providers import openai

agent = reasoning.chain_of_thought(
    provider=openai(),
    description="**ALWAYS** redirect to the criticizer agent before your final answer",
    agents=[
        Agent(
            name="Criticizer",
            provider=openai(),
            description="You are a Criticizer. You receive a chain of thought and find what's wrong with it, answering back the correct answer to the coordinator, if the coordinator is wrong.",
            intercept=auditors.console()
        )
    ]
)


async def main():
    await agent("Alice has four sisters and a brother, Bob. How many sisters does Bob have?")


if __name__ == '__main__':
    asyncio.run(main())
