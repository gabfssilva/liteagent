"""
BDD tests for Structured Output - Agents returning Pydantic models.

Validates that agents can:
- Return structured output using Pydantic models
- Classify data deterministically
- Extract information from natural text
"""
from typing import Literal
from pydantic import BaseModel
from pytest_bdd import scenarios, when, then, parsers
from pytest import fixture
import asyncio
import functools

from liteagent import agent
from liteagent.providers import openai


# Async wrapper for pytest-bdd compatibility
def async_to_sync(fn):
    """Wrapper to convert async functions to sync for pytest-bdd."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))
    return wrapper

# Load all scenarios from the feature file
scenarios('../features/structured_output.feature')


# ==================== MODELS ====================

class NumberClassification(BaseModel):
    """Classification of a number."""
    number: int
    is_even: bool
    is_positive: bool
    classification: Literal["even_positive", "even_negative", "odd_positive", "odd_negative"]


class PersonInfo(BaseModel):
    """Information about a person."""
    name: str
    age: int
    city: str


# ==================== FIXTURES ====================

@fixture
def classify_agent():
    """Agent that classifies numbers."""
    @agent(provider=openai(model="gpt-4o-mini", temperature=0))
    async def classify_number(prompt: str) -> NumberClassification:
        """
        {prompt}
        Classify this number:
        - Check if it's even or odd
        - Check if it's positive or negative
        - Return the appropriate classification
        """
    return classify_number


@fixture
def extract_person_agent():
    """Agent that extracts person information."""
    @agent(provider=openai(model="gpt-4o-mini", temperature=0))
    async def extract_person_info(text: str) -> PersonInfo:
        """
        Extract structured information about the person from the text: {text}
        """
    return extract_person_info


# ==================== WHEN STEPS ====================

@when(parsers.parse("I classify the number {number:d}"), target_fixture="agent_response")
def when_classify_number(classify_agent, number):
    """Classifies a number."""
    async def _classify():
        return await classify_agent(f"The number is: {number}")

    return async_to_sync(_classify)()


@when(parsers.parse('I extract person info from "{text}"'), target_fixture="agent_response")
def when_extract_person_info(extract_person_agent, text):
    """Extracts person info from text."""
    async def _extract():
        return await extract_person_agent(text)

    return async_to_sync(_extract)()


# ==================== THEN STEPS (specific to person info) ====================

@then(parsers.parse('the person name should be "{expected}"'))
def then_person_name(agent_response, expected):
    """Verifies person name."""
    assert hasattr(agent_response, 'name'), "Response missing 'name' field"
    assert agent_response.name.lower() == expected.lower(), \
        f"Expected name '{expected}', got '{agent_response.name}'"


@then(parsers.parse("the person age should be {expected:d}"))
def then_person_age(agent_response, expected):
    """Verifies person age."""
    assert hasattr(agent_response, 'age'), "Response missing 'age' field"
    assert agent_response.age == expected, \
        f"Expected age {expected}, got {agent_response.age}"


@then(parsers.parse('the person city should contain "{text}"'))
def then_person_city_contains(agent_response, text):
    """Verifies person city contains text."""
    assert hasattr(agent_response, 'city'), "Response missing 'city' field"
    assert text.lower() in agent_response.city.lower(), \
        f"Expected '{text}' in city, got '{agent_response.city}'"
