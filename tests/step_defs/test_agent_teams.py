"""
BDD tests for Agent Teams - Delegation between agents.

Validates that:
- Coordinator can delegate tasks to specialists
- Multiple specialists can be orchestrated correctly
- Teams work with structured output (Pydantic models)
"""
from pydantic import BaseModel
from pytest_bdd import scenarios, given, when, then, parsers
from pytest import fixture
import asyncio
import functools

from liteagent import agent, tool
from liteagent.providers import openai


# Async wrapper
def async_to_sync(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))
    return wrapper


# Load all scenarios
scenarios('../features/agent_teams.feature')


# ==================== MODELS ====================

class ProductInfo(BaseModel):
    """Product information."""
    name: str
    category: str
    available: bool


class AvailabilityReport(BaseModel):
    """Availability report."""
    product_name: str
    is_available: bool
    status: str


# ==================== TOOL FIXTURES ====================

@fixture
def get_technical_specs_tool():
    """Tool for technical specifications."""
    @tool
    def get_technical_specs() -> dict:
        """Returns technical specifications of the product."""
        return {
            "product": "Laptop X1",
            "processor": "Intel i7",
            "ram": "16GB",
            "storage": "512GB SSD"
        }
    return get_technical_specs


@fixture
def get_pricing_tool():
    """Tool for pricing information."""
    @tool
    def get_pricing() -> dict:
        """Returns pricing information."""
        return {
            "product": "Laptop X1",
            "price": 5999.90,
            "currency": "BRL",
            "discount": "10% off"
        }
    return get_pricing


@fixture
def get_warranty_tool():
    """Tool for warranty information."""
    @tool
    def get_warranty() -> dict:
        """Returns warranty information."""
        return {
            "product": "Laptop X1",
            "warranty_years": 2,
            "coverage": "hardware defects",
            "support": "24/7"
        }
    return get_warranty


@fixture
def get_product_info_tool():
    """Tool for product information."""
    @tool
    def get_product_info() -> ProductInfo:
        """Returns product information."""
        return ProductInfo(
            name="Laptop X1",
            category="Electronics",
            available=True
        )
    return get_product_info


# ==================== GIVEN STEPS ====================

@given("the OpenAI provider is available")
def given_openai_available():
    """Verify OpenAI provider is available."""
    import os
    assert os.environ.get("OPENAI_API_KEY"), "OPENAI_API_KEY required"


@given("a tech specialist with technical specifications tool", target_fixture="tech_specialist")
def given_tech_specialist(get_technical_specs_tool):
    """Creates a technical specialist agent."""
    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[get_technical_specs_tool],
        description="Specialist in technical product specifications."
    )
    async def tech_specialist(query: str) -> str:
        """Answer about technical specifications: {query}"""
    return tech_specialist


@given("a coordinator that delegates to tech specialist", target_fixture="coordinator")
def given_coordinator(tech_specialist):
    """Creates a coordinator agent."""
    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        team=[tech_specialist],
        description="Coordinator that delegates technical questions to the specialist."
    )
    async def coordinator(query: str) -> str:
        """
        Answer the question: {query}
        ALWAYS use the tech_specialist to get technical specifications.
        """
    return coordinator


@given("a sales specialist with pricing tool", target_fixture="sales_specialist")
def given_sales_specialist(get_pricing_tool):
    """Creates a sales specialist agent."""
    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[get_pricing_tool],
        description="Specialist in prices and discounts."
    )
    async def sales_specialist(query: str) -> str:
        """Answer about prices: {query}"""
    return sales_specialist


@given("a support specialist with warranty tool", target_fixture="support_specialist")
def given_support_specialist(get_warranty_tool):
    """Creates a support specialist agent."""
    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[get_warranty_tool],
        description="Specialist in warranty and support."
    )
    async def support_specialist(query: str) -> str:
        """Answer about warranty: {query}"""
    return support_specialist


