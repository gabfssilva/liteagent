from pydantic import Field
from liteagent import tool

@tool(emoji='📊')
def calculator(expression: str = Field(..., description='the python expression to be evaluated')) -> str:
    """ use this tool **EVERY TIME** you need to evaluate mathematical equations. """

    return str(eval(expression))
