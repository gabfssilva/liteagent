# LiteAgent

**This library is heavily under development. Do not use it in production.**

**LiteAgent** is a lightweight Python library that empowers you to build and orchestrate intelligent agents and tools for your applications. By leveraging large language models (LLMs) from providers such as OpenAI, Claude, Gemini, Ollama, LlamaCPP, and others, LiteAgent allows your agents to work seamlessly with custom tools to perform complex tasks and respond in a structured manner.

## Key Features

- **Simple Decorator-Based API**: Create agents with `@agent` and tools with `@tool`
- **Multiple LLM Providers**: Support for OpenAI, Claude, Gemini, Ollama, LlamaCPP, and more
- **Structured Output**: Return type hints with Pydantic models for predictable responses
- **Async by Default**: Built with asynchronicity for efficient I/O operations
- **Built-in Tools**: Web search, RAG, Python execution, API integrations, and more
- **Agent Teams**: Compose multiple agents to solve complex tasks
- **Vision Support**: Process and analyze images with compatible models

## Installation

*... currently not working*

LiteAgent can be installed via your preferred package manager. For example, if you are using UV, you can add LiteAgent with:

```bash
uv add liteagent
```

Alternatively, you can install it using pip:

```bash
pip install liteagent
```

## Quick Start

Here's a simple example of a LiteAgent agent:

```python
import asyncio

from pydantic import BaseModel

from liteagent import agent, tool
from liteagent.providers import ollama


class Person(BaseModel):
    name: str
    age: int
    occupation: str
    favorite_color: str
    favorite_weather: str
    favorite_food: str


@tool
def personal_info() -> Person: return Person(
    name="Gabriel",
    age=32,
    occupation="Software Engineer",
    favorite_color="Blue",
    favorite_weather="Cold",
    favorite_food="Pizza"
)


@agent(provider=ollama(model='llama3.2'), tools=[personal_info])
async def hello_agent() -> str:
    """ who am I? """


asyncio.run(hello_agent())
```

You'll see something like this in your console:

```
(hello_agent) 🗣: who am I?
(hello_agent) 🔧: personal_info()
(hello_agent) 🔄: personal_info() = name='Gabriel' age=32 occupation='Software Engineer' favorite_color='Blue' favor 
...
(hello_agent) 🤖: Based on the information available about you, Gabriel, I can tell you that your favorite color is blue and your occupation is software engineer. Would you like me to provide any other details or answer a specific question related to your profile?
```

## How LiteAgent Works

When you use the `@agent` and `@tool` decorators, LiteAgent converts your async functions into intelligent agents and tools. The decorators capture the function's signature and its associated docstring, which acts as a dynamic prompt template. This design enables the agent to format incoming parameters directly into the prompt, making interactions more natural and contextually relevant.

The library is built with asynchronicity in mind. All agents and tools are asynchronous by default, which ensures efficient handling of I/O-bound operations and network requests. However, LiteAgent is also designed to work in synchronous environments. It carefully offloads synchronous processing to a dedicated CPU thread when needed, giving you the flexibility to choose the most appropriate execution model for your use case.

## Structured Outputs

LiteAgent supports Structured Outputs, which transforms the way you work with your agents by making them more predictable:

```python
from typing import Literal, List

from pydantic import BaseModel, Field

from liteagent import Agent, agent
from liteagent.providers import openai
from liteagent.tools import py

import asyncio

class Question(BaseModel):
    difficulty: Literal["easy", "medium", "hard"]
    question: str
    correct_answer: str
    incorrect_answers: list[str]


class Questions(BaseModel):
    questions: List[Question]


@agent(
    provider=openai(model="o3-mini"),
    tools=[py.python_runner],
    description="You are a python runner. You resolve all of your tasks using Python."
)
async def questions(amount: int, difficulty: Literal["easy", "medium", "hard"]) -> Questions:
    """ Send a request to https://opentdb.com/api.php?amount={amount}&category=20&difficulty={difficulty}
    Then, return the questions. """
    ...


async def main():
    for question in (await questions(amount=15, difficulty="easy")).questions:
        print(question)


asyncio.run(main())
```

## Built-in Tools

LiteAgent provides a variety of tools so you don't have to create everything from scratch:

### Weather Agent Example

