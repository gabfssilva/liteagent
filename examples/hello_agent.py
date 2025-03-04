import asyncio

from pydantic import BaseModel

from liteagent import agent, tool
from liteagent.providers import github


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


@agent(
    provider=github(model="Cohere-command-r-plus-08-2024"),
    tools=[personal_info]
)
async def hello_agent() -> str: ...


if __name__ == "__main__":
    asyncio.run(hello_agent("who am I?"))
