import asyncio
from typing import List, TypedDict

from liteagent import agent, chat
from liteagent.providers import openai
from liteagent.tools import duckduckgo, wikipedia, clock, crawl4ai


@agent(
    provider=openai(model="gpt-4.1"),
    tools=[duckduckgo, wikipedia.search, wikipedia.get_complete_article, crawl4ai],
    description="""
        Research agent specialized in finding facts and information.
        Always use your tools to get up-to-date information.
        Be concise and factual in your responses.
    """
)
async def research_agent(query: str) -> str:
    """Find information about: {query}"""


@agent(
    # provider=deepseek(model='deepseek-reasoner'),
    provider=openai(model="gpt-4.1"),
    description="""
        Analytical agent specialized in solving problems that require calculation or analytical reasoning.
        Focus on solving problems step-by-step and showing your work.
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
    All you need to know: {collected_knowledge}
    The task: {task}
    """


@agent(
    provider=openai(model="gpt-4.1"),
    tools=[clock],
    description="""
    Assistant agent specialized in helping users with general questions.
    You maintain context of the conversation and provide helpful, concise responses.
    When appropriate, suggest using the specialized research or analytical agents.
    """
)
async def assistant_agent(message: str, conversation_history: List[TypedDict("PromptRequest", {
    "user": str,
    "assistant": str
})]) -> str:
    """
    User message: {message}
    Conversation history: {conversation_history}

    Respond helpfully and concisely. If the question requires research or calculations,
    suggest using the specialized research or analytical agents.
    """


@chat.terminal(
    logo="Multi-Agent Chatbot"
)
@agent(
    provider=openai(model="gpt-4.1"),
    team=[research_agent, analytical_agent, assistant_agent],
    description="""
    Coordinator agent that manages a team of specialized agents:
    1. Research Agent: For factual information and research
    2. Analytical Agent: For calculations and problem-solving
    3. Assistant Agent: For general assistance and maintaining conversation context
    
    Your job is to determine which agent is best suited for a user query and delegate accordingly.
    For complex questions that span multiple domains, you can use multiple agents and synthesize their responses.
    Always aim to provide the most helpful, accurate response using the appropriate specialized agents.
    
    You can and should dispatch multiple queries to any agent at once if necessary.
    """
)
async def multi_agent_chatbot(): pass
    

"""
Research about Trump's political position regarding the tariffs and how the World reacted.

Do a deep research on trump's political position regarding the tariffs. Evaluate how the G7 is reacting to the situation. Write an analytical essay about all the information you gathered.
"""

if __name__ == "__main__":
    asyncio.run(multi_agent_chatbot())
