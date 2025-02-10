import asyncio
from typing import Literal, List

from pydantic import BaseModel

from liteagent import agent
from liteagent.providers import openai
from liteagent.tools import py


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
    for question in (await questions(amount=5, difficulty="easy")).questions:
        pass


asyncio.run(main())
