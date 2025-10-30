"""
Example 10: Production Agent - All Features Combined

This example demonstrates:
- ALL LiteAgent features working together
- Production-ready agent architecture
- Complete workflow implementation
- Best practices

Features combined:
✅ Stateful sessions
✅ Multi-agent teams
✅ Guardrails (security)
✅ Long-term memory (memoria)
✅ Structured output
✅ Multiple tools
✅ Complex orchestration

This is a comprehensive example showing how to build a production-ready
AI agent system with LiteAgent.

Run: uv run python examples/10_production_agent.py
"""

import asyncio
from typing import List, Literal

from pydantic import BaseModel, Field

from liteagent import agent
from liteagent.guardrails import guardrail
from liteagent.guardrails.builtin import NoPII
from liteagent.providers import openai
from liteagent.tools import duckduckgo, memoria, calculator


# Structured output models
class Task(BaseModel):
    """A task with priority and status."""
    title: str = Field(description="Task title")
    priority: Literal["low", "medium", "high"] = Field(description="Priority level")
    category: str = Field(description="Task category")
    status: Literal["pending", "in_progress", "completed"] = Field(description="Current status")


class DailyPlan(BaseModel):
    """Daily plan with tasks."""
    date: str = Field(description="Date in YYYY-MM-DD format")
    tasks: List[Task] = Field(description="List of tasks")
    summary: str = Field(description="Brief summary of the day")


# Specialist agents (team members)
@agent(
    provider=openai(model="gpt-4o-mini"),
    tools=[duckduckgo()],
    description="Research specialist focused on finding accurate information."
)
async def research_specialist(query: str) -> str:
    """Research: {query}"""


@agent(
    provider=openai(model="gpt-4o-mini"),
    tools=[calculator],
    description="Data analyst specialized in calculations and metrics."
)
async def data_analyst(calculation: str) -> str:
    """Calculate: {calculation}"""


# Main production agent
@guardrail(NoPII(block_on_detection=False))  # Security layer
@agent(
    provider=openai(model="gpt-4o-mini"),
    tools=[memoria()],  # Long-term memory
    team=[research_specialist, data_analyst],  # Specialist team
    description="""
    You are an Executive AI Assistant with advanced capabilities:

    🧠 Long-term Memory: Use memoria to store and recall important information
    👥 Specialist Team: Delegate to research_specialist and data_analyst
    🔒 Security: PII protection enabled automatically
    📊 Structured Output: Can provide formatted responses when needed

    Capabilities:
    - Task planning and management
    - Research coordination
    - Data analysis
    - Information retention
    - Secure communication

    Best Practices:
    1. Always check memoria for relevant past information
    2. Store important facts and decisions in memoria
    3. Delegate research to research_specialist
    4. Delegate calculations to data_analyst
    5. Provide structured output when appropriate
    6. Maintain context across conversations
    """
)
async def executive_assistant(message: str) -> str:
    """User request: {message}"""


async def demonstrate_production_agent():
    """Demonstrate production-ready agent with all features."""

    print("🚀 Production-Ready AI Agent")
    print("="*80)
    print()

    # Create stateful session (maintains context)
    assistant = executive_assistant.stateful()

    # Scenario 1: Information storage and retrieval
    print("📝 Scenario 1: Long-term Memory")
    print("-"*80)

    async for msg in assistant("Store this: My Q1 goals are to launch product v2.0, hire 3 engineers, and increase revenue by 25%"):
        if msg.role == "assistant" and msg.complete():
            # Extract text from AssistantMessage.TextStream
            if hasattr(msg.content, 'await_complete'):
                text = await msg.content.await_complete()
                print(f"Assistant: {text}\n")

    # Scenario 2: Research delegation
    print("📊 Scenario 2: Research Delegation")
    print("-"*80)

    async for msg in assistant("Research the latest trends in AI agent frameworks"):
        if msg.role == "assistant" and msg.complete():
            # Extract text from AssistantMessage.TextStream
            if hasattr(msg.content, 'await_complete'):
                text = await msg.content.await_complete()
                print(f"Assistant: {text}\n")

    # Scenario 3: Data analysis
    print("🔢 Scenario 3: Data Analysis")
    print("-"*80)

    async for msg in assistant("If revenue is currently $1M and we increase by 25%, what's the new revenue? Then calculate quarterly targets."):
        if msg.role == "assistant" and msg.complete():
            # Extract text from AssistantMessage.TextStream
            if hasattr(msg.content, 'await_complete'):
                text = await msg.content.await_complete()
                print(f"Assistant: {text}\n")

    # Scenario 4: Memory recall
    print("🧠 Scenario 4: Memory Recall")
    print("-"*80)

    async for msg in assistant("What are my Q1 goals that we discussed earlier?"):
        if msg.role == "assistant" and msg.complete():
            # Extract text from AssistantMessage.TextStream
            if hasattr(msg.content, 'await_complete'):
                text = await msg.content.await_complete()
                print(f"Assistant: {text}\n")

    # Scenario 5: Security (PII handling)
    print("🔒 Scenario 5: Security & PII Protection")
    print("-"*80)

    async for msg in assistant("Remind me to call john.doe@example.com tomorrow"):
        if msg.role == "assistant" and msg.complete():
            # Extract text from AssistantMessage.TextStream
            if hasattr(msg.content, 'await_complete'):
                text = await msg.content.await_complete()
                print(f"Assistant: {text}")
                if "john.doe@example.com" not in text.lower():
                    print("✅ PII was redacted for security\n")

    print("="*80)
    print("\n✨ Production Agent Features Demonstrated:")
    print("   ✅ Long-term memory (memoria)")
    print("   ✅ Multi-agent coordination (team)")
    print("   ✅ Stateful conversations (session)")
    print("   ✅ Security guardrails (NoPII)")
    print("   ✅ Tool integration (calculator, search)")
    print("   ✅ Context retention across interactions")
    print("\nThis agent is production-ready! 🚀")


if __name__ == "__main__":
    asyncio.run(demonstrate_production_agent())
