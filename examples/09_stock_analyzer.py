"""
Example 09: Stock Analyzer - Real-World Workflow

This example demonstrates:
- Integration with real APIs (Yahoo Finance)
- Complex structured output
- Multi-step workflow
- Decision-making agent

Concepts introduced:
- Real API integration (yfinance)
- Complex Pydantic models
- Multi-step reasoning
- Business logic implementation

Run: uv run python examples/09_stock_analyzer.py
"""

import asyncio
from typing import List, Literal

from pydantic import BaseModel, Field

from liteagent import agent
from liteagent.providers import openai
from liteagent.tools import yfinance


class StockAnalysis(BaseModel):
    """Comprehensive stock analysis."""
    ticker: str = Field(description="Stock ticker symbol")
    company_name: str = Field(description="Company name")
    current_price: float = Field(description="Current stock price")
    recommendation: Literal["strong_buy", "buy", "hold", "sell", "strong_sell"] = Field(
        description="Investment recommendation"
    )
    risk_level: Literal["low", "medium", "high"] = Field(
        description="Investment risk level"
    )
    key_metrics: dict = Field(description="Important financial metrics")
    reasoning: str = Field(description="Detailed reasoning for recommendation")
    recent_news_summary: str = Field(description="Summary of recent news")


@agent(
    provider=openai(model="gpt-4o-mini"),
    tools=[yfinance],
    description="""
    You are an expert stock analyst providing comprehensive investment analysis.

    For each stock:
    1. Get current price and company information
    2. Retrieve analyst recommendations
    3. Get recent news
    4. Analyze financial metrics
    5. Provide clear recommendation with reasoning

    Be thorough, data-driven, and honest about risks.
    """
)
async def stock_analyzer(ticker: str) -> StockAnalysis:
    """
    Analyze stock: {ticker}

    Provide comprehensive analysis including:
    - Current valuation
    - Analyst consensus
    - Recent news impact
    - Risk assessment
    - Clear recommendation
    """


async def analyze_portfolio(tickers: List[str]):
    """Analyze multiple stocks and display results."""

    print("Stock Portfolio Analyzer")
    print("="*80)
    print()

    for ticker in tickers:
        print(f"📊 Analyzing {ticker}...")
        print("-"*80)

        try:
            analysis = await stock_analyzer(ticker)

            # Display analysis
            print(f"\n🏢 {analysis.company_name} ({analysis.ticker})")
            print(f"💵 Current Price: ${analysis.current_price:.2f}")
            print(f"\n📈 Recommendation: {analysis.recommendation.upper().replace('_', ' ')}")
            print(f"⚠️  Risk Level: {analysis.risk_level.upper()}")

            print(f"\n📊 Key Metrics:")
            for metric, value in analysis.key_metrics.items():
                print(f"   • {metric}: {value}")

            print(f"\n💡 Reasoning:")
            print(f"   {analysis.reasoning}")

            print(f"\n📰 Recent News:")
            print(f"   {analysis.recent_news_summary}")

        except Exception as e:
            print(f"❌ Error analyzing {ticker}: {e}")

        print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    # Analyze a portfolio of stocks
    portfolio = ["AAPL", "MSFT", "NVDA"]

    print("Analyzing portfolio:", ", ".join(portfolio))
    print()

    asyncio.run(analyze_portfolio(portfolio))

    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80)
