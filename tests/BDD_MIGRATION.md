# Migração para Pytest BDD

Este documento descreve a migração dos testes LiteAgent de Ward para pytest-bdd.

## 📁 Nova Estrutura

```
tests/
├── features/                    # Gherkin feature files (BDD scenarios)
│   ├── tool_calling.feature
│   ├── sessions.feature
│   ├── structured_output.feature
│   └── ...
├── step_defs/                   # Step definitions (Python implementations)
│   ├── conftest.py              # Shared Given/When/Then steps
│   ├── test_tool_calling.py
│   ├── test_sessions.py
│   ├── test_structured_output.py
│   └── ...
├── conftest.py                  # Root fixtures (extract_text, run_async)
├── test_*.py (old)              # Legacy Ward tests (kept for reference)
└── BDD_MIGRATION.md             # This file
```

## ✅ Testes Migrados

| Teste Original | Feature File | Status |
|----------------|--------------|--------|
| test_tool_calling.py | tool_calling.feature | ✅ Completo (3 scenarios) |
| test_sessions.py | sessions.feature | ✅ Completo (2 scenarios) |
| test_structured_output.py | structured_output.feature | ✅ Completo (5 scenarios) |
| test_agent_teams.py | agent_teams.feature | 🚧 Parcial |
| test_streaming.py | - | ⏳ Pendente |
| test_error_handling.py | - | ⏳ Pendente |
| test_memoria.py | - | ⏳ Pendente |

**Total: 10 testes BDD passando** 🎉

## 🔑 Componentes Principais

### 1. Async-to-Sync Wrapper

**Problema**: pytest-bdd não funciona bem com `@pytest.mark.asyncio`

**Solução**: Wrapper `async_to_sync` usando `asyncio.run()`

```python
import asyncio
import functools

def async_to_sync(fn):
    """Wrapper para converter async functions para sync (pytest-bdd)."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))
    return wrapper
```

### 2. Steps Reutilizáveis (step_defs/conftest.py)

**Given Steps**:
- `Given a basic OpenAI agent`
- `Given an agent with the "{tool_name}" tool`
- `Given an agent with the tools "{tool_list}"`
- `Given a stateful session`
- `Given an agent with temperature {temp:f}`

**When Steps**:
- `When I ask the agent "{query}"`
- `When I send the message "{message}" to the session`
- `When I send the message "{message}" to the session and ignore response`
- `When I reset the session`

**Then Steps**:
- `Then the response should contain "{text}"`
- `Then the response should NOT contain "{text}"`
- `Then the response should contain either "{text1}" or "{text2}"`
- `Then the session response should contain "{text}"`
- `Then the session response should NOT contain "{text}"`
- `Then the structured output should have field "{field}" equal to "{value}"`
- `Then the structured output should be of type {type_name}`

### 3. Tool Fixtures

```python
@fixture
def get_user_profile_tool():
    """Fixture for user profile tool."""
    # ...

@fixture
def calculate_age_in_days_tool():
    """Fixture for age calculation tool."""
    # ...
```

## 📝 Como Criar Novos Testes BDD

### Passo 1: Criar Feature File

```gherkin
# tests/features/my_feature.feature
Feature: My New Feature
  As a developer
  I want to test something
  So that I can ensure quality

  Scenario: Test something specific
    Given some precondition
    When I do something
    Then I expect some result
```

### Passo 2: Criar Test File

```python
# tests/step_defs/test_my_feature.py
from pytest_bdd import scenarios, given, when, then

# Load all scenarios from feature file
scenarios('../features/my_feature.feature')

# Additional steps (if needed)
@given("some precondition", target_fixture="my_fixture")
def given_precondition():
    return "something"
```

### Passo 3: Usar Steps Compartilhados

A maioria dos steps já existe em `step_defs/conftest.py`. Você só precisa criar steps específicos do seu teste.

## 🎯 Exemplo Completo: Tool Calling

**Feature File** (`features/tool_calling.feature`):
```gherkin
Feature: Tool Calling
  As a developer using LiteAgent
  I want agents to call tools and use returned data
  So that agents can access external information

  Scenario: Agent calls a single tool
    Given an agent with the "get_user_profile" tool
    When I ask the agent "What is the full name of the user?"
    Then the response should contain "Gabriel Silva"
```

**Test File** (`step_defs/test_tool_calling.py`):
```python
from pytest_bdd import scenarios, given

scenarios('../features/tool_calling.feature')

@given("the OpenAI provider is available")
def given_openai_available():
    import os
    assert os.environ.get("OPENAI_API_KEY")
```

## 🏃 Executando Testes BDD

```bash
# Todos os testes BDD
uv run pytest tests/step_defs/ -v

# Teste específico
uv run pytest tests/step_defs/test_tool_calling.py -v

# Apenas BDD (com marker)
uv run pytest -m bdd -v

# Com relatório HTML
uv run pytest tests/step_defs/ --html=report.html

# Com output detalhado
uv run pytest tests/step_defs/ -v --tb=short
```

## 🔍 Debugging

### Ver fixtures disponíveis:
```bash
uv run pytest --fixtures tests/step_defs/
```

### Ver steps definidos:
```bash
uv run pytest tests/step_defs/ --collect-only
```

### Traceback completo:
```bash
uv run pytest tests/step_defs/ --full-trace
```

## ⚠️ Limitações Conhecidas

1. **Async/Await**: Não é nativo - precisa de wrapper `async_to_sync`
2. **Streaming Tests**: Complexo com BDD - considere manter como pytest puro
3. **Error Handling**: Testes de exceção são verbosos em Gherkin

## 📚 Recursos

- [pytest-bdd Docs](https://pytest-bdd.readthedocs.io/)
- [Gherkin Syntax](https://cucumber.io/docs/gherkin/reference/)
- [pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)

## 🚀 Próximos Passos

1. Migrar test_agent_teams.py
2. Migrar test_streaming.py (considerar pytest puro)
3. Migrar test_error_handling.py
4. Migrar test_memoria.py
5. Migrar testes de vector DB, Wikipedia, etc.
6. Adicionar tags Gherkin (@smoke, @integration)
7. Configurar CI/CD com reports BDD

## 📊 Comparação: Antes vs Depois

### Antes (Ward):
```python
@test("agent can call a tool and use the returned data")
async def _(extract_text):
    @agent(provider=openai(model="gpt-4o-mini"), tools=[get_user_profile])
    async def profile_agent(query: str) -> str:
        """Answer: {query}"""

    result = await profile_agent("What is the user's name?")
    result_text = await extract_text(result)
    assert "Gabriel" in result_text
```

### Depois (pytest-bdd):

**Feature**:
```gherkin
Scenario: Agent calls a tool
  Given an agent with the "get_user_profile" tool
  When I ask the agent "What is the user's name?"
  Then the response should contain "Gabriel"
```

**Test**:
```python
scenarios('../features/tool_calling.feature')
# Steps are reused from conftest.py!
```

**Vantagens**:
- ✅ Mais legível para stakeholders
- ✅ Steps reutilizáveis
- ✅ Separação clara entre cenários e implementação
- ✅ Documentação viva

**Desvantagens**:
- ⚠️ Wrapper async-to-sync necessário
- ⚠️ Mais arquivos para manter
- ⚠️ Curva de aprendizado Gherkin

---

**Última atualização**: 2025-10-29
**Autor**: Claude (via liteagent BDD migration)
