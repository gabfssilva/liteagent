from datetime import datetime

from liteagent import tool


@tool(eager=True, emoji='🕒')
def clock() -> str:
    """ use this tool to get the current time. """
    return str(datetime.now())
