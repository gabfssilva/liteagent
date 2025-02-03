from pydantic import Field, BaseModel, JsonValue
from rich.pretty import Pretty

from liteagent import tool


class PythonScriptResult(BaseModel):
    script: str = Field(..., description="The python's script evaluated.")
    result: JsonValue = Field(..., description="The result of the script")

    def __rich__(self):
        return Pretty(self.result)

    def __tool_response__(self) -> JsonValue:
        return self.result


@tool
def python_runner(
    script: str = Field(..., description="The python's script to be evaluated."),
    output_variable: str = Field(...,
                                 description="The name of the variable that will contain all the needed result of the execution."),

) -> PythonScriptResult:
    """A tool for evaluating python's code.

    - Use this **EVERY TIME** you have to perform a calculation.
    - **EVERY TIME** you can't tell something that can be answered by running code, do it.
    - The script **MUST** assign the result to the `output_variable` provided:

    Examples:

    ## Math
    **User**: What's 5*5? // or 5*5=? // or any kind of math
    **Assistant via `python_runner`**:

    {
      "script": "final_result = 5 * 5"
      "output_variable": "final_result"
    }

    ## HTTP Request
    **User**: Use ipify and tell me what's my ip.
    **Assistant via `python_runner`**:

    {
      "script": "import requests; response = requests.get(\"https://api.ipify.org?format=json\"); final_result = response.json()[\"ip\"]"
      "output_variable": "final_result"
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
