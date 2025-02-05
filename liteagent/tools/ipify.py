import httpx

from liteagent import tool


@tool
async def ipify() -> str:
    """ use this tool to fetch the current ip address via ipify """

    async with httpx.AsyncClient() as client:
        response = await client.get(url="https://api64.ipify.org?format=json")
        response.raise_for_status()
        return response.json()["ip"]
