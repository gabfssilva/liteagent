
**This library is heavily under development. Do not use it in production.**

**LiteAgent** is a~~nother~~ lightweight Python library that empowers you to build and orchestrate intelligent agents and tools for your applications. By leveraging large language models (or LLMs, for short) from providers such as OpenAI, Ollama,
LlamaCCP, and others, LiteAgent allows your agents to work seamlessly with custom tools to perform complex tasks and respond in a structured manner.

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

## How does it work?

As any agent library, here's your first ~~not very useful~~ agent:

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

When you use the `@agent` and `@tool` decorators, LiteAgent converts your async functions into intelligent agents and tools. The decorators perform several important tasks: they capture the function’s signature and its associated docstring, which acts as a dynamic prompt template. This design enables the agent to format incoming parameters directly into the prompt, making interactions more natural and contextually relevant.

The library is built with asynchronicity in mind. All agents and tools are asynchronous by default, which ensures efficient handling of I/O-bound operations and network requests. However, LiteAgent is also designed to work in
synchronous environments. It carefully offloads synchronous processing to a dedicated CPU thread when needed, giving you the flexibility to choose the most appropriate execution model for your use case.

LiteAgent supports also Structured Outputs, which completely transforms the way you work with your agents by making them way more predictable:

```python
from typing import Literal, List

from pydantic import BaseModel, Field

from liteagent import Agent, agent
from liteagent.providers import ollama, openai, deepseek
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

Another significant strength of LiteAgent lies in its flexible and extensible provider strategy. The library is built to integrate with multiple LLM providers and makes it straightforward to add new ones. This extensibility means that you
can easily swap out or combine providers like OpenAI, Ollama, and LlamaCCP, tailoring the behavior of your agents to the requirements of your application.

LiteAgent also provides a number of tools for you to work with, so you don't have to create everything from scratch:

```python
import asyncio

from liteagent import agent
from liteagent.auditors import minimal
from liteagent.providers import openai
from liteagent.tools import OpenMeteo


@agent(
    description="You're a weather agent. Use your tools to fetch information about the weather.",
    tools=[OpenMeteo()],
    provider=openai(model='gpt-4o-mini'),
    intercept=minimal()
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

Expect additional tools coming soon. 

## Contributing

TODO: come back here later. ;)

## License

LiteAgent is distributed under the MIT License. For full details, please refer to the [LICENSE](LICENSE.md) file.