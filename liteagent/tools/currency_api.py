from pydantic import Field

from liteagent import Tools, tool
from liteagent.tools import http

class CurrencyApi(Tools):
    @tool(emoji='💱')
    @http(url='https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies.json')
    async def get_currencies(self) -> list[str]:
        """ use this tool to fetch a list of currencies """

    @tool(emoji='💱')
    @http(url='https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{base_currency}.json')
    async def get_currency(self, base_currency: str = Field(..., description="in lowercase")) -> str:
        """ use this tool to fetch the current exchange rate of the currencies with the base currency """

currency_api = CurrencyApi()
