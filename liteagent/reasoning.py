from litellm import BaseModel
from liteagent import agent
from liteagent.providers.provider import Provider
from functools import wraps
from collections import Counter

from liteagent.tools import calculator

from pydantic import BaseModel, Field
from typing import List

class ReasoningStep(BaseModel):
    description: str = Field(..., description="A concise explanation of the current reasoning step.")
    initial_analysis: str = Field(..., description="The preliminary thought process or context leading to this step.")
    counterfactual_check: str = Field(
        ...,
        description="A discussion of potential pitfalls or alternative scenarios (e.g., overcounting errors) to validate the step."
    )
    logical_conclusion: str = Field(
        ...,
        description="The derived conclusion for this step after considering all factors and counterfactuals."
    )
    is_final: bool = Field(..., description="Indicator whether this step represents the final, verified solution.")

class Reasoning(BaseModel):
    steps: List[ReasoningStep] = Field(..., description="A list of reasoning steps detailing the problem-solving process.")
    final_answer: str = Field(..., description="The final answer extracted from the verified reasoning steps.")


def reasoner(
    provider: Provider,
    minimum_steps: int = 3,
    maximum_steps: int = 5,
    n_variations: int = 5,  # for self-consistency
    num_branches: int = 3,  # for tree-of-thought branching
    refinement_rounds: int = 3  # additional refinement iterations per step
):
    def decorator(func):
        @agent(
            provider=provider,
            system_message=f"""
                You are a tree-of-thought reasoning planner using self-prompted chain-of-thought techniques.
                Generate multiple alternative sequences (branches) of reasoning steps to solve the problem.
                Provide at least {num_branches} alternative sequences, each with between {minimum_steps} and {maximum_steps} steps.
                DO NOT provide the final solution in any branch. 
                If a branch accidentally reveals the answer, say "sorry" and stop that branch.
            """
        )
        async def tree_reason_planner(initial_prompt: str) -> list[list[str]]:
            ...

        @agent(
            provider=provider,
            system_message="""
                You are a reasoning agent.
                Given the problem and the current sequence of reasoning steps, generate the next step in the chain-of-thought.
                Your response should be logically coherent and provide clear, verifiable reasoning.
                Use one of the tools if needed:
                {tools}
            """,
            tools=[calculator]
        )
        async def reasoner_agent(initial_prompt: str, steps: str, step_to_be_solved: str) -> ReasoningStep:
            """
            **Initial prompt:** {initial_prompt}

            **Current Steps:**
            ```json
            {steps}
            ```

            Step to be solved:
            > {step_to_be_solved}
            """

        @agent(
            provider=provider,
            system_message="""
                You are a reasoning refiner.
                Your task is to iteratively improve the provided reasoning step by correcting logical errors and enhancing clarity.
                If the step appears optimal, simply restate it.
                Use one of the tools if needed:
                {tools}
            """,
            tools=[calculator]
        )
        async def refine_reasoning_step(initial_prompt: str, steps: str, current_step: str) -> ReasoningStep:
            """
            **Initial prompt:** {initial_prompt}

            **Current Steps:**
            ```json
            {steps}
            ```

            Current step to refine:
            > {current_step}
            """

        @agent(
            provider=provider,
            system_message="""
                You are a reasoning summarizer.
                Evaluate all the provided reasoning steps and extract the final expected answer.
                Focus especially on ensuring that the final step is logically consistent.
                Use one of the tools if needed:
                {tools}
                
                Your output must contain a summarized step-by-step reasoning process, along with the final answer.
            """,
            tools=[calculator]
        )
        async def reasoning_summarizer(initial_prompt: str, steps: str) -> str:
            """
            **Initial prompt:** {initial_prompt}

            **Steps:**
            ```json
            {steps}
            ```
            """

        async def solve_steps(prompt: str, branch_steps: list[str]) -> Reasoning:
            acc = []
            for step_text in branch_steps:
                # Stop early if a final solution has already been reached
                if acc and acc[-1].is_final:
                    break

                current_steps_json = "[" + ",\n".join([p.model_dump_json(indent=2) for p in acc]) + "]"
                # Generate multiple variations for the current step (self-consistency)
                variations = []
                for _ in range(n_variations):
                    candidate = await reasoner_agent(
                        initial_prompt=prompt,
                        steps=current_steps_json,
                        step_to_be_solved=step_text
                    )
                    variations.append(candidate)
                # Choose the most common candidate based on its JSON representation
                variation_counts = Counter([cand.model_dump_json() for cand in variations])
                most_common_json, _ = variation_counts.most_common(1)[0]
                selected_candidate = next(cand for cand in variations if cand.model_dump_json() == most_common_json)

                # Refinement phase: iteratively improve the selected candidate
                refined_candidate = selected_candidate
                for _ in range(refinement_rounds):
                    current_steps_json = "[" + ",\n".join([p.model_dump_json(indent=2) for p in acc]) + "]"
                    refined_candidate = await refine_reasoning_step(
                        initial_prompt=prompt,
                        steps=current_steps_json,
                        current_step=refined_candidate.model_dump_json()
                    )
                acc.append(refined_candidate)
            current_steps_json = "[" + ",\n".join([p.model_dump_json(indent=2) for p in acc]) + "]"
            final_answer = await reasoning_summarizer(initial_prompt=prompt, steps=current_steps_json)
            return Reasoning(steps=acc, final_answer=final_answer)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            prompt = kwargs.get("prompt")
            # Generate multiple reasoning branches using tree-of-thought planning with SP-CoT
            branches = await tree_reason_planner(prompt)
            branch_results = []
            for branch in branches:
                # Create a list of ReasoningStep objects from the branch
                branch_steps = [step for step in branch]
                result = await solve_steps(prompt, branch_steps)
                branch_results.append(result)
            # Select the best branch.
            # For example, choose the first branch whose final answer does not include an error signal like "sorry"
            selected = next(
                (br for br in branch_results if "sorry" not in br.final_answer.lower()),
                branch_results[0]
            )
            return await func(selected)

        return wrapper

    return decorator
