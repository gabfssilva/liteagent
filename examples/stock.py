import asyncio

from liteagent import agent
from liteagent.providers import openai
from liteagent.tools import yfinance


@agent(
    tools=[yfinance],
    provider=openai()
)
async def stock_agent(tickers: list[str]) -> str:
    """
    - Check the stock price of {tickers}.
    - Check also the news.
    - In amarkdown table, provide the following:

    | Ticker | Current Price | Recommendations | Recent News | Your Take |
    | --- | --- | --- | --- | --- |
    | EXMPL1 | 100.00 | Strong Buy: 11, Buy: 47, Hold: 4 | [EXMPL1 gone wild](https://link) | Investing in EXMPL1 seems to be a great deal as... |
    """


asyncio.run(stock_agent(tickers=['NVDA', 'AAPL', 'MSFT', 'TSLA']))
