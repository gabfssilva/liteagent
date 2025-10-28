"""
Testes para structured output com OpenAI.

Este teste verifica que o agent consegue retornar structured output
usando Pydantic models de forma determinística.
"""
import pytest
from typing import Literal
from pydantic import BaseModel

from liteagent import agent
from liteagent.providers import openai


class NumberClassification(BaseModel):
    """Classificação de um número."""
    number: int
    is_even: bool
    is_positive: bool
    classification: Literal["even_positive", "even_negative", "odd_positive", "odd_negative"]


@pytest.mark.asyncio
async def test_structured_output_deterministic():
    """
    Testa que o agent retorna structured output correto e determinístico.

    Usa temperature=0 para garantir que o resultado seja determinístico.
    O teste classifica números como par/ímpar e positivo/negativo.

    A biblioteca faz o parse automático do JSON retornado pelo LLM
    e retorna o objeto Pydantic diretamente.
    """

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[]
    )
    async def classify_number(prompt: str) -> NumberClassification:
        """
        {prompt}
        Classifica esse número:
        - Verifica se é par ou ímpar
        - Verifica se é positivo ou negativo
        - Retorna a classificação apropriada
        """

    # Testa com número par positivo
    result_1 = await classify_number("O número é: 4")
    assert isinstance(result_1, NumberClassification)
    assert result_1.number == 4
    assert result_1.is_even is True
    assert result_1.is_positive is True
    assert result_1.classification == "even_positive"

    # Testa com número ímpar positivo
    result_2 = await classify_number("O número é: 7")
    assert isinstance(result_2, NumberClassification)
    assert result_2.number == 7
    assert result_2.is_even is False
    assert result_2.is_positive is True
    assert result_2.classification == "odd_positive"

    # Testa com número par negativo
    result_3 = await classify_number("O número é: -6")
    assert isinstance(result_3, NumberClassification)
    assert result_3.number == -6
    assert result_3.is_even is True
    assert result_3.is_positive is False
    assert result_3.classification == "even_negative"

    # Testa com número ímpar negativo
    result_4 = await classify_number("O número é: -3")
    assert isinstance(result_4, NumberClassification)
    assert result_4.number == -3
    assert result_4.is_even is False
    assert result_4.is_positive is False
    assert result_4.classification == "odd_negative"


@pytest.mark.asyncio
async def test_structured_output_simple():
    """
    Testa structured output simples com informação pessoal.

    Este teste verifica que a biblioteca consegue extrair informação
    estruturada de texto natural e retornar como objeto Pydantic.
    """

    class PersonInfo(BaseModel):
        """Informação sobre uma pessoa."""
        name: str
        age: int
        city: str

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[]
    )
    async def extract_person_info(text: str) -> PersonInfo:
        """
        Extrai informação estruturada sobre a pessoa do texto: {text}
        """

    # A biblioteca faz o parse automático e retorna o objeto Pydantic
    result = await extract_person_info("João tem 25 anos e mora em São Paulo")

    assert isinstance(result, PersonInfo)
    assert result.name.lower() == "joão"
    assert result.age == 25
    assert "paulo" in result.city.lower() or "são paulo" in result.city.lower()
