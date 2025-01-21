import asyncio

from liteagents.providers import ollama
from liteagents.agent_decorator import agent


@agent(provider=ollama(model='vanilj/phi-4-unsloth:latest'))
def hello_agent():
    """ You are pretty good saying hello. You always come up with the most creative and unique greetings that any person can think """


async def main():
    await hello_agent.run("Hi, my name is Gabriel!")


if __name__ == '__main__':
    asyncio.run(main())
