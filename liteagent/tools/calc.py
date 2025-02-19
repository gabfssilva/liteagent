from pydantic import Field
from liteagent import tool

@tool(emoji='📊')
def calculator(expression: str = Field(..., description='the python expression to be evaluated')) -> any:
    """ use this tool to evaluate mathematical problems. """

    return eval(expression)
