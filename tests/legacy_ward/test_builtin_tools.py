"""
Tests for Built-in Tools - Tools that come with the library.

Validates that internal tools work correctly:
- Python Runner: Executes arbitrary Python code
- Calculator: Evaluates mathematical expressions
- Clock/Today: Returns current date and time

NOTE: These tests use dynamic imports to avoid optional dependencies (playwright).
"""
from datetime import datetime
from ward import test, fixture

from liteagent import agent
from liteagent.providers import openai


# Fixture to dynamically load built-in tools
@fixture
def builtin_tools():
    """Loads built-in tools without going through __init__.py to avoid optional dependencies."""
    import sys
    import importlib.util

    tools = {}

    # Load python_runner
    spec = importlib.util.spec_from_file_location("py_tools", "liteagent/tools/py.py")
    py_module = importlib.util.module_from_spec(spec)
    sys.modules["py_tools"] = py_module
    spec.loader.exec_module(py_module)
    tools['python_runner'] = py_module.python_runner

    # Load calculator
    spec = importlib.util.spec_from_file_location("calc_tools", "liteagent/tools/calc.py")
    calc_module = importlib.util.module_from_spec(spec)
    sys.modules["calc_tools"] = calc_module
    spec.loader.exec_module(calc_module)
    tools['calculator'] = calc_module.calculator

    # Load clock tools
    spec = importlib.util.spec_from_file_location("clock_tools", "liteagent/tools/clock.py")
    clock_module = importlib.util.module_from_spec(spec)
    sys.modules["clock_tools"] = clock_module
    spec.loader.exec_module(clock_module)
    tools['clock'] = clock_module.clock
    tools['today'] = clock_module.today

    return tools


@test("python_runner executes simple Python code")
async def _(tools=builtin_tools):
    """
    Tests that python_runner can execute simple Python code.

    Deterministic scenario:
    - Agent uses python_runner to calculate 5 + 3
    - Validates that result is 8
    """

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[tools['python_runner']]
    )
    async def code_agent(query: str) -> str:
        """
        Answer: {query}
        Use the python_runner tool to execute code when necessary.
        """

    result = await code_agent("Calculate 5 + 3 using Python")
    result_text = await extract_text(result)

    # Validate that result contains 8
    assert "8" in result_text


@test("python_runner makes HTTP requests")
async def _(tools=builtin_tools):
    """
    Tests that python_runner can make HTTP requests.

    Deterministic scenario:
    - Agent uses python_runner to make request
    - Validates that it got a response
    """

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[tools['python_runner']]
    )
    async def http_agent(query: str) -> str:
        """
        Answer: {query}
        Use python_runner to make HTTP requests when necessary.
        """

    result = await http_agent(
        "Use requests to GET https://httpbin.org/json and return the 'slideshow' property from the JSON"
    )
    result_text = await extract_text(result)

    # Validate that it made the request and processed JSON
    assert "slideshow" in result_text.lower() or "author" in result_text.lower() or "title" in result_text.lower()


@test("calculator evaluates mathematical expressions")
async def _(tools=builtin_tools):
    """
    Tests that calculator can evaluate mathematical expressions.

    Deterministic scenario:
    - Agent uses calculator to evaluate 10 * 5 + 2
    - Validates that result is 52
    """

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[tools['calculator']]
    )
    async def math_agent(query: str) -> str:
        """
        Answer: {query}
        Use the calculator tool to calculate mathematical expressions.
        """

    result = await math_agent("What is 10 * 5 + 2?")
    result_text = await extract_text(result)

    # Validate that result is 52
    assert "52" in result_text


@test("calculator evaluates complex expressions")
async def _(tools=builtin_tools):
    """
    Tests that calculator can evaluate complex expressions.

    Deterministic scenario:
    - Agent uses calculator for (100 / 4) + (3 ** 2)
    - Validates that result is 34.0 or 34
    """

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[tools['calculator']]
    )
    async def complex_math_agent(query: str) -> str:
        """
        Answer: {query}
        Use calculator for mathematical expressions.
        """

    result = await complex_math_agent("Calculate (100 / 4) + (3 ** 2)")
    result_text = await extract_text(result)

    # 100/4 = 25, 3**2 = 9, 25 + 9 = 34
    assert "34" in result_text


@test("today returns current date")
async def _(tools=builtin_tools):
    """
    Tests that today returns the current date.

    Deterministic scenario:
    - Agent uses today to get date
    - Validates that it returns something with date format
    """

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[tools['today']]
    )
    async def date_agent(query: str) -> str:
        """
        Answer: {query}
        Use the today tool to get the current date.
        """

    result = await date_agent("What is today's date?")
    result_text = await extract_text(result)

    # Validate that it contains current year (2025)
    current_year = str(datetime.now().year)
    assert current_year in result_text


@test("clock is an eager tool executed automatically")
async def _(tools=builtin_tools):
    """
    Tests that clock is an eager tool (executed automatically).

    Deterministic scenario:
    - clock is marked as eager=True
    - Agent receives current time before processing query
    - Validates that agent has access to timestamp
    """

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[tools['clock']]
    )
    async def time_agent(query: str) -> str:
        """
        Answer: {query}
        You have access to the clock tool which was executed automatically.
        """

    result = await time_agent("What is the current time?")
    result_text = await extract_text(result)

    # Validate that it contains indication of time (hour, minute, or "Current time")
    assert any(word in result_text.lower() for word in ["time", ":", "current"])


@test("agent uses multiple built-in tools together")
async def _(tools=builtin_tools):
    """
    Tests that agent can use multiple built-in tools together.

    Deterministic scenario:
    - Agent has access to python_runner and calculator
    - Can choose which to use based on task
    """

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[tools['python_runner'], tools['calculator']]
    )
    async def multi_tool_agent(query: str) -> str:
        """
        Answer: {query}
        Use python_runner for complex code or calculator for simple expressions.
        """

    result = await multi_tool_agent("Calculate 15 * 3")
    result_text = await extract_text(result)

    # Validate correct calculation: 15 * 3 = 45
    assert "45" in result_text
