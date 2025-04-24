import subprocess
from pathlib import Path

from liteagent import tool, Tools, ToolDef


class Terminal(Tools):
    def __init__(self, root: str, allowed: list[str] = None):
        self.root = Path(root).resolve()
        self.available_commands = allowed or ["ls", "cat", "grep", "echo"]

    @tool(emoji='💻')
    def available_commands(self) -> list[str]:
        return self.available_commands

    @tool(emoji="💻")
    def run_command(
        self,
        command: str,
        args: list[str],
    ) -> str:
        """
        Run a terminal command from a fixed safe set with arguments.

        Example: command="ls", args=["-l", "src"]
        """
        if command not in self.available_commands:
            return f"Command not allowed: {command}"

        try:
            result = subprocess.run(
                [command, *args],
                cwd=self.root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding="utf-8",
                timeout=5,
            )
            return result.stdout.strip()
        except Exception as e:
            return f"Error running command: {e}"


def terminal(root: str, allowed: list[str] = None) -> ToolDef:
    return Terminal(root=root, allowed=allowed)
