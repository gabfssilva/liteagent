"""
Tests for structured output with OpenAI.

Validates that agents can return structured output using Pydantic models
in a deterministic way.
"""
from typing import Literal
from pydantic import BaseModel
from ward import test

from liteagent import agent
from liteagent.providers import openai


class NumberClassification(BaseModel):
    """Classification of a number."""
    number: int
    is_even: bool
    is_positive: bool
    classification: Literal["even_positive", "even_negative", "odd_positive", "odd_negative"]


@test("structured output returns correct and deterministic classification")
async def _():
    """
    Tests that agent returns correct and deterministic structured output.

    Uses temperature=0 to ensure deterministic results.
    The test classifies numbers as even/odd and positive/negative.

    The library automatically parses the JSON returned by the LLM
    and returns the Pydantic object directly.
    """

    @agent(provider=openai(model="gpt-4o-mini", temperature=0))
    async def classify_number(prompt: str) -> NumberClassification:
        """
        {prompt}
        Classify this number:
        - Check if it's even or odd
        - Check if it's positive or negative
        - Return the appropriate classification
        """

    # Test with positive even number
    result_1 = await classify_number("The number is: 4")
    assert isinstance(result_1, NumberClassification)
    assert result_1.number == 4
    assert result_1.is_even is True
    assert result_1.is_positive is True
    assert result_1.classification == "even_positive"

    # Test with positive odd number
    result_2 = await classify_number("The number is: 7")
    assert isinstance(result_2, NumberClassification)
    assert result_2.number == 7
    assert result_2.is_even is False
    assert result_2.is_positive is True
    assert result_2.classification == "odd_positive"

    # Test with negative even number
    result_3 = await classify_number("The number is: -6")
    assert isinstance(result_3, NumberClassification)
    assert result_3.number == -6
    assert result_3.is_even is True
    assert result_3.is_positive is False
    assert result_3.classification == "even_negative"

    # Test with negative odd number
    result_4 = await classify_number("The number is: -3")
    assert isinstance(result_4, NumberClassification)
    assert result_4.number == -3
    assert result_4.is_even is False
    assert result_4.is_positive is False
    assert result_4.classification == "odd_negative"


@test("structured output extracts personal information from natural text")
async def _():
    """
    Tests simple structured output with personal information.

    Validates that the library can extract structured information from
    natural text and return it as a Pydantic object.
    """

    class PersonInfo(BaseModel):
        """Information about a person."""
        name: str
        age: int
        city: str

    @agent(provider=openai(model="gpt-4o-mini", temperature=0))
    async def extract_person_info(text: str) -> PersonInfo:
        """
        Extract structured information about the person from the text: {text}
        """

    # The library automatically parses and returns the Pydantic object
    result = await extract_person_info("John is 25 years old and lives in San Francisco")

    assert isinstance(result, PersonInfo)
    assert result.name.lower() == "john"
    assert result.age == 25
    assert "francisco" in result.city.lower() or "san francisco" in result.city.lower()
