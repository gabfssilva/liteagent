from liteagent import tool
from liteagent.tools import http

@tool
@http(url='https://api.chucknorris.io/jokes/random')
async def chuck_norris() -> str:
    """ use this tool to fetch a random joke from chuck norris. send the joke as is in the response. """

@tool
@http(url='https://api64.ipify.org?format=json')
async def ipify() -> str:
    """ use this tool to fetch the current ip address via ipify """
