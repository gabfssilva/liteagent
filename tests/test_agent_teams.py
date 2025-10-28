"""
Testes para Agent Teams - Delegação entre agentes.

Valida que:
- Coordinator consegue delegar tarefas para specialists
- Múltiplos specialists podem ser orquestrados corretamente
- Teams funcionam com structured output (Pydantic models)
"""
from pydantic import BaseModel
from ward import test

from liteagent import agent, tool
from liteagent.providers import openai
from tests.conftest import extract_text


@test("coordinator consegue delegar tarefas para specialists")
async def _():
    """
    Testa que um agente coordinator consegue delegar tarefas para specialists.

    Cenário determinístico:
    - Specialist tem conhecimento específico (via tool)
    - Coordinator delega para o specialist
    - Validar que a delegação funciona corretamente
    """

    @tool
    def get_technical_specs() -> dict:
        """Retorna especificações técnicas do produto."""
        return {
            "product": "Laptop X1",
            "processor": "Intel i7",
            "ram": "16GB",
            "storage": "512GB SSD"
        }

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[get_technical_specs],
        description="Especialista em especificações técnicas de produtos."
    )
    async def tech_specialist(query: str) -> str:
        """Responda sobre especificações técnicas: {query}"""

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        team=[tech_specialist],
        description="Coordenador que delega perguntas técnicas para o especialista."
    )
    async def coordinator(query: str) -> str:
        """
        Responda a pergunta: {query}
        SEMPRE use o tech_specialist para obter especificações técnicas.
        """

    result = await coordinator("Quais são as especificações do processador e memória RAM do Laptop X1?")
    result_text = await extract_text(result)

    # Validar que o coordinator obteve informação do specialist
    result_lower = result_text.lower()
    assert "i7" in result_lower or "intel" in result_lower
    assert "16gb" in result_lower or "16 gb" in result_lower


@test("coordinator orquestra múltiplos specialists especializados")
async def _():
    """
    Testa coordinator com múltiplos specialists especializados.

    Cenário determinístico:
    - Sales specialist com informações de preço
    - Support specialist com informações de garantia
    - Coordinator delega para o specialist correto
    """

    @tool
    def get_pricing() -> dict:
        """Retorna informações de preço."""
        return {
            "product": "Laptop X1",
            "price": 5999.90,
            "currency": "BRL",
            "discount": "10% off"
        }

    @tool
    def get_warranty() -> dict:
        """Retorna informações de garantia."""
        return {
            "product": "Laptop X1",
            "warranty_years": 2,
            "coverage": "hardware defects",
            "support": "24/7"
        }

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[get_pricing],
        description="Especialista em preços e descontos."
    )
    async def sales_specialist(query: str) -> str:
        """Responda sobre preços: {query}"""

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[get_warranty],
        description="Especialista em garantia e suporte."
    )
    async def support_specialist(query: str) -> str:
        """Responda sobre garantia: {query}"""

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        team=[sales_specialist, support_specialist],
        description="Coordenador que delega para especialistas de vendas ou suporte."
    )
    async def sales_coordinator(query: str) -> str:
        """
        Responda: {query}
        Use sales_specialist para perguntas sobre preços.
        Use support_specialist para perguntas sobre garantia.
        """

    # Testar delegação para sales specialist
    result_price = await sales_coordinator("Qual é o preço do Laptop X1?")
    price_text = await extract_text(result_price)
    assert "5999" in price_text or "R$" in price_text or "preço" in price_text.lower()

    # Testar delegação para support specialist
    result_warranty = await sales_coordinator("Qual é o período de garantia do Laptop X1?")
    warranty_text = await extract_text(result_warranty)
    assert "2" in warranty_text and ("ano" in warranty_text.lower() or "year" in warranty_text.lower())


@test("teams funcionam com structured output")
async def _():
    """
    Testa que teams funcionam com structured output.

    Cenário determinístico:
    - Specialist retorna dados estruturados
    - Coordinator processa e retorna estruturado também
    """

    class ProductInfo(BaseModel):
        """Informações do produto."""
        name: str
        category: str
        available: bool

    @tool
    def get_product_info() -> ProductInfo:
        """Retorna informações do produto."""
        return ProductInfo(
            name="Laptop X1",
            category="Electronics",
            available=True
        )

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[get_product_info],
        description="Especialista em catálogo de produtos."
    )
    async def catalog_specialist(query: str) -> str:
        """Responda sobre produtos: {query}"""

    class AvailabilityReport(BaseModel):
        """Relatório de disponibilidade."""
        product_name: str
        is_available: bool
        status: str

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        team=[catalog_specialist]
    )
    async def availability_checker(query: str) -> AvailabilityReport:
        """
        Verifique disponibilidade: {query}
        Consulte o especialista e retorne um relatório estruturado.
        """

    result = await availability_checker("O Laptop X1 está disponível?")

    # Validar structured output
    assert isinstance(result, AvailabilityReport)
    assert result.product_name == "Laptop X1"
    assert result.is_available is True
    # Aceita variações de "disponível" em diferentes capitalizações
    status_lower = result.status.lower()
    assert any(word in status_lower for word in ["available", "stock", "disponível", "yes"])
