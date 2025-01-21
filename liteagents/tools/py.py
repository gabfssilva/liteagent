from pydantic import Field, BaseModel, JsonValue
from rich.syntax import Syntax
from rich.pretty import Pretty

from liteagents import tool


class PythonScriptResult(BaseModel):
    script: str = Field(..., description="The python's script evaluated.")
    result: JsonValue = Field(..., description="The result of the script")

    def __rich__(self):
        return Pretty(self.result)


@tool
def evaluate(
    inline: str = Field(..., description="The python's inline script to be evaluated. Must be a single line script."),
) -> dict:
    """ A tool for evaluating python's code. Use this **EVERY TIME** you have to perform a calculation """

    return {
        "script": inline,
        "result": eval(inline)
    }


@tool
def runner(
    script: str = Field(..., description="The python's script to be evaluated."),
    output_variable: str = Field(...,
                                 description="The name of the variable that will contain all the needed result of the execution."),

) -> PythonScriptResult:
    """
    A tool for evaluating python's code.

    - Use this **EVERY TIME** you have to perform a calculation.
    - **EVERY TIME** you can't tell something that can be answered by running code, do it.
    - The script **MUST** assign the result to the `output_variable` provided:

    Examples:

    {
      "script": "result = 42"
      "output_variable": "result"
    }
    """
    try:
        namespace = {}
        exec(script, namespace)

        return PythonScriptResult(
            script=script,
            result=namespace[output_variable]
        )
    except KeyError as e:
        return PythonScriptResult(
            script=script,
            result=f"It looks like `{output_variable}` was not properly defined in the script. Be sure to assign the last result to this variable"
        )
    except BaseException as e:
        return PythonScriptResult(
            script=script,
            result=f"An error occurred while evaluating the script: {e}"
        )
