import inspect
from typing import Any

from pydantic import create_model, Field

from .agent import Agent
from .tool import Tool


class AgentDispatcher(Tool):
    def __init__(self, agent: Agent):
        self.agent = agent

        input_model = self._create_input_model()

        super().__init__(
            name=f"{self.agent.name.replace(' ', '_').lower()}_redirection",
            description=f"Dispatch to the {self.agent.name} agent: {self.agent.description or ''}",
            input=input_model,
            handler=self._dispatch,
            emoji='🤖'
        )

    async def _dispatch(self, *args, **kwargs):
        args = filter(lambda arg: arg is not self, args)
        return await self.agent(*list(args), stream=True, **kwargs)

    def _create_input_model(self):
        if not self.agent.signature:
            return create_model(
                f"{self.agent.name.capitalize()}Input",
                query=(str, Field(..., description="Query to send to the agent"))
            )

        parameters = {}
        for name, param in self.agent.signature.parameters.items():
            annotation = param.annotation if param.annotation != inspect.Parameter.empty else Any
            default = param.default if param.default != inspect.Parameter.empty else ...
            parameters[name] = (annotation, Field(default=default))

        return create_model(
            f"{self.agent.name.capitalize()}Input",
            **parameters
        )
