import asyncio

from liteagent import agent
from liteagent.auditors import minimal
from liteagent.providers import openai
from liteagent.tools import OpenMeteo


@agent(
    description="You're a weather agent. Use your tools to fetch information about the weather.",
    tools=[OpenMeteo()],
    provider=openai(model='gpt-4o-mini'),
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
