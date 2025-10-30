"""
Example 03: Web Researcher - Using Multiple Built-in Tools

This example demonstrates:
- Using built-in tools (DuckDuckGo, Wikipedia)
- Composing multiple tools together
- Agent choosing which tool to use
- Real-world research workflow

Concepts introduced:
- Built-in tools
- Tool composition
- Agent decision-making
- Web search and Wikipedia integration

Run: uv run python examples/03_web_researcher.py
"""

import asyncio

from liteagent import agent
from liteagent.providers import openai
from liteagent.tools import duckduckgo, wikipedia


@agent(
    provider=openai(model="gpt-4o-mini"),
    tools=[
        duckduckgo(),
        wikipedia.search,
        wikipedia.get_complete_article
    ],
    description="""
    You are a research assistant that finds accurate information.

    Always:
    1. Use DuckDuckGo to find recent information
    2. Use Wikipedia for detailed, verified facts
    3. Cite your sources
    4. Provide comprehensive answers
    """
)
async def researcher(query: str) -> str:
    """Research this topic: {query}"""


if __name__ == "__main__":
    # Test the research agent
    queries = [
        "What are the latest developments in quantum computing?",
        "Who won the Nobel Prize in Physics in 2024?",
        "Explain how photosynthesis works",
    ]

    for query in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)

        result = asyncio.run(researcher(query))
        print(result)
