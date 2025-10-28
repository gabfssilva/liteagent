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
    """
    import json

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
        - Retorna a classificação apropriada no formato JSON
        """

    async def get_classification(number: int) -> NumberClassification:
        """Helper para parsear o resultado do agent."""
        result = await classify_number(f"O número é: {number}", stream=True)
        messages = [msg async for msg in result]

        for msg in messages:
            if hasattr(msg.content, 'content'):
                content_str = await msg.content.await_complete() if hasattr(msg.content, 'await_complete') else str(msg.content.content)
                data = json.loads(content_str)
                return NumberClassification(**data)

        raise ValueError("No classification found in messages")

    # Testa com número par positivo
    result_1 = await get_classification(4)
    assert isinstance(result_1, NumberClassification)
    assert result_1.number == 4
    assert result_1.is_even is True
    assert result_1.is_positive is True
    assert result_1.classification == "even_positive"

    # Testa com número ímpar positivo
    result_2 = await get_classification(7)
    assert isinstance(result_2, NumberClassification)
    assert result_2.number == 7
    assert result_2.is_even is False
    assert result_2.is_positive is True
    assert result_2.classification == "odd_positive"

    # Testa com número par negativo
    result_3 = await get_classification(-6)
    assert isinstance(result_3, NumberClassification)
    assert result_3.number == -6
    assert result_3.is_even is True
    assert result_3.is_positive is False
    assert result_3.classification == "even_negative"

    # Testa com número ímpar negativo
    result_4 = await get_classification(-3)
    assert isinstance(result_4, NumberClassification)
    assert result_4.number == -3
    assert result_4.is_even is False
    assert result_4.is_positive is False
    assert result_4.classification == "odd_negative"


@pytest.mark.asyncio
async def test_structured_output_simple():
    """
    Testa structured output simples com informação pessoal.

    Este teste é mais simples e verifica apenas que o formato está correto.
    """
    import json

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

    result = await extract_person_info("João tem 25 anos e mora em São Paulo", stream=True)

    messages = [msg async for msg in result]
    print(f"\nMessages: {len(messages)}")

    for msg in messages:
        print(f"Message type: {type(msg).__name__}")
        print(f"Content type: {type(msg.content).__name__}")
        if hasattr(msg.content, 'content'):
            content_str = await msg.content.await_complete() if hasattr(msg.content, 'await_complete') else str(msg.content.content)
            print(f"Content string: {content_str}")

            # Parse JSON and create PersonInfo
            data = json.loads(content_str)
            person = PersonInfo(**data)

            print(f"Parsed PersonInfo: {person}")

            # Assertions
            assert person.name.lower() == "joão"
            assert person.age == 25
            assert "paulo" in person.city.lower() or "são paulo" in person.city.lower()

            print("✓ Test passed!")
            return

    assert False, "No valid PersonInfo found in messages"
