"""
BDD tests for YFinance Tool - Stock Market Data Retrieval.

Validates that:
- Stock info retrieval works correctly
- Historical data fetching is functional
- Financial statements are retrieved properly
- All tools handle valid tickers
- Tools are properly decorated and registered
"""
import sys
import importlib.util
from unittest.mock import Mock, patch
from pytest_bdd import scenarios, given, when, then, parsers
from pytest import fixture
import asyncio
import functools


def async_to_sync(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))
    return wrapper


# Load all scenarios from yfinance.feature
scenarios('../features/yfinance.feature')


# ==================== FIXTURES ====================

@fixture
def yfinance_context():
    """Context to store test state."""
    return {}


@fixture
def yfinance_module():
    """Load yfinance module directly."""
    spec = importlib.util.spec_from_file_location(
        "liteagent.tools.yfinance",
        "liteagent/tools/yfinance.py"
    )
    yfinance_module = importlib.util.module_from_spec(spec)
    sys.modules['liteagent.tools.yfinance'] = yfinance_module
    spec.loader.exec_module(yfinance_module)
    return yfinance_module.yfinance


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


# ==================== WHEN STEPS ====================

@when(parsers.parse('I call get_stock_info for ticker "{ticker}"'))
def when_call_get_stock_info(yfinance_module, yfinance_context, mock_stock_info, ticker):
    """Call get_stock_info with mocked yfinance."""
    with patch('yfinance.Ticker') as mock_ticker:
        mock_instance = Mock()
        mock_instance.info = mock_stock_info
        mock_ticker.return_value = mock_instance

        result = yfinance_module.get_stock_info.handler(yfinance_module, ticker=ticker)
        yfinance_context['result'] = result
        yfinance_context['mock_ticker'] = mock_ticker


@when(parsers.parse('I call get_historical_data for ticker "{ticker}" with period "{period}" and interval "{interval}"'))
def when_call_get_historical_data(yfinance_module, yfinance_context, mock_historical_data, ticker, period, interval):
    """Call get_historical_data with mocked yfinance."""
    with patch('yfinance.Ticker') as mock_ticker:
        mock_instance = Mock()
        mock_instance.history.return_value = mock_historical_data
        mock_ticker.return_value = mock_instance

        result = yfinance_module.get_historical_data.handler(
            yfinance_module,
            ticker=ticker,
            period=period,
            interval=interval
        )
        yfinance_context['result'] = result
        yfinance_context['mock_instance'] = mock_instance


@when(parsers.parse('I call get_financials for ticker "{ticker}"'))
def when_call_get_financials(yfinance_module, yfinance_context, mock_financials, ticker):
    """Call get_financials with mocked yfinance."""
    with patch('yfinance.Ticker') as mock_ticker:
        mock_instance = Mock()
        mock_instance.get_financials.return_value = mock_financials
        mock_instance.get_balance_sheet.return_value = mock_financials
        mock_instance.get_cash_flow.return_value = mock_financials
        mock_ticker.return_value = mock_instance

        result = yfinance_module.get_financials.handler(yfinance_module, ticker=ticker)
        yfinance_context['result'] = result
        yfinance_context['mock_instance'] = mock_instance


@when(parsers.parse('I call get_dividends for ticker "{ticker}"'))
def when_call_get_dividends(yfinance_module, yfinance_context, mock_dividends, ticker):
    """Call get_dividends with mocked yfinance."""
    with patch('yfinance.Ticker') as mock_ticker:
        mock_instance = Mock()
        mock_instance.dividends = mock_dividends
        mock_ticker.return_value = mock_instance

        result = yfinance_module.get_dividends.handler(yfinance_module, ticker=ticker)
        yfinance_context['result'] = result


@when(parsers.parse('I call get_recommendations for ticker "{ticker}"'))
def when_call_get_recommendations(yfinance_module, yfinance_context, mock_recommendations, ticker):
    """Call get_recommendations with mocked yfinance."""
    with patch('yfinance.Ticker') as mock_ticker:
        mock_instance = Mock()
        mock_instance.get_recommendations.return_value = mock_recommendations
        mock_ticker.return_value = mock_instance

        result = yfinance_module.get_recommendations.handler(yfinance_module, ticker=ticker)
        yfinance_context['result'] = result
        yfinance_context['mock_instance'] = mock_instance


