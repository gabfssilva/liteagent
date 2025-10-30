"""
Example 01: Hello World - The Simplest Agent

This example demonstrates:
- Creating a basic agent with @agent decorator
- Using a provider (OpenAI)
- Simple prompt template
- Basic async execution

Concepts introduced:
- @agent decorator
- Provider configuration
- Prompt templates
- asyncio.run()

Run: uv run python examples/01_hello_world.py
"""

import asyncio

from liteagent import agent
from liteagent.providers import openai


@agent(provider=openai(model="gpt-4o-mini"))
async def hello_agent() -> str:
    """
    You are a helpful AI assistant.

    Explain what LiteAgent is in one paragraph.
    """


async def main():
    result = await hello_agent()
    # Extract text from AssistantMessage
    if hasattr(result, 'content') and hasattr(result.content, 'await_complete'):
        text = await result.content.await_complete()
        print(text)
    else:
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
