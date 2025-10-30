"""
Example 05: Customer Support - Stateful Conversations

This example demonstrates:
- Using sessions for stateful conversations
- Maintaining conversation history
- Context retention across messages
- .stateful() method

Concepts introduced:
- Session management
- Conversation history
- Context retention
- .stateful() method

Run: uv run python examples/05_customer_support.py
"""

import asyncio

from liteagent import agent
from liteagent.providers import openai


@agent(
    provider=openai(model="gpt-4o-mini"),
    description="""
    You are a helpful customer support agent for TechStore, an online electronics retailer.

    Your responsibilities:
    - Answer questions about orders, products, and policies
    - Maintain context throughout the conversation
    - Be friendly and professional
    - Remember details the customer provides

    Store policies:
    - 30-day return policy
    - Free shipping on orders over $50
    - 1-year warranty on all electronics
    """
)
async def support_agent(message: str) -> str:
    """Customer says: {message}"""


async def run_support_session():
    """Simulate a customer support conversation."""

    # Create a stateful session
    chat = support_agent.stateful()

    print("TechStore Customer Support")
    print("="*60)
    print("Agent: Hello! How can I help you today?\n")

    # Simulate a conversation
    messages = [
        "Hi, I ordered a laptop last week but it hasn't arrived yet.",
        "The order number is #12345",
        "When will it arrive?",
        "What if I'm not satisfied with it?",
        "How much was the shipping cost?",
    ]

    for user_message in messages:
        print(f"Customer: {user_message}")

        # Agent maintains context from previous messages
        # Collect all messages and print the final assistant response
        messages_list = []
        async for response in chat(user_message):
            messages_list.append(response)

        # Get the last assistant message and extract text
        for response in reversed(messages_list):
            if response.role == "assistant":
                # Extract text from AssistantMessage.TextStream
                if hasattr(response.content, 'await_complete'):
                    text = await response.content.await_complete()
                    print(f"Agent: {text}\n")
                break

    print("="*60)
    print("Session demonstrates context retention:")
    print("- Agent remembers order number from message 2")
    print("- Agent provides relevant policy information")
    print("- Conversation flows naturally across messages")


if __name__ == "__main__":
    asyncio.run(run_support_session())
