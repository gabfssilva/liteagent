from datetime import datetime

from liteagent import tool


@tool(eager=True, emoji='🕒')
def clock() -> str:
    """ use this tool to get the current time. """
    return f"Current time: {str(datetime.now())}"


@tool(emoji='📅')
def today() -> str:
    """ use this tool to get the current date. """

    return str(datetime.now().date())
