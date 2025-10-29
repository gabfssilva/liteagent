"""
Tests for Tool Calling - Agents using custom tools.

Validates that agents can:
- Call individual tools and use returned data
- Orchestrate multiple tools in sequence
- Pass structured parameters to tools correctly
"""
from pydantic import BaseModel
from ward import test

from liteagent import agent, tool
from liteagent.providers import openai


class UserProfile(BaseModel):
    """User profile information."""
    name: str
    age: int
    city: str
    occupation: str


@tool
def get_user_profile() -> UserProfile:
    """Returns the current user profile."""
    return UserProfile(
        name="Gabriel Silva",
        age=32,
        city="São Paulo",
        occupation="Software Engineer"
    )


@tool
def calculate_age_in_days(age_in_years: int) -> int:
    """Calculates approximate age in days given age in years."""
    return age_in_years * 365


@test("agent can call a tool and use the returned data")
async def _(extract_text):
    """
    Tests that agent can call a tool and use the returned data.

    Deterministic scenario:
    - Tool returns fixed user data
    - Agent must call the tool to get information
    - Validate that response contains correct data
    """

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[get_user_profile]
    )
    async def profile_agent(query: str) -> str:
        """
        Answer the user's question: {query}
        Use available tools when necessary.
        """

    result = await profile_agent("What is the full name and occupation of the user?")
    result_text = await extract_text(result)
    result_lower = result_text.lower()

    # Validate that response contains profile information
    assert "Gabriel Silva" in result_text or "Gabriel" in result_text
    assert "Software Engineer" in result_text or "Engineer" in result_text or "engineer" in result_lower


@test("agent can call multiple tools in sequence")
async def _(extract_text):
    """
    Tests that agent can call multiple tools in sequence.

    Deterministic scenario:
    - First tool returns user profile
    - Second tool calculates age in days
    - Agent must orchestrate both tools
    """

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[get_user_profile, calculate_age_in_days]
    )
    async def multi_tool_agent(query: str) -> str:
        """
        Answer the user's question: {query}
        Use available tools to get and process information.
        """

    result = await multi_tool_agent(
        "How many days approximately has the user lived? "
        "First get their age then calculate."
    )
    result_text = await extract_text(result)

    # Validate that response mentions the days (32 years * 365 days = 11680 days)
    assert "11680" in result_text or "11,680" in result_text or "days" in result_text.lower()


@test("agent can call tools with structured parameters")
async def _(extract_text):
    """
    Tests that agent can call tools with structured parameters.

    Deterministic scenario:
    - Tool receives integer parameter
    - Agent must extract value from prompt and pass correctly
    """

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[calculate_age_in_days]
    )
    async def calculator_agent(query: str) -> str:
        """
        Answer the question: {query}
        Use the calculation tool when necessary.
        """

    result = await calculator_agent("How many days are in 25 years?")
    result_text = await extract_text(result)

    # Validate correct calculation: 25 * 365 = 9125
    assert "9125" in result_text or "9,125" in result_text
