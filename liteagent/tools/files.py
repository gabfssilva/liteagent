import re
import shutil
import uuid
from difflib import unified_diff
from pathlib import Path
from typing import TypedDict, List, Literal, Optional

from pydantic import Field

from liteagent import Tools, tool, ToolDef

class Files(Tools):
    def __init__(self, folder: str):
        """Initialize the file tool with a root folder."""
        self.folder = Path(folder)
        self.changes = {}

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
        Use this tool to extract a specific part of a file by either:

        - Providing a `term` to search, which returns that line and a few lines around it (`context`)
        - Or specifying `start_line` and `end_line` to extract a specific line range

        Returns: List of lines with line numbers as strings.
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

    @tool(emoji='🔥')
    def apply_change(self, change_id: str):
        """ Apply the specified change """

        return self.changes.pop(change_id)()

    @tool(emoji='📄')
    def create_file(self, path: str):
        """  Create a new file. """
        def execution():
            file_path = self.folder / path
            try:
                if not file_path.exists():
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.touch()

                return f"File '{file_path}' created."
            except Exception as e:
                return f"Error creating file: {e}"

        change_id = f'{uuid.uuid4()}'
        self.changes[change_id] = execution

        return {
            "message": "dry run finished.",
            "change_id": change_id
        }

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
        path: str = Field(..., description="Relative path to the file"),
        expected_text: List[TypedDict("LineEdit", {
            "line": int,
            "content": str,
        })] = Field(..., description="Current lines to be validated before applying changes"),
        new_content: Optional[List[TypedDict("LineEdit", {
            "line": int,
            "content": str | None,
        })]] = Field(None, description="Replacement lines (same line numbers)"),
    ) -> dict:
        """
        Use this tool to **safely replace lines** in a file.
        **Always** use `dry_run=True` to preview changes as a diff before applying them.

        - `expected_text` must match current content line-by-line.
        - `new_content` provides replacement content for the same line numbers. If None, the line is removed.

        Returns: status, message, and unified diff.
        """
        file_path = self.folder / path

        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
            updated_lines = lines[:]
            mismatches = []

            for edit in expected_text:
                if edit['line'] < 1 or edit['line'] > len(lines):
                    mismatches.append((edit['line'], "out of bounds", edit['content']))
                    continue
                actual = lines[edit['line'] - 1].rstrip()
                expected = edit['content'].rstrip()
                if actual != expected:
                    mismatches.append((edit['line'], actual, expected))

            if mismatches:
                return {
                    "status": "error",
                    "message": "Expected lines did not match file content",
                    "next_action": "Fix the mismatches and try again.",
                    "mismatches": mismatches
                }

            if new_content:
                remove_lines = sorted(
                    [edit['line'] for edit in new_content if edit['content'] is None],
                    reverse=True
                )

                for line in remove_lines:
                    if 1 <= line <= len(updated_lines):
                        del updated_lines[line - 1]
                    else:
                        return {
                            "status": "error",
                            "message": f"Invalid line number to remove: {line}"
                        }

                for edit in new_content:
                    if edit['line'] < 1 or edit['line'] > len(updated_lines):
                        return {
                            "status": "error",
                            "next_action": "Fix the mismatches and try again.",
                            "message": f"Invalid new_content line number: {edit['line']}"
                        }

                    updated_lines[edit['line'] - 1] = edit['content']

            diff = list(unified_diff(
                lines,
                updated_lines,
                fromfile=path,
                tofile=path,
                lineterm=""
            ))

            def execution():
                file_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")

                return {
                    "status": "ok",
                    "summary": f"{len(new_content or [])} lines updated in {path}.",
                    "diff": diff
                }

            change_id = f'{uuid.uuid4()}'
            self.changes[change_id] = execution

            return {
                "status": "dry_run",
                "message": f"After applied, {len(new_content or [])} lines would be updated. DO NOT APPLY IF YOU'RE NOT SURE.",
                "diff": diff,
                "change_id": change_id,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @tool(emoji='🗑️')
    def delete_file(self, path: str):
        """
        Delete a file at the given path.

        Returns a success or error message.
        """
        def execution():
            file_path = self.folder / path
            try:
                file_path.unlink()
                return f"File '{file_path}' deleted."
            except Exception as e:
                return f"Error deleting file: {e}"

        change_id = f'{uuid.uuid4()}'
        self.changes[change_id] = execution

        return {
            "message": "Do not remove the file if you're not sure about it.",
            "change_id": change_id,
        }

    @tool(emoji='✏️')
    def insert_lines(self, path: str, lines: list[str], line_number: int | None = None):
        """
        Use this tool to add lines to a file.

        - To append to the end, omit `line_number`.
        - To insert before a specific line (1-based), provide `line_number`.

        Returns a status message.
        """
        file_path = self.folder / path
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if not file_path.exists():
                file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                return f"File '{file_path}' created with {len(lines)} lines."

            content = file_path.read_text(encoding="utf-8").splitlines()
            if line_number is None:
                content.extend(lines)
            else:
                line_index = max(0, min(len(content), line_number - 1))
                content = content[:line_index] + lines + content[line_index:]

            file_path.write_text("\n".join(content) + "\n", encoding="utf-8")
            return f"{len(lines)} lines {'inserted' if line_number is not None else 'appended'} to '{file_path}' at line {line_number or len(content)}."
        except Exception as e:
            return f"Error modifying file: {e}"


def files(folder: str) -> ToolDef:
    return Files(folder)
