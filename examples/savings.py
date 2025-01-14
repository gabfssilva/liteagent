import os

from pydantic import Field

from liteagents import tool, Agent, auditors
from liteagents.providers import OpenAICompatible


@tool
async def budget_analysis(
    income: float = Field(..., description="The user's total monthly income."),
    expenses: float = Field(..., description="The user's total monthly expenses.")
) -> str:
    """Analyzes the user's budget and provides suggestions to optimize savings."""

    savings = income - expenses
    if savings < 0:
        return f"You are overspending by ${-savings:.2f}. Consider reducing discretionary expenses."
    else:
        return f"You are saving ${savings:.2f} per month. Great job! Consider allocating some of it to investments."


@tool
async def investment_planning(
    savings: float = Field(..., description="The user's monthly savings."),
    risk_tolerance: str = Field(..., description="The user's risk tolerance: 'low', 'medium', or 'high'.")
) -> str:
    """Provides investment suggestions based on savings and risk tolerance."""
    if risk_tolerance == "low":
        return f"With savings of ${savings:.2f}, consider investing in bonds or a high-yield savings account."
    elif risk_tolerance == "medium":
        return f"With savings of ${savings:.2f}, consider a mix of index funds and ETFs."
    elif risk_tolerance == "high":
        return f"With savings of ${savings:.2f}, consider investing in stocks or cryptocurrency."
    return "Please specify a valid risk tolerance."


@tool
async def risk_analysis(
    investments: str = Field(..., description="The user's current investment portfolio."),
    market_conditions: str = Field(...,
                                   description="Current market conditions: 'stable', 'volatile', or 'uncertain'.")
) -> str:
    """Analyzes the risk of the user's investments based on market conditions."""
    if market_conditions == "stable":
        return f"Your investments in {investments} are performing well in the stable market. No changes needed."
    elif market_conditions == "volatile":
        return f"Your investments in {investments} are at risk due to market volatility. Consider diversifying your portfolio."
    elif market_conditions == "uncertain":
        return f"The uncertain market may impact your investments in {investments}. Stay cautious and avoid high-risk assets."
    return "Please specify valid market conditions."


@tool
async def tax_optimization(
    income: float = Field(..., description="The user's total annual income."),
    deductions: float = Field(..., description="The user's total annual tax deductions.")
) -> str:
    """Provides tax optimization strategies to reduce tax liabilities."""
    taxable_income = income - deductions
    return f"With a taxable income of ${taxable_income:.2f}, consider contributing to tax-deferred accounts or charitable donations to lower your tax liability."


@tool
async def savings_strategy(
    goal: float = Field(..., description="The user's savings goal."),
    timeline: int = Field(..., description="The timeline in months to achieve the goal."),
    current_savings: float = Field(..., description="The user's current savings."),
) -> str:
    """Suggests a strategy to achieve a savings goal within a timeline."""
    monthly_contribution = max((goal - current_savings) / timeline, 0)
    return f"To achieve a savings goal of ${goal:.2f} in {timeline} months, save ${monthly_contribution:.2f} per month."


if __name__ == '__main__':
    console = auditors.console()

    budget_agent = Agent(
        name="Budget Agent",
        provider=OpenAICompatible(),
        description="An agent for analyzing and optimizing budgets.",
        system_message="You are an agent specialized in budget analysis.",
        tools=[budget_analysis],
        intercept=console
    )

    investment_agent = Agent(
        name="Investment Agent",
        provider=OpenAICompatible(),
        description="An agent for investment planning.",
        system_message="You are an agent specialized in investment planning.",
        tools=[investment_planning],
        intercept=console
    )

    risk_agent = Agent(
        name="Risk Analysis Agent",
        provider=OpenAICompatible(),
        description="An agent for analyzing financial risks.",
        system_message="You are an agent specialized in risk analysis.",
        tools=[risk_analysis],
        intercept=console
    )

    tax_agent = Agent(
        name="Tax Agent",
        provider=OpenAICompatible(),
        description="An agent for tax optimization strategies.",
        system_message="You are an agent specialized in tax optimization.",
        tools=[tax_optimization],
        intercept=console
    )

    savings_agent = Agent(
        name="Savings Agent",
        provider=OpenAICompatible(),
        description="An agent for creating savings strategies.",
        system_message="You are an agent specialized in savings strategies.",
        tools=[savings_strategy],
        intercept=console
    )

    coordinator_agent = Agent(
        name="Financial Coordinator Agent",
        provider=OpenAICompatible(),
        description="An agent that coordinates financial planning tasks.",
        system_message="You are a coordinator agent that integrates financial planning from specialized agents.",
        team=[
            budget_agent,
            investment_agent,
            risk_agent,
            tax_agent,
            savings_agent,
        ],
        intercept=console
    )

    prompt = """I need help with my financial planning. Here are the details:

    1. My monthly income is $5000, and my expenses are $4200. Analyze my budget and let me know how much I can allocate for investments and savings while keeping $500 aside for emergencies.
    2. Based on the budget analysis, suggest how to invest the allocated amount with medium risk tolerance. Keep in mind I already have an emergency fund of $15,000.
    3. My portfolio includes index funds. Analyze risks if the market is volatile and propose any portfolio adjustments to align with the new investments you suggest.
    4. My annual income is $60,000 with $10,000 in deductions. Provide tax strategies to maximize returns while considering the investments and adjustments you propose.
    5. I want to save $20,000 in 24 months, starting with my current savings of $5000. Ensure that the plan for achieving this goal aligns with the investment strategy, risk analysis, and tax optimization.
    6. If any of the above steps involve trade-offs, such as reducing investments to meet the savings goal, provide a prioritized action plan."""

    *_, _ = coordinator_agent.sync(prompt)
