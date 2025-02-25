import asyncio

from pydantic import BaseModel

from liteagent import agent, tool
from liteagent.providers import claude, openai


class Person(BaseModel):
    name: str
    age: int
    occupation: str
    favorite_color: str
    favorite_weather: str
    favorite_food: str


@tool
def personal_info() -> Person:
    return Person(
        name="Gabriel",
        age=32,
        occupation="Software Engineer",
        favorite_color="Blue",
        favorite_weather="Cold",
        favorite_food="Pizza"
    )


@agent(
    provider=claude(model='claude-3-7-sonnet-20250219'),
    tools=[personal_info],
    description="You are a helpful assistant that answers questions about the person.",
)
async def claude_agent() -> str:
    """
    Who am I? Provide a short summary about me based on the information you can gather.
    """


if __name__ == "__main__":
    asyncio.run(claude_agent())
