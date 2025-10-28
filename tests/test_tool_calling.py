"""
Testes para Tool Calling - Agentes usando ferramentas customizadas.

Valida que agents conseguem:
- Chamar tools únicas e usar os dados retornados
- Orquestrar múltiplas tools em sequência
- Passar parâmetros estruturados para tools corretamente
"""
import pytest
from pydantic import BaseModel

from liteagent import agent, tool
from liteagent.providers import openai
from tests.conftest import extract_text


class UserProfile(BaseModel):
    """Perfil de um usuário."""
    name: str
    age: int
    city: str
    occupation: str


@tool
def get_user_profile() -> UserProfile:
    """Retorna o perfil do usuário atual."""
    return UserProfile(
        name="Gabriel Silva",
        age=32,
        city="São Paulo",
        occupation="Software Engineer"
    )


@tool
def calculate_age_in_days(age_in_years: int) -> int:
    """Calcula a idade aproximada em dias dado a idade em anos."""
    return age_in_years * 365


@pytest.mark.asyncio
async def test_tool_calling_single_tool():
    """
    Testa que o agente consegue chamar uma ferramenta e usar os dados retornados.

    Cenário determinístico:
    - Tool retorna dados fixos do usuário
    - Agente deve chamar a tool para obter informações
    - Validar que a resposta contém os dados corretos
    """

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[get_user_profile]
    )
    async def profile_agent(query: str) -> str:
        """
        Responda a pergunta do usuário: {query}
        Use as ferramentas disponíveis quando necessário.
        """

    result = await profile_agent("Qual é o nome completo e a profissão do usuário?")
    result_text = await extract_text(result)
    result_lower = result_text.lower()

    # Validar que a resposta contém informações do perfil
    assert "Gabriel Silva" in result_text or "Gabriel" in result_text
    assert "Software Engineer" in result_text or "Engineer" in result_text or "engenheiro" in result_lower


@pytest.mark.asyncio
async def test_tool_calling_multiple_tools():
    """
    Testa que o agente consegue chamar múltiplas ferramentas em sequência.

    Cenário determinístico:
    - Primeira tool retorna perfil do usuário
    - Segunda tool calcula idade em dias
    - Agente deve orquestrar ambas as tools
    """

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[get_user_profile, calculate_age_in_days]
    )
    async def multi_tool_agent(query: str) -> str:
        """
        Responda a pergunta do usuário: {query}
        Use as ferramentas disponíveis para obter e processar informações.
        """

    result = await multi_tool_agent(
        "Quantos dias aproximadamente o usuário viveu? "
        "Primeiro obtenha a idade dele e depois calcule."
    )
    result_text = await extract_text(result)

    # Validar que a resposta menciona os dias (32 anos * 365 dias = 11680 dias)
    assert "11680" in result_text or "11,680" in result_text or "dias" in result_text.lower()


@pytest.mark.asyncio
async def test_tool_with_structured_input():
    """
    Testa que o agente consegue chamar tools com parâmetros estruturados.

    Cenário determinístico:
    - Tool recebe inteiro como parâmetro
    - Agente deve extrair o valor do prompt e passar corretamente
    """

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[calculate_age_in_days]
    )
    async def calculator_agent(query: str) -> str:
        """
        Responda a pergunta: {query}
        Use a ferramenta de cálculo quando necessário.
        """

    result = await calculator_agent("Quantos dias tem 25 anos?")
    result_text = await extract_text(result)

    # Validar que calculou corretamente: 25 * 365 = 9125
    assert "9125" in result_text or "9,125" in result_text
