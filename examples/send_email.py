import asyncio

from aiosmtpd.controller import Controller


class DebuggingHandler:
    async def handle_DATA(self, server, session, envelope):
        print(f"E-mail received:")
        print('\n'.join([f'> {ln}' for ln in envelope.content.decode('utf8', errors='replace').splitlines()]))

        return '250 Message accepted for delivery'


controller = Controller(DebuggingHandler(), hostname="localhost", port=1025)

from liteagent import agent
from liteagent.providers import openai
from liteagent.tools import email_sender, brasil_api, clock


@agent(
    tools=[
        clock,
        brasil_api,
        email_sender(sslcontext=None)
    ],
    provider=openai(),
)
async def email_sender_agent(email: str) -> str:
    """
    - get the brazilian holidays for the current year
    - send them as a markdown table to the following e-mail: {email}
    """

if __name__ == "__main__":
    controller.start()
    asyncio.run(email_sender_agent(email="receiver@example.com"))
    controller.stop()
