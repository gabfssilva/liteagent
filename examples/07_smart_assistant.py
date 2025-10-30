"""
Example 07: Smart Assistant - Long-term Memory

This example demonstrates:
- Using memoria for long-term memory
- Persistent information storage
- Information retrieval across sessions
- RAG (Retrieval-Augmented Generation) concepts

Concepts introduced:
- memoria tool (long-term memory)
- Persistent storage
- Memory retrieval
- RAG basics

Run: uv run python examples/07_smart_assistant.py
"""

import asyncio

from liteagent import agent
from liteagent.providers import openai
from liteagent.tools import memoria


@agent(
    provider=openai(model="gpt-4o-mini"),
    tools=[memoria],
    description="""
    You are a personal assistant with long-term memory.

    IMPORTANT:
    - ALWAYS check your memory before responding to questions
    - Store important facts and preferences the user shares
    - Recall information from previous conversations
    - Use memoria tool to store and retrieve information

    When user shares information (preferences, facts, plans):
    - Store it in memoria for later retrieval

    When user asks questions:
    - Search memoria first for relevant information
    - Provide personalized responses based on stored data
    """
)
async def smart_assistant(message: str) -> str:
    """User says: {message}"""


async def demonstrate_memory():
    """Demonstrate long-term memory across multiple interactions."""

    print("Smart Assistant with Long-term Memory")
    print("="*70)
    print()

    # Session 1: Storing information
    print("📝 Session 1: Storing user preferences")
    print("-"*70)

    session1_messages = [
        "My name is Alex and I'm a software engineer",
        "I love Python and I'm learning about AI agents",
        "My favorite food is sushi and I live in Tokyo",
        "I'm planning to learn Japanese next month",
    ]

    for msg in session1_messages:
        print(f"User: {msg}")
        result = asyncio.run(smart_assistant(msg))
        print(f"Assistant: {result}\n")

    print("\n" + "="*70)
    print("📖 Session 2: Retrieving stored information")
    print("-"*70)

    # Session 2: Retrieving information (simulating a new conversation)
    session2_messages = [
        "What's my name?",
        "What do I do for work?",
        "What am I planning to learn?",
        "Recommend a restaurant for me based on my preferences",
    ]

    for msg in session2_messages:
        print(f"User: {msg}")
        result = asyncio.run(smart_assistant(msg))
        print(f"Assistant: {result}\n")

    print("="*70)
    print("\nDemonstration complete!")
    print("The assistant remembered information across separate interactions.")


if __name__ == "__main__":
    asyncio.run(demonstrate_memory())
