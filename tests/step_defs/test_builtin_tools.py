"""
BDD tests for Built-in Tools - Tools that come with the library.

Validates that:
- Python Runner executes arbitrary Python code
- Calculator evaluates mathematical expressions
- Clock/Today returns current date and time
"""
import sys
import importlib.util
from datetime import datetime
from pytest_bdd import scenarios, given, when, then, parsers
from pytest import fixture
import asyncio
import functools

from liteagent import agent
from liteagent.providers import openai


def async_to_sync(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))
    return wrapper


# Load all scenarios from builtin_tools.feature
scenarios('../features/builtin_tools.feature')


# ==================== FIXTURES ====================

@fixture
def builtin_tools_fixture():
    """Loads built-in tools without going through __init__.py to avoid optional dependencies."""
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


@fixture
def builtin_context():
    """Context to store test state."""
    return {}


# ==================== GIVEN STEPS ====================

@given("the built-in tools are loaded")
def given_builtin_tools_loaded(builtin_tools_fixture):
    """Ensure built-in tools are loaded."""
    assert builtin_tools_fixture is not None


@given(parsers.parse('an agent with the "{tool_name}" tool'), target_fixture="test_agent")
def given_agent_with_builtin_tool(builtin_tools_fixture, tool_name, builtin_context):
    """Create an agent with a specific built-in tool."""
    tool = builtin_tools_fixture[tool_name]

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=[tool]
    )
    async def builtin_agent(query: str) -> str:
        """
        Answer: {query}
        Use the available tools to answer the question.
        """

    builtin_context['agent'] = builtin_agent
    return builtin_agent


@given(parsers.parse('an agent with the tools "{tool_list}"'), target_fixture="test_agent")
def given_agent_with_multiple_builtin_tools(builtin_tools_fixture, tool_list, builtin_context):
    """Create an agent with multiple built-in tools."""
    tool_names = [name.strip() for name in tool_list.split(',')]
    tools = [builtin_tools_fixture[name] for name in tool_names]

    @agent(
        provider=openai(model="gpt-4o-mini", temperature=0),
        tools=tools
    )
    async def multi_builtin_agent(query: str) -> str:
        """
        Answer: {query}
        Use python_runner for complex code or calculator for simple expressions.
        """

    builtin_context['agent'] = multi_builtin_agent
    return multi_builtin_agent


# ==================== WHEN STEPS ====================

@when(parsers.parse('I ask the agent "{query}"'), target_fixture="agent_response")
def when_ask_builtin_agent(builtin_context, query, extract_text):
    """Ask the agent a question."""
    agent_func = builtin_context.get('agent')
    assert agent_func is not None, "No agent found in context"

    async def _ask():
        result = await agent_func(query)
        return await extract_text(result)

    return async_to_sync(_ask)()


# ==================== THEN STEPS ====================

@then("the response should contain the current year")
def then_response_contains_current_year(agent_response):
    """Validate that response contains the current year."""
    current_year = str(datetime.now().year)
    assert current_year in agent_response, f"Expected current year {current_year} in response, got: {agent_response}"
