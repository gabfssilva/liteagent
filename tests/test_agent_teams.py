"""
Tests for Agent Teams - Delegation between agents.

Validates that:
- Coordinator can delegate tasks to specialists
- Multiple specialists can be orchestrated correctly
- Teams work with structured output (Pydantic models)
"""
from pydantic import BaseModel
from ward import test

from liteagent import agent, tool
from liteagent.providers import openai
from tests.conftest import extract_text


@test("coordinator can delegate tasks to specialists")
async def _():
    """
    Tests that a coordinator agent can delegate tasks to specialists.

    Deterministic scenario:
    - Specialist has specific knowledge (via tool)
    - Coordinator delegates to specialist
    - Validate that delegation works correctly
    """

    @tool
    def get_technical_specs() -> dict:
        """Returns technical specifications of the product."""
        return {
            "product": "Laptop X1",
            "processor": "Intel i7",
            "ram": "16GB",
            "storage": "512GB SSD"
        }

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[get_technical_specs],
        description="Specialist in technical product specifications."
    )
    async def tech_specialist(query: str) -> str:
        """Answer about technical specifications: {query}"""

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

    result = await coordinator("What are the processor and RAM specifications of the Laptop X1?")
    result_text = await extract_text(result)

    # Validate that coordinator got information from specialist
    result_lower = result_text.lower()
    assert "i7" in result_lower or "intel" in result_lower
    assert "16gb" in result_lower or "16 gb" in result_lower


@test("coordinator orchestrates multiple specialized specialists")
async def _():
    """
    Tests coordinator with multiple specialized specialists.

    Deterministic scenario:
    - Sales specialist with pricing information
    - Support specialist with warranty information
    - Coordinator delegates to correct specialist
    """

    @tool
    def get_pricing() -> dict:
        """Returns pricing information."""
        return {
            "product": "Laptop X1",
            "price": 5999.90,
            "currency": "BRL",
            "discount": "10% off"
        }

    @tool
    def get_warranty() -> dict:
        """Returns warranty information."""
        return {
            "product": "Laptop X1",
            "warranty_years": 2,
            "coverage": "hardware defects",
            "support": "24/7"
        }

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[get_pricing],
        description="Specialist in prices and discounts."
    )
    async def sales_specialist(query: str) -> str:
        """Answer about prices: {query}"""

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[get_warranty],
        description="Specialist in warranty and support."
    )
    async def support_specialist(query: str) -> str:
        """Answer about warranty: {query}"""

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

    # Test delegation to sales specialist
    result_price = await sales_coordinator("What is the price of the Laptop X1?")
    price_text = await extract_text(result_price)
    assert "5999" in price_text or "R$" in price_text or "price" in price_text.lower()

    # Test delegation to support specialist
    result_warranty = await sales_coordinator("What is the warranty period for the Laptop X1?")
    warranty_text = await extract_text(result_warranty)
    assert "2" in warranty_text and ("year" in warranty_text.lower())


@test("teams work with structured output")
async def _():
    """
    Tests that teams work with structured output.

    Deterministic scenario:
    - Specialist returns structured data
    - Coordinator processes and also returns structured output
    """

    class ProductInfo(BaseModel):
        """Product information."""
        name: str
        category: str
        available: bool

    @tool
    def get_product_info() -> ProductInfo:
        """Returns product information."""
        return ProductInfo(
            name="Laptop X1",
            category="Electronics",
            available=True
        )

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[get_product_info],
        description="Specialist in product catalog."
    )
    async def catalog_specialist(query: str) -> str:
        """Answer about products: {query}"""

    class AvailabilityReport(BaseModel):
        """Availability report."""
        product_name: str
        is_available: bool
        status: str

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        team=[catalog_specialist]
    )
    async def availability_checker(query: str) -> AvailabilityReport:
        """
        Check availability: {query}
        Consult the specialist and return a structured report.
        """

    result = await availability_checker("Is the Laptop X1 available?")

    # Validate structured output
    assert isinstance(result, AvailabilityReport)
    assert result.product_name == "Laptop X1"
    assert result.is_available is True
    # Accept variations of "available" in different capitalizations
    status_lower = result.status.lower()
    assert any(word in status_lower for word in ["available", "stock", "yes"])
