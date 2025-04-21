from typing import Literal

from pydantic import Field

from liteagent import tool, Tools
from liteagent.internal import depends_on


class YFinance(Tools):
    @tool(emoji='💹')
    @depends_on({"yfinance": "yfinance"})
    def get_stock_info(self, ticker: str = Field(...,
                                                 description="unique symbol assigned to a publicly traded company on a stock exchange. e.g. AAPL, TSLA, GOOGL, MSFT, AMZN, etc.")) -> dict:
        """Retrieves general information about the given stock ticker."""
        import yfinance as yf

        stock = yf.Ticker(ticker)
        return stock.info

    @tool(emoji='📈')
    @depends_on({"yfinance": "yfinance"})
    def get_historical_data(
        self,
        period: Literal['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'],
        interval: Literal['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1d', '5d', '1wk', '1mo', '3mo'],
        ticker: str = Field(...,
                            description="unique symbol assigned to a publicly traded company on a stock exchange. e.g. AAPL, TSLA, GOOGL, MSFT, AMZN, etc."),
    ) -> dict:
        """Fetches historical market data for the given stock ticker. """
        import yfinance as yf

        stock = yf.Ticker(ticker)
        data = stock.history(period=period, interval=interval)
        return data.to_dict()

    @tool(emoji='📊')
    @depends_on({"yfinance": "yfinance"})
    def get_financials(self, ticker: str = Field(...,
                                                 description="unique symbol assigned to a publicly traded company on a stock exchange. e.g. AAPL, TSLA, GOOGL, MSFT, AMZN, etc.")) -> dict:
        """Retrieves financial statements such as income statements, balance sheets, and cash flow statements."""
        import yfinance as yf

        stock = yf.Ticker(ticker)
        return {
            "income_statement": stock.get_financials(as_dict=True),
            "balance_sheet": stock.get_balance_sheet(as_dict=True),
            "cash_flow": stock.get_cash_flow(as_dict=True)
        }

    @tool(emoji='📡')
    @depends_on({"yfinance": "yfinance"})
    def get_recommendations(self, ticker: str = Field(...,
                                                      description="unique symbol assigned to a publicly traded company on a stock exchange. e.g. AAPL, TSLA, GOOGL, MSFT, AMZN, etc.")) -> str:
        """Fetches analyst recommendations for the given stock ticker."""
        import yfinance as yf

        stock = yf.Ticker(ticker)
        return stock.get_recommendations(as_dict=True)

    @tool(emoji='📰')
    @depends_on({"yfinance": "yfinance"})
    def get_news(self, ticker: str = Field(...,
                                           description="unique symbol assigned to a publicly traded company on a stock exchange. e.g. AAPL, TSLA, GOOGL, MSFT, AMZN, etc.")) -> list:
        """Fetches the latest news related to the given stock ticker."""
        import yfinance as yf

        stock = yf.Ticker(ticker)
        return stock.news

    @tool(emoji='🏛️')
    @depends_on({"yfinance": "yfinance"})
    def get_dividends(self, ticker: str = Field(...,
                                                description="unique symbol assigned to a publicly traded company on a stock exchange. e.g. AAPL, TSLA, GOOGL, MSFT, AMZN, etc.")) -> dict:
        """Fetches the dividend history for the given stock ticker."""
        import yfinance as yf

        stock = yf.Ticker(ticker)
        return stock.dividends.to_dict()

    @tool(emoji='🔍')
    @depends_on({"yfinance": "yfinance"})
    def get_options(self, ticker: str = Field(...,
                                              description="unique symbol assigned to a publicly traded company on a stock exchange. e.g. AAPL, TSLA, GOOGL, MSFT, AMZN, etc.")) -> dict:
        """Retrieves available options expiration dates for the given stock ticker."""
        import yfinance as yf

        stock = yf.Ticker(ticker)
        return {"expiration_dates": stock.options}


yfinance = YFinance()
