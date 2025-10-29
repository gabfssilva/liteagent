"""
Tests for YFinance Tool - Stock market data retrieval.

Validates that:
- Stock info retrieval works correctly
- Historical data fetching is functional
- Financial statements are retrieved properly
- All tools handle valid tickers
- Tools are properly decorated and registered

NOTE: These tests mock yfinance responses for determinism.
"""
import asyncio
import sys
import importlib.util
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from ward import test, fixture

# Load yfinance module directly without going through tools/__init__.py
# (which has playwright dependency)
spec = importlib.util.spec_from_file_location(
    "liteagent.tools.yfinance",
    "/home/user/liteagent/liteagent/tools/yfinance.py"
)
yfinance_module = importlib.util.module_from_spec(spec)
sys.modules['liteagent.tools.yfinance'] = yfinance_module
spec.loader.exec_module(yfinance_module)
yfinance = yfinance_module.yfinance


# ============================================
# Fixtures - Mock yfinance responses
# ============================================

@fixture
def mock_stock_info():
    """Mock stock.info response."""
    return {
        'symbol': 'AAPL',
        'longName': 'Apple Inc.',
        'sector': 'Technology',
        'industry': 'Consumer Electronics',
        'marketCap': 3000000000000,
        'currentPrice': 180.50,
        'previousClose': 179.25,
        'fiftyTwoWeekHigh': 198.23,
        'fiftyTwoWeekLow': 164.08,
        'currency': 'USD',
        'exchange': 'NASDAQ'
    }


@fixture
def mock_historical_data():
    """Mock stock.history() response as DataFrame-like object."""
    class MockDataFrame:
        def to_dict(self):
            return {
                'Open': {
                    '2024-01-01': 180.0,
                    '2024-01-02': 181.0,
                    '2024-01-03': 182.0,
                    '2024-01-04': 183.0,
                    '2024-01-05': 184.0
                },
                'High': {
                    '2024-01-01': 182.0,
                    '2024-01-02': 183.0,
                    '2024-01-03': 184.0,
                    '2024-01-04': 185.0,
                    '2024-01-05': 186.0
                },
                'Low': {
                    '2024-01-01': 179.0,
                    '2024-01-02': 180.0,
                    '2024-01-03': 181.0,
                    '2024-01-04': 182.0,
                    '2024-01-05': 183.0
                },
                'Close': {
                    '2024-01-01': 181.0,
                    '2024-01-02': 182.0,
                    '2024-01-03': 183.0,
                    '2024-01-04': 184.0,
                    '2024-01-05': 185.0
                },
                'Volume': {
                    '2024-01-01': 1000000,
                    '2024-01-02': 1100000,
                    '2024-01-03': 1200000,
                    '2024-01-04': 1300000,
                    '2024-01-05': 1400000
                }
            }
    return MockDataFrame()


@fixture
def mock_financials():
    """Mock financial statements."""
    return {
        'Total Revenue': {
            '2023-12-31': 394328000000,
            '2022-12-31': 394328000000
        },
        'Net Income': {
            '2023-12-31': 96995000000,
            '2022-12-31': 99803000000
        }
    }


@fixture
def mock_dividends():
    """Mock dividends history as Series-like object."""
    class MockSeries:
        def to_dict(self):
            return {
                '2023-01-01': 0.23,
                '2023-04-01': 0.24,
                '2023-07-01': 0.24,
                '2023-10-01': 0.24
            }
    return MockSeries()


@fixture
def mock_recommendations():
    """Mock analyst recommendations."""
    return {
        'period': ['2024-01-01', '2024-01-02'],
        'strongBuy': [15, 16],
        'buy': [10, 9],
        'hold': [5, 5],
        'sell': [1, 1],
        'strongSell': [0, 0]
    }


@fixture
def mock_news():
    """Mock news articles."""
    return [
        {
            'title': 'Apple announces new product',
            'publisher': 'Reuters',
            'link': 'https://example.com/news1',
            'providerPublishTime': 1704067200
        },
        {
            'title': 'Apple stock rises',
            'publisher': 'Bloomberg',
            'link': 'https://example.com/news2',
            'providerPublishTime': 1704153600
        }
    ]


@fixture
def mock_options():
    """Mock options expiration dates."""
    return ('2024-01-19', '2024-02-16', '2024-03-15')


# ============================================
# Direct Tool Tests (with mocking)
# ============================================

@test("get_stock_info retrieves company information")
def _(mock_info=mock_stock_info):
    """
    Tests that get_stock_info returns valid stock information.

    Deterministic scenario:
    - Mock yfinance.Ticker().info
    - Call get_stock_info handler directly
    - Validate response structure
    """
    with patch('yfinance.Ticker') as mock_ticker:
        mock_instance = Mock()
        mock_instance.info = mock_info
        mock_ticker.return_value = mock_instance

        # Call the handler with self parameter
        result = yfinance.get_stock_info.handler(yfinance, ticker='AAPL')

        assert result['symbol'] == 'AAPL'
        assert result['longName'] == 'Apple Inc.'
        assert result['sector'] == 'Technology'
        assert 'marketCap' in result
        assert 'currentPrice' in result
        mock_ticker.assert_called_once_with('AAPL')


@test("get_historical_data fetches price history")
def _(mock_history=mock_historical_data):
    """
    Tests that get_historical_data returns historical price data.

    Deterministic scenario:
    - Mock yfinance.Ticker().history()
    - Request 5d data
    - Validate DataFrame is converted to dict
    """
    with patch('yfinance.Ticker') as mock_ticker:
        mock_instance = Mock()
        mock_instance.history.return_value = mock_history
        mock_ticker.return_value = mock_instance

        result = yfinance.get_historical_data.handler(
            yfinance,
            ticker='AAPL',
            period='5d',
            interval='1d'
        )

        assert isinstance(result, dict)
        assert 'Open' in result
        assert 'Close' in result
        assert 'Volume' in result
        assert len(result['Open']) == 5
        mock_instance.history.assert_called_once_with(period='5d', interval='1d')


