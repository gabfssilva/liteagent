# CLAUDE.md - LiteAgent Development Guide

This file contains essential information for AI assistants and developers working on the LiteAgent codebase.

## AI Assistant Profile

**You are a senior software engineering agent** with extensive experience in:
- Software architecture and design patterns
- Test-driven development (TDD) and behavior-driven development (BDD)
- Python best practices and async/await patterns
- Code quality, maintainability, and SOLID principles
- Writing comprehensive, reliable tests

**Core Principles:**
- **Quality over speed**: 100% test pass rate is mandatory, not optional
- **Best practices first**: Always follow established patterns and conventions
- **Complete solutions**: Partial implementations are unacceptable
- **Clean code**: Readable, maintainable, well-documented code is the baseline

**Testing Philosophy:**
- **All tests must pass (100% pass rate required)** - 85% passing is 0% success
- Tests should be deterministic and reliable
- BDD scenarios should be clear and complete
- No flaky tests, no "good enough" solutions

**Documentation Philosophy:**
- **NEVER create markdown files (.md) unless explicitly requested by the user**
- Only essential markdown files should exist: README.md, CLAUDE.md, LICENSE.md
- Documentation belongs in code comments, docstrings, and commit messages
- Temporary documentation files clutter the repository

## Project Overview

**LiteAgent** is a lightweight Python framework for building intelligent agents powered by Large Language Models (LLMs). It provides a simple, decorator-based API for creating AI agents that can use tools and coordinate with other agents.

**Status**: Heavily under development - not for production use
**Python Version**: 3.12 (strict)
**Package Manager**: UV

## Quick Start

### Setup Development Environment

```bash
# Install all dependencies including dev group
uv sync --group dev

# Install with specific optional groups
uv sync --group dev --group providers --group vectordb
```

### Running Tests

**The test suite uses pytest-bdd with Gherkin features** for behavior-driven development.

```bash
# Run all BDD tests (must be 100% passing)
uv run pytest tests/step_defs/ -v

# Run specific test suite
uv run pytest tests/step_defs/test_tool_calling.py -v

# Run with HTML report
uv run pytest tests/step_defs/ --html=report.html --self-contained-html

# Run with detailed output
uv run pytest tests/step_defs/ -vv --tb=short
```

**IMPORTANT**: All tests must pass (100% pass rate). Partial test success is not acceptable.
"85% passing" means "0% success" - either all tests pass or the work is incomplete.

### Running Examples

```bash
# Run any example
uv run python examples/hello_agent.py

# Examples require API keys
export OPENAI_API_KEY="your-key"
uv run python examples/multi_agent_chatbot.py
```

## Project Structure

```
liteagent/
├── liteagent/              # Main package
│   ├── __init__.py         # Public API exports
│   ├── agent.py            # Agent class - core execution logic
│   ├── tool.py             # Tool class and definitions
│   ├── decorators.py       # @agent, @tool, @team decorators
│   ├── provider.py         # Provider abstract base class
│   ├── message.py          # Message types (User, Assistant, Tool, System)
│   ├── session.py          # Session management for stateful conversations
│   ├── providers/          # LLM Provider implementations (OpenAI, Claude, etc)
│   ├── tools/              # Built-in tool implementations (25+ tools)
│   ├── vector/             # Vector database implementations and RAG
│   ├── bus/                # Event bus for pub-sub pattern
│   └── internal/           # Internal utilities
├── tests/                  # Test suite (pytest-bdd with Gherkin features)
├── examples/               # Example scripts (17+ examples)
├── pyproject.toml          # Project metadata and dependencies
├── pytest.ini              # Test configuration
└── uv.lock                 # Locked dependencies
```

## Core Components

### 1. Agent (`liteagent/agent.py`)
- Central orchestration class managing LLM interaction
- Key methods:
  - `__call__()` - Execute agent with async streaming or final result
  - `as_tool()` - Convert agent to reusable tool
  - `with_tool()` - Add tools dynamically

### 2. Tool (`liteagent/tool.py`)
- Represents executable functions available to agents
- Three ways to define tools:
  - Function decorator: `@tool`
  - Class-based: `class MyTools(Tools)`
  - Agent as tool: `agent.as_tool()`

### 3. Provider (`liteagent/provider.py`)
- Abstract interface for LLM backends
- Implementations in `liteagent/providers/`:
  - OpenAI, Anthropic (Claude), Google (Gemini), Ollama, Azure AI