@when(parsers.parse('I call get_news for ticker "{ticker}"'))
def when_call_get_news(yfinance_module, yfinance_context, mock_news, ticker):
    """Call get_news with mocked yfinance."""
    with patch('yfinance.Ticker') as mock_ticker:
        mock_instance = Mock()
        mock_instance.news = mock_news
        mock_ticker.return_value = mock_instance

        result = yfinance_module.get_news.handler(yfinance_module, ticker=ticker)
        yfinance_context['result'] = result


@when(parsers.parse('I call get_options for ticker "{ticker}"'))
def when_call_get_options(yfinance_module, yfinance_context, mock_options, ticker):
    """Call get_options with mocked yfinance."""
    with patch('yfinance.Ticker') as mock_ticker:
        mock_instance = Mock()
        mock_instance.options = mock_options
        mock_ticker.return_value = mock_instance

        result = yfinance_module.get_options.handler(yfinance_module, ticker=ticker)
        yfinance_context['result'] = result


@when("I check the yfinance tools registration")
def when_check_tools_registration(yfinance_module, yfinance_context):
    """Check that all tools are registered."""
    tools_list = [
        yfinance_module.get_stock_info,
        yfinance_module.get_historical_data,
        yfinance_module.get_financials,
        yfinance_module.get_recommendations,
        yfinance_module.get_news,
        yfinance_module.get_dividends,
        yfinance_module.get_options
    ]
    yfinance_context['tools'] = tools_list


@when(parsers.parse('I call get_stock_info for tickers "{ticker1}", "{ticker2}", "{ticker3}", "{ticker4}"'))
def when_call_get_stock_info_multiple(yfinance_module, yfinance_context, mock_stock_info, ticker1, ticker2, ticker3, ticker4):
    """Call get_stock_info for multiple tickers."""
    tickers = [ticker1, ticker2, ticker3, ticker4]

    with patch('yfinance.Ticker') as mock_ticker:
        mock_instance = Mock()
        mock_instance.info = mock_stock_info
        mock_ticker.return_value = mock_instance

        for ticker in tickers:
            yfinance_module.get_stock_info.handler(yfinance_module, ticker=ticker)

        yfinance_context['mock_ticker'] = mock_ticker
        yfinance_context['tickers'] = tickers


# ==================== THEN STEPS ====================

@then(parsers.parse('the stock info should contain symbol "{symbol}"'))
def then_stock_info_has_symbol(yfinance_context, symbol):
    """Validate stock info contains symbol."""
    result = yfinance_context['result']
    assert result['symbol'] == symbol, f"Expected symbol '{symbol}', got '{result.get('symbol')}'"


@then(parsers.parse('the stock info should contain longName "{name}"'))
def then_stock_info_has_long_name(yfinance_context, name):
    """Validate stock info contains longName."""
    result = yfinance_context['result']
    assert result['longName'] == name, f"Expected longName '{name}', got '{result.get('longName')}'"


@then(parsers.parse('the stock info should contain sector "{sector}"'))
def then_stock_info_has_sector(yfinance_context, sector):
    """Validate stock info contains sector."""
    result = yfinance_context['result']
    assert result['sector'] == sector, f"Expected sector '{sector}', got '{result.get('sector')}'"


@then(parsers.parse('the stock info should have field "{field}"'))
def then_stock_info_has_field(yfinance_context, field):
    """Validate stock info has field."""
    result = yfinance_context['result']
    assert field in result, f"Expected field '{field}' in result: {result.keys()}"


@then(parsers.parse('the historical data should have field "{field}"'))
def then_historical_data_has_field(yfinance_context, field):
    """Validate historical data has field."""
    result = yfinance_context['result']
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert field in result, f"Expected field '{field}' in result: {result.keys()}"


@then(parsers.parse('the historical data field "{field}" should have {count:d} entries'))
def then_historical_data_field_has_entries(yfinance_context, field, count):
    """Validate historical data field has correct number of entries."""
    result = yfinance_context['result']
    assert field in result, f"Expected field '{field}' in result"
    assert len(result[field]) == count, f"Expected {count} entries in '{field}', got {len(result[field])}"


@then(parsers.parse('the financials should have field "{field}"'))
def then_financials_has_field(yfinance_context, field):
    """Validate financials has field."""
    result = yfinance_context['result']
    assert field in result, f"Expected field '{field}' in result: {result.keys()}"


@then("the dividends should be a dict")
def then_dividends_is_dict(yfinance_context):
    """Validate dividends is a dict."""
    result = yfinance_context['result']
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"


@then(parsers.parse('the dividends should have {count:d} entries'))
def then_dividends_has_entries(yfinance_context, count):
    """Validate dividends has correct number of entries."""
    result = yfinance_context['result']
    assert len(result) == count, f"Expected {count} entries, got {len(result)}"


