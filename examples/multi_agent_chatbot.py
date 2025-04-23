import asyncio
from typing import List, TypedDict

from liteagent import agent, chat
from liteagent.providers import openai, deepseek
from liteagent.tools import duckduckgo, wikipedia, browser


@agent(
    provider=openai(model="gpt-4.1-mini"),
    tools=[duckduckgo, wikipedia.search, wikipedia.get_complete_article, browser],
    description="""
        Research agent specialized in conducting thorough, source-backed investigations.
        Always use tools to verify claims and retrieve the most current and credible information.
        Summarize findings clearly, cite sources, and surface multiple viewpoints when relevant.
    """
)
async def research_agent(query: str) -> str:
    """Investigate: {query}. Collect and verify facts rigorously."""


@agent(
    provider=deepseek(model='deepseek-reasoner'),
    description="""
        Analytical agent focused on deep reasoning, complex inference, and multi-step problem solving.
        Integrates and synthesizes knowledge to form well-structured answers and insights.
        Prioritize clarity of reasoning, intermediate steps, and defensible conclusions.
    """
)
async def analytical_agent(
    collected_knowledge: List[TypedDict("Knowledge", {
        "fact": str,
        "source": str
    })],
    task: str
) -> str:
    """
    Base your analysis on: {collected_knowledge}
    Your objective: {task}
    """


@agent(
    provider=deepseek(model="deepseek-reasoner"),
    description="""
        Agent specialized in risk analysis, tradeoff evaluation, and scenario stress testing.
        Analyzes negative outcomes, edge cases, uncertainties, and failure modes in any proposed idea or dataset.
    """
)
async def risk_assessor_agent(
    collected_knowledge: List[TypedDict("Knowledge", {"fact": str, "source": str})],
    subject: str
) -> str:
    """
    Evaluate risks associated with: {subject}, using the following evidence: {collected_knowledge}
    """


@agent(
    provider=deepseek(model="deepseek-reasoner"),
    description="""
        Agent skilled in generating and evaluating counterfactuals — alternative "what-if" scenarios.
        Useful for assessing causality, strategy shifts, and policy alternatives.
    """
)
async def counterfactual_agent(
    collected_knowledge: List[TypedDict("Knowledge", {"fact": str, "source": str})],
    hypothetical: str
) -> str:
    """
    Base your analysis on: {collected_knowledge}
    Analyze this hypothetical scenario: {hypothetical} — What would change, based on the evidence?
    """


@agent(
    provider=openai(model="gpt-4.1"),
    team=[research_agent, analytical_agent, risk_assessor_agent, counterfactual_agent],
    description="""
        Coordinator agent leading a high-rigor, multi-agent research and analysis team.

        Team roles:
        1. Research Agent — Gathers diverse, accurate, and up-to-date information from trusted sources.
        2. Analytical Agent — Performs deep analysis, reasoning, and structured synthesis based on the evidence.
        3. Risk Assessor Agent — Identifies risks, trade-offs, and edge cases in any proposal or dataset.
        4. Counterfactual Agent — Explores "what-if" scenarios and evaluates alternative causal pathways.

        For **every prompt** you receive:
        - Initiate a preliminary fact-finding mission with the Research Agent.
        - Use the Analytical Agent to formulate refined research directives.
        - Dispatch additional Research Agents as needed for focused or expanded investigation.
        - Engage the Risk Assessor Agent when evaluating options, consequences, or potential failures.
        - Call the Counterfactual Agent to model hypothetical or alternative scenarios.
        - Use the Analytical Agent again to produce a comprehensive, reasoned answer.
        - Ensure all responses are sourced, well-argued, and ready for decision-making or publication.
    """
)
async def deep_search_coordinator(prompt: str):
    """{prompt}"""


@chat.terminal(
    logo="Executive Meta-Agent"
)
@agent(
    provider=openai(model="gpt-4.1"),
    team=[deep_search_coordinator],
    description="""
        Executive Meta-Agent that oversees and evaluates the deep_search_coordinator's performance.

        For every user prompt:
        - Come up with a high-level objective for the deep_search_coordinator.
        - Create a single prompt for the deep_search_coordinator to complete.
        - Concurrently, **using the exact same prompt**, dispatch 3 times the deep_search_coordinator in order to gather diverse perspectives.
        - Compare the results to identify discrepancies, redundancies, and complementary insights.
        - Synthesize a final, high-confidence answer based on convergence, clarity, and reasoning strength.
        - If outputs disagree, explain the differences and justify the final conclusion.
    """
)
async def executive_meta_agent(): pass


if __name__ == "__main__":
    asyncio.run(executive_meta_agent())