### 4. Message (`liteagent/message.py`)
- Types: `SystemMessage`, `UserMessage`, `AssistantMessage`, `ToolMessage`
- Supports streaming with `TextStream` and `ToolUseStream`

### 5. Session (`liteagent/session.py`)
- Manages stateful conversation history
- Methods: `__call__()`, `summarize()`, `reset()`

## Development Workflow

### Adding a New Provider

1. Create file in `liteagent/providers/{provider_name}/`
2. Extend `Provider` abstract class
3. Implement `completion()` method returning `AsyncIterable[Message]`
4. Add factory function in `liteagent/providers/providers.py`
5. Export in `liteagent/providers/__init__.py`
6. Add tests in `tests/test_providers.py`

### Adding a New Tool

1. Create file in `liteagent/tools/` (e.g., `my_tool.py`)
2. Use `@tool` decorator or extend `Tools` class
3. Add proper type hints (Pydantic models for parameters)
4. Document with docstrings
5. Export in `liteagent/tools/__init__.py`
6. Add tests in `tests/test_tools/`

### Adding a New Test

1. Create `.feature` file in `tests/features/` with Gherkin scenarios:
   ```gherkin
   Feature: My Feature
     As a developer
     I want to test functionality
     So that the system works correctly

     Scenario: My test scenario
       Given some precondition
       When I perform an action
       Then I should see the expected result
   ```
2. Create `test_*.py` file in `tests/step_defs/` with step definitions:
   ```python
   from pytest_bdd import scenarios, given, when, then, parsers

   scenarios('../features/my_feature.feature')

   @given("some precondition")
   def given_precondition():
       # Setup code

   @when("I perform an action", target_fixture="result")
   def when_action():
       # Action code
       return result

   @then("I should see the expected result")
   def then_result(result):
       assert result == expected
   ```
3. Use `conftest.py` utilities like `extract_text()` for parsing responses
4. Use `async_to_sync` wrapper for async operations
5. Run with `uv run pytest tests/step_defs/test_*.py -v`

## Environment Variables

Required API keys for different providers:

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic (Claude)
export ANTHROPIC_API_KEY="sk-ant-..."

# Google Gemini
export GEMINI_API_KEY="..."

# Other providers
export OPENROUTER_API_KEY="..."
export DEEPSEEK_API_KEY="..."
export GITHUB_TOKEN="..."
```

## Dependency Groups

Install optional features using UV groups:

```bash
# Basic (core + OpenAI)
uv sync --group basic

# All LLM providers
uv sync --group providers

# Vector databases
uv sync --group vectordb

# RAG/Vector + Embeddings full stack
uv sync --group rag

# Web tools
uv sync --group web

# Everything except dev
uv sync --group full

# Development tools (testing, profiling)
uv sync --group dev
```

## Testing Guidelines

### Test Categories (93 BDD scenarios total)

**Core Agent Tests:**
- `test_tool_calling.py` - Tool invocation and parameter passing (3 scenarios)
- `test_sessions.py` - Stateful conversation management (2 scenarios)
- `test_structured_output.py` - Pydantic model responses (5 scenarios)
- `test_streaming.py` - Real-time message streaming (4 scenarios)
- `test_agent_teams.py` - Multi-agent coordination (4 scenarios)
- `test_error_handling.py` - Error handling and validation (5 scenarios)

**Built-in Tools Tests:**
- `test_builtin_tools.py` - Python runner, calculator, clock (7 scenarios)
- `test_files.py` - File system operations (19 scenarios)
- `test_memoria.py` - Long-term memory storage/retrieval (10 scenarios)
- `test_vector_db.py` - Vector database and RAG (9 scenarios)
- `test_wikipedia.py` - Wikipedia search and article fetching (6 scenarios)
- `test_yfinance.py` - Yahoo Finance stock data (9 scenarios)

**Internal Tests:**
- `test_cached_iterator.py` - Cached async iteration (10 scenarios)

### Test Configuration

Located in `pytest.ini`:
- `asyncio_mode = auto` - Automatic async test handling
- Tests auto-discovered in `tests/` directory
- Pattern: `test_*.py`, `Test*`, `test_*`

## Common Tasks

### Run specific test
```bash
uv run pytest tests/step_defs/test_tool_calling.py -v
```

### Run with profiling
```bash
uv run py-spy record -o profile.svg -- python your_script.py
```

### Check dependencies
```bash
uv tree
```

### Add new dependency
```bash
# Add to core dependencies
uv add package-name

