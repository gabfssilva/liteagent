Feature: YFinance Tool - Stock Market Data Retrieval
  As a developer using LiteAgent
  I want to retrieve stock market data from Yahoo Finance
  So that agents can analyze and provide financial information

  # Stock Information
  Scenario: Get stock info retrieves company information
    When I call get_stock_info for ticker "AAPL"
    Then the stock info should contain symbol "AAPL"
    And the stock info should contain longName "Apple Inc."
    And the stock info should contain sector "Technology"
    And the stock info should have field "marketCap"
    And the stock info should have field "currentPrice"

  # Historical Data
  Scenario: Get historical data fetches price history
    When I call get_historical_data for ticker "AAPL" with period "5d" and interval "1d"
    Then the historical data should have field "Open"
    And the historical data should have field "Close"
    And the historical data should have field "Volume"
    And the historical data field "Open" should have 5 entries

  # Financial Statements
  Scenario: Get financials retrieves financial statements
    When I call get_financials for ticker "AAPL"
    Then the financials should have field "income_statement"
    And the financials should have field "balance_sheet"
    And the financials should have field "cash_flow"

  # Dividends
  Scenario: Get dividends retrieves dividend history
    When I call get_dividends for ticker "AAPL"
    Then the dividends should be a dict
    And the dividends should have 4 entries
    And the dividends should contain value 0.23

  # Analyst Recommendations
  Scenario: Get recommendations retrieves analyst ratings
    When I call get_recommendations for ticker "AAPL"
    Then the recommendations should have field "strongBuy"
    And the recommendations should have field "buy"
    And the recommendations should have field "hold"

  # News
  Scenario: Get news retrieves recent news articles
    When I call get_news for ticker "AAPL"
    Then the news should be a list
    And the news should have 2 articles
    And the news article 0 should have title "Apple announces new product"
    And the news article 1 should have publisher "Bloomberg"

  # Options
  Scenario: Get options retrieves expiration dates
    When I call get_options for ticker "AAPL"
    Then the options should have field "expiration_dates"
    And the options field "expiration_dates" should have 3 entries
    And the options field "expiration_dates" should contain "2024-01-19"

  # Tool Registration
  Scenario: YFinance tools are properly registered
    When I check the yfinance tools registration
    Then there should be 7 tools registered
    And each tool should have attribute "name"
    And each tool should have attribute "definition"
    And each tool should be callable

  # Multiple Tickers
  Scenario: Tools handle different ticker symbols
    When I call get_stock_info for tickers "AAPL", "GOOGL", "MSFT", "TSLA"
    Then the ticker API should be called 4 times
    And the ticker API should receive tickers "AAPL", "GOOGL", "MSFT", "TSLA"
