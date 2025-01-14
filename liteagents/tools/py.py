from pydantic import Field

from liteagents import tool


@tool
def evaluate(
    inline: str = Field(..., description="The python's inline script to be evaluated. Must be a single line script."),
) -> dict:
    """ A tool for evaluating python's code. Use this **EVERY TIME** you have to perform a calculation """

    return {
        "script": inline,
        "result": eval(inline)
    }
