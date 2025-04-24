import re
import shutil
from pathlib import Path
from typing import TypedDict, List, Literal

from liteagent import Tools, tool, ToolDef


class Files(Tools):
    def __init__(self, folder: str):
        """Initialize the file tool with a root folder."""
        self.folder = Path(folder)

    @tool(emoji='🔎')
    def search(self, term: str, extension: str | None):
        """
        Search for a text term across all files in the folder (recursively).

        Returns a list of matches with file path and line number.
        """
        result = []
        pattern = re.compile(term, re.IGNORECASE)

        for file in self.folder.rglob(f"*{extension}" if extension else "*"):
            try:
                with file.open("r", encoding="utf-8") as f:
                    for i, line in enumerate(f, start=1):
                        if pattern.search(line):
                            result.append(f"{file} (line {i}): {line.strip()}")
            except Exception as e:
                result.append(f"Error while reading file {file}: {e}")

        return result

    @tool(emoji='📖')
    def read_file(self, path: str):
        """
        Read the entire contents of a file with line numbers.

        Returns the file content as a list of lines with line numbers.
        """
        file_path = self.folder / path
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
            return [f"{i + 1}: {line}" for i, line in enumerate(lines)]
        except Exception as e:
            return [f"Error reading file: {e}"]

    @tool(emoji='📖')
    def read_partial(self, path: str, term: str | None = None, start_line: int | None = None,
                     end_line: int | None = None, context: int = 2):
        """
        Read a partial view of the file, either by matching a term (with N lines of context)
        or by providing a start and end line number.

        Returns the selected lines as a list with line numbers.
        """
        file_path = self.folder / path
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
            result = []

            if start_line is not None and end_line is not None:
                for i in range(start_line - 1, min(end_line, len(lines))):
                    result.append(f"{i + 1}: {lines[i]}")
            elif term:
                pattern = re.compile(term, re.IGNORECASE)
                for i, line in enumerate(lines):
                    if pattern.search(line):
                        start = max(0, i - context)
                        end = min(len(lines), i + context + 1)
                        for j in range(start, end):
                            result.append(f"{j + 1}: {lines[j]}")
                        result.append("...")
                if not result:
                    result = ["No match found."]
            else:
                result = ["Provide either term or start/end line."]

            return result
        except Exception as e:
            return [f"Error reading partial file: {e}"]

    @tool(emoji='📄')
    def create_file(self, path: str, content: str):
        """
        Create a new file with the specified content.

        Overwrites the file if it already exists.
        """
        file_path = self.folder / path
        try:
            file_path.write_text(content, encoding="utf-8")
            return f"File '{file_path}' created."
        except Exception as e:
            return f"Error creating file: {e}"

    @tool(emoji='➡️')
    def copy(self, src: str, dest: str):
        """
        Copy a file or folder to a new location.

        Overwrites destination if it exists.
        """
        src_path = self.folder / src
        dest_path = self.folder / dest

        try:
            if src_path.is_dir():
                shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dest_path)
            return f"Copied '{src_path}' to '{dest_path}'."
        except Exception as e:
            return f"Error copying: {e}"

    @tool(emoji='📂')
    def list_dir(self, path: str, recursive: bool | None):
        """
        List contents of a directory.

        If recursive is True, traverses all subdirectories. Defaults to True
        Each item includes relative path and indicates if it's a folder.
        """
        recursive = recursive if recursive is not None else True

        dir_path = self.folder / path
        try:
            if recursive:
                return sorted(
                    str(p.relative_to(self.folder)) + ("/" if p.is_dir() else "")
                    for p in dir_path.rglob("*")
                )
            else:
                return sorted(
                    str(p.relative_to(self.folder)) + ("/" if p.is_dir() else "")
                    for p in dir_path.iterdir()
                )
        except Exception as e:
            return [f"Error listing directory: {e}"]

    @tool
    def scaffold_folder_structure(self, entries: List[TypedDict("Entry", {
        "path": str,
        "type": Literal["file", "folder"],
        "content": str | None,
    })]):
        """
        Create a folder and file structure based on a flat list of entries.
        Each entry must define a path, a type ("file" or "folder"), and optional content (only for files).
        Ensure that parent folders are created as needed.
        Use this to set up a project scaffold or layout from a predefined plan.

        Example:
        [
          {"path": "src", "type": "folder"},
          {"path": "src/main.py", "type": "file", "content": "print('hello')"},
          {"path": "docs/", "type": "folder"},
          {"path": "README.md", "type": "file", "content": "# Project"}
        ]
        ```
        """
        for entry in entries:
            path = entry["path"]
            type_ = entry["type"]
            content = entry.get("content")

            full_path = self.folder / path

            if type_ == "folder":
                full_path.mkdir(parents=True, exist_ok=True)
            elif type_ == "file":
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content or "", encoding="utf-8")

        return "Flat structure created."

    @tool(emoji='📁')
    def create_folder(self, path: str):
        """
        Create a new folder (including parent directories if needed).

        Does nothing if the folder already exists.
        """
        folder_path = self.folder / path
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
            return f"Folder '{folder_path}' created (or already existed)."
        except Exception as e:
            return f"Error creating folder: {e}"

    @tool(emoji='📦')
    def move(self, src: str, dest: str):
        """
        Move a file or directory from one location to another.

        Overwrites the destination if it already exists.
        """
        src_path = self.folder / src
        dest_path = self.folder / dest

        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            src_path.rename(dest_path)
            return f"Moved '{src_path}' to '{dest_path}'."
        except Exception as e:
            return f"Error moving file or folder: {e}"

    @tool(emoji='✏️')
    def update_lines(
        self,
        path: str,
        start_line: int,
        end_line: int,
        expected_text: str,
        new_content: str | None = None,
    ):
        """
        Replace or delete a range of lines in a file.
        The replacement only happens if the original lines match expected_text exactly.

        If new_content is None, the lines are removed.
        """
        file_path = self.folder / path
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
            original = "\n".join(lines[start_line - 1:end_line])

            if original != expected_text:
                return (
                    f"Expected text does not match the actual content in lines "
                    f"{start_line}-{end_line}.\n\nExpected:\n{expected_text}\n\nFound:\n{original}"
                )

            updated_lines = (
                lines[:start_line - 1] +
                ([] if new_content is None else new_content.splitlines()) +
                lines[end_line:]
            )
            file_path.write_text("\n".join(updated_lines), encoding="utf-8")
            return f"Lines {start_line} to {end_line} updated in '{file_path}'."
        except Exception as e:
            return f"Error updating file: {e}"

    @tool(emoji='🗑️')
    def delete_file(self, path: str):
        """
        Delete a file at the given path.

        Returns a success or error message.
        """
        file_path = self.folder / path
        try:
            file_path.unlink()
            return f"File '{file_path}' deleted."
        except Exception as e:
            return f"Error deleting file: {e}"

    @tool(emoji='✏️')
    def append_lines(self, path: str, lines: list[str]):
        """
        Append a list of lines to the end of the specified file.

        Creates the file if it does not exist.
        """
        file_path = self.folder / path
        try:
            with file_path.open("a", encoding="utf-8") as f:
                for line in lines:
                    f.write(line + "\n")
            return f"Appended {len(lines)} lines to '{file_path}'."
        except Exception as e:
            return f"Error appending to file: {e}"


def files(folder: str) -> ToolDef:
    return Files(folder)