# Add to specific group
uv add --group dev package-name
```

### Update dependencies
```bash
uv sync
```

## Architecture Patterns

### Async-First Design
- All operations use `asyncio`
- Sync functions auto-offloaded to threads via `asyncio.to_thread()`
- Streaming via async generators

### Event Bus Pattern
- Located in `bus/eventbus.py`
- Pub-sub system for monitoring agent execution
- Events: `AgentCallEvent`, `SystemMessageEvent`, `UserMessageEvent`, etc.

### Provider Pattern
- Each provider extends `Provider` abstract class
- Implements `completion()` returning `AsyncIterable[Message]`
- Handles conversion to/from provider's message format

### Tool Definition Pattern
- Decorators create `FunctionToolDef` instances
- Pydantic models for type-safe parameters
- JSON Schema generated for LLM function calling

## Example Code

### Simple Agent
```python
import asyncio
from liteagent import agent, tool
from liteagent.providers import openai

@tool
def get_weather(city: str) -> str:
    return f"Sunny in {city}"

@agent(provider=openai(model="gpt-4o-mini"), tools=[get_weather])
async def weather_bot(city: str) -> str:
    """What's the weather in {city}?"""

asyncio.run(weather_bot("Paris"))
```

### Multi-Agent Team
```python
from liteagent import agent, team
from liteagent.providers import claude

@agent(provider=claude())
async def researcher(topic: str) -> str:
    """Research the topic: {topic}"""

@agent(provider=claude())
async def writer(research: str) -> str:
    """Write based on: {research}"""

@team(name="content_team", agents=[researcher, writer], provider=claude())
async def content_creator(topic: str) -> str:
    """Create content about {topic}"""
```

### With Sessions
```python
from liteagent import session, agent
from liteagent.providers import openai

@agent(provider=openai())
async def chatbot(msg: str) -> str:
    """Respond to: {msg}"""

s = session(chatbot)
async for message in s("Hello!"):
    print(message)
async for message in s("Remember what I said?"):
    print(message)
```

## Important Files

- `pyproject.toml` - Project metadata, dependencies, and configuration
- `pytest.ini` - Test configuration for pytest-bdd
- `uv.lock` - Locked dependency versions (don't edit manually)
- `liteagent/__init__.py` - Public API exports
- `tests/conftest.py` - Test utilities and fixtures
- `tests/features/` - Gherkin feature files for BDD tests
- `tests/step_defs/` - pytest-bdd step definitions

## Key Differences from Other Frameworks

1. **UV Package Manager** - Not pip/poetry, use `uv` commands
2. **pytest-bdd with Gherkin** - Behavior-driven development with feature files
3. **Async-First** - Everything is async, no sync wrapper APIs
4. **Decorator-Based** - Primary interface is via `@agent` and `@tool`
5. **Event Bus** - Built-in pub-sub for monitoring without code modification

## Debugging Tips

### Enable Debug Logging
```python
import structlog
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
)
```

### Use Event Bus for Monitoring
```python
from liteagent import bus
from liteagent.events import AssistantMessageEvent

@bus.on(AssistantMessageEvent)
async def log_assistant(event):
    print(f"Assistant: {event.message}")
```

### Profile Performance
```bash
uv run py-spy record -o profile.svg -- python your_script.py
```

## Contributing Guidelines

1. **Always run tests** before committing: `uv run pytest tests/step_defs/ -v`
2. **All tests must pass** - 100% pass rate required, 85% is 0%
3. **Add BDD tests** for new features:
   - Create `.feature` file in `tests/features/`
   - Create step definitions in `tests/step_defs/`
4. **Update documentation** if adding public APIs (in code, not new .md files)
5. **Use type hints** - Pydantic models for complex types
6. **Async-first** - All new code should be async-compatible
7. **Follow existing patterns** - See examples in codebase

## Known Limitations

- Python 3.12 only (strict requirement)
- Not production-ready (active development)
- Some providers may have incomplete implementations
- Vector database backends require optional dependencies

## Resources

- Main README: `/home/user/liteagent/README.md`
- Examples: `/home/user/liteagent/examples/`
- Tests: `/home/user/liteagent/tests/`
- License: MIT (`/home/user/liteagent/LICENSE.md`)

## Last Updated

This guide reflects the codebase state as of the latest commit:
- Branch: `claude/explore-codebase-011CUaq1pi5CrbfYk3rJhdJ2`
- Recent work: Terminal UI removal, Memoria tests, dependency sync