@then(parsers.parse('the dividends should contain value {value:f}'))
def then_dividends_contains_value(yfinance_context, value):
    """Validate dividends contains value."""
    result = yfinance_context['result']
    assert any(val == value for val in result.values()), f"Expected value {value} in dividends"


@then(parsers.parse('the recommendations should have field "{field}"'))
def then_recommendations_has_field(yfinance_context, field):
    """Validate recommendations has field."""
    result = yfinance_context['result']
    assert field in result, f"Expected field '{field}' in result: {result.keys()}"


@then("the news should be a list")
def then_news_is_list(yfinance_context):
    """Validate news is a list."""
    result = yfinance_context['result']
    assert isinstance(result, list), f"Expected list, got {type(result)}"


@then(parsers.parse('the news should have {count:d} articles'))
def then_news_has_articles(yfinance_context, count):
    """Validate news has correct number of articles."""
    result = yfinance_context['result']
    assert len(result) == count, f"Expected {count} articles, got {len(result)}"


@then(parsers.parse('the news article {index:d} should have title "{title}"'))
def then_news_article_has_title(yfinance_context, index, title):
    """Validate news article has title."""
    result = yfinance_context['result']
    assert len(result) > index, f"Not enough articles, expected at least {index + 1}"
    assert result[index]['title'] == title, f"Expected title '{title}', got '{result[index].get('title')}'"


@then(parsers.parse('the news article {index:d} should have publisher "{publisher}"'))
def then_news_article_has_publisher(yfinance_context, index, publisher):
    """Validate news article has publisher."""
    result = yfinance_context['result']
    assert len(result) > index, f"Not enough articles, expected at least {index + 1}"
    assert result[index]['publisher'] == publisher, f"Expected publisher '{publisher}', got '{result[index].get('publisher')}'"


@then(parsers.parse('the options should have field "{field}"'))
def then_options_has_field(yfinance_context, field):
    """Validate options has field."""
    result = yfinance_context['result']
    assert field in result, f"Expected field '{field}' in result: {result.keys()}"


@then(parsers.parse('the options field "{field}" should have {count:d} entries'))
def then_options_field_has_entries(yfinance_context, field, count):
    """Validate options field has correct number of entries."""
    result = yfinance_context['result']
    assert field in result, f"Expected field '{field}' in result"
    assert len(result[field]) == count, f"Expected {count} entries in '{field}', got {len(result[field])}"


@then(parsers.parse('the options field "{field}" should contain "{value}"'))
def then_options_field_contains_value(yfinance_context, field, value):
    """Validate options field contains value."""
    result = yfinance_context['result']
    assert field in result, f"Expected field '{field}' in result"
    assert value in result[field], f"Expected '{value}' in field '{field}': {result[field]}"


@then(parsers.parse('there should be {count:d} tools registered'))
def then_should_have_tools(yfinance_context, count):
    """Validate number of tools registered."""
    tools = yfinance_context['tools']
    assert len(tools) == count, f"Expected {count} tools, got {len(tools)}"


@then(parsers.parse('each tool should have attribute "{attribute}"'))
def then_each_tool_has_attribute(yfinance_context, attribute):
    """Validate each tool has attribute."""
    tools = yfinance_context['tools']
    for tool in tools:
        assert hasattr(tool, attribute), f"Tool {tool} missing attribute '{attribute}'"


@then("each tool should be callable")
def then_each_tool_is_callable(yfinance_context):
    """Validate each tool is callable."""
    tools = yfinance_context['tools']
    for tool in tools:
        assert callable(tool), f"Tool {tool} is not callable"


@then(parsers.parse('the ticker API should be called {count:d} times'))
def then_ticker_api_called_times(yfinance_context, count):
    """Validate ticker API was called correct number of times."""
    mock_ticker = yfinance_context['mock_ticker']
    assert mock_ticker.call_count == count, f"Expected {count} calls, got {mock_ticker.call_count}"


@then(parsers.parse('the ticker API should receive tickers "{ticker1}", "{ticker2}", "{ticker3}", "{ticker4}"'))
def then_ticker_api_receives_tickers(yfinance_context, ticker1, ticker2, ticker3, ticker4):
    """Validate ticker API received correct tickers."""
    mock_ticker = yfinance_context['mock_ticker']
    expected_tickers = [ticker1, ticker2, ticker3, ticker4]
    actual_tickers = [call[0][0] for call in mock_ticker.call_args_list]
    assert actual_tickers == expected_tickers, f"Expected tickers {expected_tickers}, got {actual_tickers}"
