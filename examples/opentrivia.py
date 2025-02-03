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


if __name__ == '__main__':
    asyncio.run(main())
