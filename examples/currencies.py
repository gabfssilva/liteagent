import asyncio

from liteagent import agent
from liteagent.providers import openai
from liteagent.tools import currency_api, calculator


@agent(tools=[currency_api, calculator], provider=openai())
async def currency_agent(amount_from: str, in_currency: str) -> str:
    """ how much is {amount_from} in {in_currency}? """

if __name__ == "__main__":
    asyncio.run(currency_agent(amount_from='20 BRL', in_currency='USD'))
