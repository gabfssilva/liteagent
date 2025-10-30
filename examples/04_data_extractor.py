"""
Example 04: Data Extractor - Structured Output with Pydantic

This example demonstrates:
- Using Pydantic models for structured output
- Type-safe responses
- Automatic data extraction
- Return type annotations

Concepts introduced:
- Pydantic BaseModel
- Type annotations (-> Person, -> Company)
- Structured data extraction
- Type safety

Run: uv run python examples/04_data_extractor.py
"""

import asyncio
from typing import List

from pydantic import BaseModel, Field

from liteagent import agent
from liteagent.providers import openai


class Person(BaseModel):
    """Structured information about a person."""
    name: str = Field(description="Full name of the person")
    age: int = Field(description="Age in years")
    occupation: str = Field(description="Job or profession")
    location: str = Field(description="City and country")
    skills: List[str] = Field(description="List of skills or expertise")


class Company(BaseModel):
    """Structured information about a company."""
    name: str = Field(description="Company name")
    founded_year: int = Field(description="Year founded")
    industry: str = Field(description="Primary industry")
    headquarters: str = Field(description="Location of headquarters")
    employees: int = Field(description="Approximate number of employees")


@agent(provider=openai(model="gpt-4o-mini"))
async def person_extractor(text: str) -> Person:
    """
    Extract person information from this text: {text}

    Return structured data about the person mentioned.
    """


@agent(provider=openai(model="gpt-4o-mini"))
async def company_extractor(text: str) -> Company:
    """
    Extract company information from this text: {text}

    Return structured data about the company mentioned.
    """


if __name__ == "__main__":
    # Test person extraction
    person_text = """
    Dr. Sarah Chen is a 34-year-old computational biologist based in Singapore.
    She specializes in genomics, machine learning, and protein folding prediction.
    Her work combines biology with advanced data science techniques.
    """

    print("Extracting person information...")
    person = asyncio.run(person_extractor(person_text))
    print(f"\nExtracted Person:")
    print(f"  Name: {person.name}")
    print(f"  Age: {person.age}")
    print(f"  Occupation: {person.occupation}")
    print(f"  Location: {person.location}")
    print(f"  Skills: {', '.join(person.skills)}")

    # Test company extraction
    company_text = """
    TechNova Inc. was founded in 2018 and is headquartered in Austin, Texas.
    The company operates in the artificial intelligence and cloud computing space.
    With approximately 500 employees, TechNova develops enterprise AI solutions.
    """

    print("\n" + "="*60)
    print("Extracting company information...")
    company = asyncio.run(company_extractor(company_text))
    print(f"\nExtracted Company:")
    print(f"  Name: {company.name}")
    print(f"  Founded: {company.founded_year}")
    print(f"  Industry: {company.industry}")
    print(f"  Headquarters: {company.headquarters}")
    print(f"  Employees: {company.employees}")