@test("get_financials retrieves financial statements")
def _(mock_fins=mock_financials):
    """
    Tests that get_financials returns income, balance, cash flow.

    Deterministic scenario:
    - Mock all financial statement methods
    - Call get_financials
    - Validate all three statements are present
    """
    with patch('yfinance.Ticker') as mock_ticker:
        mock_instance = Mock()
        mock_instance.get_financials.return_value = mock_fins
        mock_instance.get_balance_sheet.return_value = mock_fins
        mock_instance.get_cash_flow.return_value = mock_fins
        mock_ticker.return_value = mock_instance

        result = yfinance.get_financials.handler(yfinance, ticker='AAPL')

        assert 'income_statement' in result
        assert 'balance_sheet' in result
        assert 'cash_flow' in result
        assert result['income_statement'] == mock_fins
        mock_instance.get_financials.assert_called_once_with(as_dict=True)
        mock_instance.get_balance_sheet.assert_called_once_with(as_dict=True)
        mock_instance.get_cash_flow.assert_called_once_with(as_dict=True)


@test("get_dividends retrieves dividend history")
def _(mock_divs=mock_dividends):
    """
    Tests that get_dividends returns dividend payment history.

    Deterministic scenario:
    - Mock dividends Series
    - Call get_dividends
    - Validate dict conversion
    """
    with patch('yfinance.Ticker') as mock_ticker:
        mock_instance = Mock()
        mock_instance.dividends = mock_divs
        mock_ticker.return_value = mock_instance

        result = yfinance.get_dividends.handler(yfinance, ticker='AAPL')

        assert isinstance(result, dict)
        assert len(result) == 4  # 4 quarters
        # Values should be present
        assert any(val == 0.23 for val in result.values())


@test("get_recommendations retrieves analyst ratings")
def _(mock_recs=mock_recommendations):
    """
    Tests that get_recommendations returns analyst recommendations.

    Deterministic scenario:
    - Mock recommendations data
    - Call get_recommendations
    - Validate structure
    """
    with patch('yfinance.Ticker') as mock_ticker:
        mock_instance = Mock()
        mock_instance.get_recommendations.return_value = mock_recs
        mock_ticker.return_value = mock_instance

        result = yfinance.get_recommendations.handler(yfinance, ticker='AAPL')

        assert 'strongBuy' in result
        assert 'buy' in result
        assert 'hold' in result
        mock_instance.get_recommendations.assert_called_once_with(as_dict=True)


@test("get_news retrieves recent news articles")
def _(mock_articles=mock_news):
    """
    Tests that get_news returns recent news for a ticker.

    Deterministic scenario:
    - Mock news list
    - Call get_news
    - Validate articles structure
    """
    with patch('yfinance.Ticker') as mock_ticker:
        mock_instance = Mock()
        mock_instance.news = mock_articles
        mock_ticker.return_value = mock_instance

        result = yfinance.get_news.handler(yfinance, ticker='AAPL')

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]['title'] == 'Apple announces new product'
        assert result[1]['publisher'] == 'Bloomberg'


@test("get_options retrieves expiration dates")
def _(mock_opts=mock_options):
    """
    Tests that get_options returns options expiration dates.

    Deterministic scenario:
    - Mock options tuple
    - Call get_options
    - Validate dates are returned
    """
    with patch('yfinance.Ticker') as mock_ticker:
        mock_instance = Mock()
        mock_instance.options = mock_opts
        mock_ticker.return_value = mock_instance

        result = yfinance.get_options.handler(yfinance, ticker='AAPL')

        assert 'expiration_dates' in result
        assert len(result['expiration_dates']) == 3
        assert '2024-01-19' in result['expiration_dates']


# ============================================
# Integration Tests with Agents
# ============================================
# NOTE: Agent integration tests removed as they require OpenAI and
# are inherently non-deterministic. The direct tool tests above provide
# sufficient coverage of the yfinance tool functionality.


@test("yfinance tools are properly registered")
def _():
    """
    Tests that all yfinance tools are properly registered.

    Validates:
    - Tool count matches expected
    - All tools have proper metadata
    - Tools are callable
    """
    tools_list = [
        yfinance.get_stock_info,
        yfinance.get_historical_data,
        yfinance.get_financials,
        yfinance.get_recommendations,
        yfinance.get_news,
        yfinance.get_dividends,
        yfinance.get_options
    ]

    assert len(tools_list) == 7

    # Check each tool has required attributes
    for tool in tools_list:
        assert hasattr(tool, 'name')
        assert hasattr(tool, 'definition')
        assert callable(tool)


@test("tools handle different ticker symbols")
def _(mock_info=mock_stock_info):
    """
    Tests that tools work with different ticker symbols.

    Deterministic scenario:
    - Test with multiple tickers
    - Validate tool is called with correct ticker
    """
    with patch('yfinance.Ticker') as mock_ticker:
        mock_instance = Mock()
        mock_instance.info = mock_info
        mock_ticker.return_value = mock_instance

        # Test with different tickers
        tickers = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']

        for ticker in tickers:
            yfinance.get_stock_info.handler(yfinance, ticker=ticker)

        # Should have been called 4 times
        assert mock_ticker.call_count == 4

        # Verify each ticker was passed correctly
        calls = [call[0][0] for call in mock_ticker.call_args_list]
        assert calls == tickers
