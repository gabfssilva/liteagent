"""
Example 02: Calculator Tool - Your First Custom Tool

This example demonstrates:
- Creating custom tools with @tool decorator
- Type hints for parameters
- Tool execution by the agent
- Agent with tools parameter

Concepts introduced:
- @tool decorator
- Tool definitions
- Function parameters with type hints
- Agent tool calling

Run: uv run python examples/02_calculator_tool.py
"""

import asyncio

from liteagent import agent, tool
from liteagent.providers import openai


@tool
def calculate(expression: str) -> float:
    """
    Evaluate a mathematical expression safely.

    Args:
        expression: A mathematical expression like "2 + 2" or "10 * 5"

    Returns:
        The result of the calculation
    """
    # Safe evaluation of basic math expressions
    try:
        # Only allow basic math operations
        allowed_chars = set("0123456789+-*/(). ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Invalid characters in expression"

        result = eval(expression)
        return float(result)
    except Exception as e:
        return f"Error: {str(e)}"


@agent(
    provider=openai(model="gpt-4o-mini"),
    tools=[calculate]
)
async def calculator_agent(problem: str) -> str:
    """
    You are a calculator assistant.

    Solve this math problem: {problem}

    Use the calculate tool to compute the answer.
    """


if __name__ == "__main__":
    # Test the calculator agent
    problems = [
        "What is 234 + 567?",
        "Calculate 15 * 8 - 20",
        "What is (100 + 50) / 3?",
    ]

    for problem in problems:
        print(f"\nProblem: {problem}")
        result = asyncio.run(calculator_agent(problem))
        print(f"Answer: {result}")
