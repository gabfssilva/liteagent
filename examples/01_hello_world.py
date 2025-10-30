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


if __name__ == "__main__":
    result = asyncio.run(hello_agent())
    print(result)