```python
import asyncio

from liteagent import agent
from liteagent.providers import openai
from liteagent.tools import openmeteo


@agent(
    description="You're a weather agent. Use your tools to fetch information about the weather.",
    tools=[openmeteo],
    provider=openai(model='gpt-4.1-mini'),
)
async def weather_agent(city: str) -> str:
    """
    Using a markdown table, provide to me the forecast of the next week for {city}.

    The table must contain the following columns:
    - Date (use yyyy-MM-dd)
    - Temperature in °C (e.g. ↓ 10.5° ↑ 20.5°)
    - Chance of Rain % (e.g. 10%)
    - Weather Conditions (e.g. Sunny, Cloudy, etc.)
    """


asyncio.run(weather_agent(city="Sao Paulo"))
```

### RAG (Retrieval-Augmented Generation) Example

```python
import asyncio
from liteagent import agent
from liteagent.providers import openai
from liteagent.tools import vector_store
from liteagent.vector import in_memory, token_chunking
from liteagent.vector.loaders import from_pdf

@agent(
    provider=openai(model="gpt-4.1-mini"),
    tools=[vector_store],
    description="You are a helpful assistant that answers questions based on the provided documents."
)
async def pdf_assistant(query: str) -> str:
    """
    Answer the user's question: {query}
    
    Use the vector search tool to find relevant information in the loaded documents.
    Provide a comprehensive answer based on the document content.
    If the information is not in the documents, politely say so.
    """

async def main():
    # Load documents
    documents = await from_pdf("/path/to/document.pdf")
    
    # Create vector database with documents
    vector_search = await vector_store(
        store=in_memory(),
        initial=[documents],
        chunking_strategy=token_chunking(),
    )
    
    # Query the assistant
    response = await pdf_assistant("What are the key points in chapter 3?")
    print(response)

asyncio.run(main())
```

### Web Search Example

```python
import asyncio
from liteagent import agent
from liteagent.providers import claude
from liteagent.tools import duckduckgo, wikipedia

@agent(
    provider=claude(model="claude-3-haiku-20240307"),
    tools=[duckduckgo, wikipedia.search, wikipedia.get_complete_article],
    description="You are a research assistant that provides accurate information from the web."
)
async def research_agent(topic: str) -> str:
    """
    Research the following topic and provide a comprehensive summary: {topic}
    
    First search the web for recent information, then check Wikipedia for background context.
    Synthesize the information into a well-organized report with:
    1. Brief introduction
    2. Key facts and findings
    3. Different perspectives (if applicable)
    4. Conclusion with the most important takeaways
    """

asyncio.run(research_agent(topic="Recent advances in fusion energy"))
```

### Python Code Execution Example

```python
import asyncio
from liteagent import agent
from liteagent.providers import openai
from liteagent.tools import py

@agent(
    provider=openai(model="gpt-4o"),
    tools=[py.python_runner],
    description="You are a Python coding assistant that solves problems by writing and executing Python code."
)
async def code_agent(task: str) -> str:
    """
    Solve the following task by writing and executing Python code: {task}
    
    1. Think through the problem carefully
    2. Write clean, efficient Python code to solve it
    3. Execute the code to verify your solution
    4. Explain your approach and the results
    """

asyncio.run(code_agent(task="Create a function that finds all prime numbers between 1 and 100 using the Sieve of Eratosthenes algorithm"))
```

## Provider Flexibility

A significant strength of LiteAgent lies in its flexible and extensible provider strategy. The library is built to integrate with multiple LLM providers and makes it straightforward to add new ones. This extensibility means that you can easily swap out or combine providers like OpenAI, Claude, Gemini, Ollama, and LlamaCPP, tailoring the behavior of your agents to the requirements of your application.

```python
# Using OpenAI
from liteagent.providers import openai

@agent(provider=openai(model="gpt-4o"))
async def openai_agent() -> str:
    """What's the capital of France?"""

# Using Claude
from liteagent.providers import claude

@agent(provider=claude(model="claude-3-sonnet-20240229"))
async def claude_agent() -> str:
    """What's the capital of France?"""

# Using Gemini
from liteagent.providers import gemini

@agent(provider=gemini(model="gemini-1.5-pro"))
async def gemini_agent() -> str:
    """What's the capital of France?"""

# Using Ollama (local models)
from liteagent.providers import ollama

@agent(provider=ollama(model="llama3.2"))
async def ollama_agent() -> str:
    """What's the capital of France?"""
```

## Contributing

TODO: come back here later. ;)

## License

LiteAgent is distributed under the MIT License. For full details, please refer to the [LICENSE](LICENSE.md) file.