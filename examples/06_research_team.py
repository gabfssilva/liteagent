"""
Example 06: Research Team - Multi-Agent Coordination

This example demonstrates:
- Creating specialized agent teams
- Agent delegation and coordination
- team parameter
- Multi-agent workflows

Concepts introduced:
- Specialist agents
- team parameter
- Agent delegation
- Coordinator pattern

Run: uv run python examples/06_research_team.py
"""

import asyncio

from liteagent import agent
from liteagent.providers import openai
from liteagent.tools import duckduckgo, wikipedia


@agent(
    provider=openai(model="gpt-4o-mini"),
    tools=[duckduckgo(), wikipedia.search],
    description="""
    You are a search specialist focused on finding relevant information.
    Use DuckDuckGo for recent info and Wikipedia for established facts.
    """
)
async def search_specialist(query: str) -> str:
    """Search for information about: {query}"""


@agent(
    provider=openai(model="gpt-4o-mini"),
    description="""
    You are an analysis specialist focused on deep reasoning.
    Analyze data, identify patterns, and draw insights.
    """
)
async def analysis_specialist(data: str) -> str:
    """Analyze this information: {data}"""


@agent(
    provider=openai(model="gpt-4o-mini"),
    description="""
    You are a writing specialist focused on clear communication.
    Synthesize information into well-structured summaries.
    """
)
async def writing_specialist(research: str, analysis: str) -> str:
    """
    Write a summary based on:

    Research findings: {research}
    Analysis: {analysis}

    Create a clear, concise summary with key insights.
    """


@agent(
    provider=openai(model="gpt-4o-mini"),
    team=[search_specialist, analysis_specialist, writing_specialist],
    description="""
    You are a research coordinator managing a team of specialists:

    1. search_specialist - Finds information
    2. analysis_specialist - Analyzes data
    3. writing_specialist - Creates summaries

    For each research request:
    - Delegate search tasks to search_specialist
    - Send findings to analysis_specialist for insights
    - Have writing_specialist create the final summary

    Coordinate the workflow and ensure comprehensive coverage.
    """
)
async def research_coordinator(topic: str) -> str:
    """
    Coordinate a research project on: {topic}

    Use your team effectively to produce a comprehensive report.
    """


if __name__ == "__main__":
    # Test the research team
    topics = [
        "Recent breakthroughs in renewable energy",
        "Impact of AI on the job market",
        "The future of space exploration",
    ]

    for topic in topics:
        print(f"\n{'='*70}")
        print(f"Research Topic: {topic}")
        print('='*70)

        result = asyncio.run(research_coordinator(topic))
        print(result)
        print()