@given("a multi-team coordinator", target_fixture="multi_coordinator")
def given_multi_coordinator(sales_specialist, support_specialist):
    """Creates a multi-team coordinator."""
    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        team=[sales_specialist, support_specialist],
        description="Coordinator that delegates to sales or support specialists."
    )
    async def sales_coordinator(query: str) -> str:
        """
        Answer: {query}
        Use sales_specialist for questions about prices.
        Use support_specialist for questions about warranty.
        """
    return sales_coordinator


@given("a catalog specialist with product info tool", target_fixture="catalog_specialist")
def given_catalog_specialist(get_product_info_tool):
    """Creates a catalog specialist agent."""
    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[get_product_info_tool],
        description="Specialist in product catalog."
    )
    async def catalog_specialist(query: str) -> str:
        """Answer about products: {query}"""
    return catalog_specialist


@given("an availability checker that uses catalog specialist", target_fixture="availability_checker")
def given_availability_checker(catalog_specialist):
    """Creates an availability checker agent."""
    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        team=[catalog_specialist]
    )
    async def availability_checker(query: str) -> AvailabilityReport:
        """
        Check availability: {query}
        Consult the specialist and return a structured report.
        """
    return availability_checker


# ==================== WHEN STEPS ====================

@when(parsers.parse('I ask the coordinator "{query}"'), target_fixture="coordinator_response")
def when_ask_coordinator(coordinator, query, extract_text):
    """Asks the coordinator a question."""
    async def _ask():
        result = await coordinator(query)
        return await extract_text(result)
    return async_to_sync(_ask)()


@when(parsers.parse('I ask the multi-team coordinator "{query}"'), target_fixture="multi_team_response")
def when_ask_multi_coordinator(multi_coordinator, query, extract_text):
    """Asks the multi-team coordinator a question."""
    async def _ask():
        result = await multi_coordinator(query)
        return await extract_text(result)
    return async_to_sync(_ask)()


@when(parsers.parse('I check availability for "{query}"'), target_fixture="availability_report")
def when_check_availability(availability_checker, query):
    """Checks availability."""
    async def _check():
        return await availability_checker(query)
    return async_to_sync(_check)()


# ==================== THEN STEPS ====================

@then(parsers.parse('the coordinator response should contain "{text}"'))
def then_coordinator_response_contains(coordinator_response, text):
    """Verifies coordinator response contains text."""
    response_lower = coordinator_response.lower()
    text_lower = text.lower()
    assert text_lower in response_lower, \
        f"Expected '{text}' in coordinator response: {coordinator_response}"


@then(parsers.parse('the multi-team response should contain "{text}"'))
def then_multi_team_response_contains(multi_team_response, text):
    """Verifies multi-team response contains text."""
    response_lower = multi_team_response.lower()
    text_lower = text.lower()
    # Remove formatting characters for numeric comparisons
    response_clean = response_lower.replace(',', '').replace('.', '')
    text_clean = text_lower.replace(',', '').replace('.', '')
    assert text_lower in response_lower or text_clean in response_clean, \
        f"Expected '{text}' in multi-team response: {multi_team_response}"


@then(parsers.parse('the availability report should have product_name "{expected}"'))
def then_availability_product_name(availability_report, expected):
    """Verifies availability report product name."""
    assert isinstance(availability_report, AvailabilityReport)
    assert availability_report.product_name == expected, \
        f"Expected product_name='{expected}', got '{availability_report.product_name}'"


@then(parsers.parse('the availability report should have is_available {expected}'))
def then_availability_is_available(availability_report, expected):
    """Verifies availability report is_available field."""
    assert isinstance(availability_report, AvailabilityReport)
    expected_bool = expected.lower() == "true"
    assert availability_report.is_available == expected_bool, \
        f"Expected is_available={expected_bool}, got {availability_report.is_available}"


@then("the availability report status should indicate available")
def then_availability_status_available(availability_report):
    """Verifies availability report status indicates available."""
    assert isinstance(availability_report, AvailabilityReport)
    status_lower = availability_report.status.lower()
    assert any(word in status_lower for word in ["available", "stock", "yes"]), \
        f"Expected status to indicate available, got: {availability_report.status}"
