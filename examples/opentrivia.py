import asyncio
from typing import Literal, List

from pydantic import BaseModel

from liteagent import agent
from liteagent.providers import github
from liteagent.tools import py


class Question(BaseModel):
    difficulty: Literal["easy", "medium", "hard"]
    question: str
    correct_answer: str
    incorrect_answers: list[str]


class Questions(BaseModel):
    questions: List[Question]


@agent(
    provider=github(model="gpt-4o"),
    tools=[py.python_runner],
    description="You are a python runner. You resolve all of your tasks using Python."
)
async def questions(amount: int, difficulty: Literal["easy", "medium", "hard"]) -> Questions:
    """
    Send a request to https://opentdb.com/api.php?amount={amount}&category=20&difficulty={difficulty}
    Then, return the questions.
    """


if __name__ == "__main__":
    print(asyncio.run(questions(amount=5, difficulty="easy")))
