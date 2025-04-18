import inspect
from typing import Any

from pydantic import create_model, Field

from .tool import Tool

class AgentDispatch(Tool):
    def __init__(self, agent):
        self.agent = agent
        input_model = self._create_input_model()

        super().__init__(
            name=f"{agent.name.replace(' ', '_').lower()}_redirection",
            description=f"Dispatch to the {agent.name} agent: {agent.description or ''}",
            input=input_model,
            handler=self._dispatch,
            emoji='🤖'
        )

    async def _dispatch(self, *args, **kwargs):
        return await self.agent(*args, **kwargs)

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
