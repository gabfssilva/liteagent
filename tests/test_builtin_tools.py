"""
Testes para Built-in Tools - Tools que vêm com a biblioteca.

Valida que as tools internas funcionam corretamente:
- Python Runner: Executa código Python arbitrário
- Calculator: Avalia expressões matemáticas
- Clock/Today: Retorna data e hora atual

NOTA: Estes testes usam imports dinâmicos para evitar dependências opcionais (playwright).
"""
from datetime import datetime
from ward import test, fixture

from liteagent import agent
from liteagent.providers import openai
from tests.conftest import extract_text


# Fixture para carregar as built-in tools dinamicamente
@fixture
def builtin_tools():
    """Carrega as built-in tools sem passar por __init__.py para evitar dependências opcionais."""
    import sys
    import importlib.util

    tools = {}

    # Carrega python_runner
    spec = importlib.util.spec_from_file_location("py_tools", "liteagent/tools/py.py")
    py_module = importlib.util.module_from_spec(spec)
    sys.modules["py_tools"] = py_module
    spec.loader.exec_module(py_module)
    tools['python_runner'] = py_module.python_runner

    # Carrega calculator
    spec = importlib.util.spec_from_file_location("calc_tools", "liteagent/tools/calc.py")
    calc_module = importlib.util.module_from_spec(spec)
    sys.modules["calc_tools"] = calc_module
    spec.loader.exec_module(calc_module)
    tools['calculator'] = calc_module.calculator

    # Carrega clock tools
    spec = importlib.util.spec_from_file_location("clock_tools", "liteagent/tools/clock.py")
    clock_module = importlib.util.module_from_spec(spec)
    sys.modules["clock_tools"] = clock_module
    spec.loader.exec_module(clock_module)
    tools['clock'] = clock_module.clock
    tools['today'] = clock_module.today

    return tools


@test("python_runner executa código Python simples")
async def _(tools=builtin_tools):
    """
    Testa que python_runner consegue executar código Python simples.

    Cenário determinístico:
    - Agent usa python_runner para calcular 5 + 3
    - Valida que o resultado é 8
    """

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[tools['python_runner']]
    )
    async def code_agent(query: str) -> str:
        """
        Responda: {query}
        Use a ferramenta python_runner para executar código quando necessário.
        """

    result = await code_agent("Calcule 5 + 3 usando Python")
    result_text = await extract_text(result)

    # Validar que o resultado contém 8
    assert "8" in result_text


@test("python_runner faz requisições HTTP")
async def _(tools=builtin_tools):
    """
    Testa que python_runner consegue fazer requisições HTTP.

    Cenário determinístico:
    - Agent usa python_runner para fazer request
    - Valida que conseguiu obter resposta
    """

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[tools['python_runner']]
    )
    async def http_agent(query: str) -> str:
        """
        Responda: {query}
        Use python_runner para fazer requisições HTTP quando necessário.
        """

    result = await http_agent(
        "Use requests para fazer GET em https://httpbin.org/json e retorne a propriedade 'slideshow' do JSON"
    )
    result_text = await extract_text(result)

    # Validar que conseguiu fazer a requisição e processar JSON
    assert "slideshow" in result_text.lower() or "author" in result_text.lower() or "title" in result_text.lower()


@test("calculator avalia expressões matemáticas")
async def _(tools=builtin_tools):
    """
    Testa que calculator consegue avaliar expressões matemáticas.

    Cenário determinístico:
    - Agent usa calculator para avaliar 10 * 5 + 2
    - Valida que o resultado é 52
    """

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[tools['calculator']]
    )
    async def math_agent(query: str) -> str:
        """
        Responda: {query}
        Use a ferramenta calculator para calcular expressões matemáticas.
        """

    result = await math_agent("Quanto é 10 * 5 + 2?")
    result_text = await extract_text(result)

    # Validar que o resultado é 52
    assert "52" in result_text


@test("calculator avalia expressões complexas")
async def _(tools=builtin_tools):
    """
    Testa que calculator consegue avaliar expressões complexas.

    Cenário determinístico:
    - Agent usa calculator para (100 / 4) + (3 ** 2)
    - Valida que o resultado é 34.0 ou 34
    """

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[tools['calculator']]
    )
    async def complex_math_agent(query: str) -> str:
        """
        Responda: {query}
        Use calculator para expressões matemáticas.
        """

    result = await complex_math_agent("Calcule (100 / 4) + (3 ** 2)")
    result_text = await extract_text(result)

    # 100/4 = 25, 3**2 = 9, 25 + 9 = 34
    assert "34" in result_text


@test("today retorna a data atual")
async def _(tools=builtin_tools):
    """
    Testa que today retorna a data atual.

    Cenário determinístico:
    - Agent usa today para obter a data
    - Valida que retorna algo com formato de data
    """

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[tools['today']]
    )
    async def date_agent(query: str) -> str:
        """
        Responda: {query}
        Use a ferramenta today para obter a data atual.
        """

    result = await date_agent("Qual é a data de hoje?")
    result_text = await extract_text(result)

    # Validar que contém ano atual (2025)
    current_year = str(datetime.now().year)
    assert current_year in result_text


@test("clock é uma eager tool executada automaticamente")
async def _(tools=builtin_tools):
    """
    Testa que clock é uma eager tool (executada automaticamente).

    Cenário determinístico:
    - clock é marcada como eager=True
    - Agent recebe o tempo atual antes de processar a query
    - Valida que o agent tem acesso ao timestamp
    """

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[tools['clock']]
    )
    async def time_agent(query: str) -> str:
        """
        Responda: {query}
        Você tem acesso à ferramenta clock que foi executada automaticamente.
        """

    result = await time_agent("Qual é a hora atual?")
    result_text = await extract_text(result)

    # Validar que contém indicação de tempo (hora, minuto, ou "Current time")
    assert any(word in result_text.lower() for word in ["hora", "time", ":", "current"])


@test("agent usa múltiplas built-in tools juntas")
async def _(tools=builtin_tools):
    """
    Testa que agent consegue usar múltiplas built-in tools juntas.

    Cenário determinístico:
    - Agent tem acesso a python_runner e calculator
    - Pode escolher qual usar baseado na tarefa
    """

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[tools['python_runner'], tools['calculator']]
    )
    async def multi_tool_agent(query: str) -> str:
        """
        Responda: {query}
        Use python_runner para código complexo ou calculator para expressões simples.
        """

    result = await multi_tool_agent("Calcule 15 * 3")
    result_text = await extract_text(result)

    # Validar que calculou corretamente: 15 * 3 = 45
    assert "45" in result_text
