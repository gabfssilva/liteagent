"""
Tests for Files Tool - File system operations.

Validates that:
- File reading operations work correctly
- File writing/editing operations work correctly
- Directory operations work correctly
- Search functionality works correctly
- Dry-run system for destructive operations works

NOTE: Tests use temporary directory for isolation.
"""
import sys
import importlib.util
import tempfile
from pathlib import Path
from ward import test, fixture

# Load files module directly without going through tools/__init__.py
# (which has playwright dependency)
spec = importlib.util.spec_from_file_location(
    "liteagent.tools.files",
    "/home/user/liteagent/liteagent/tools/files.py"
)
files_module = importlib.util.module_from_spec(spec)
sys.modules['liteagent.tools.files'] = files_module
spec.loader.exec_module(files_module)
Files = files_module.Files


@fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@fixture
def files_tool(temp_dir=temp_dir):
    """Create Files tool instance with temp directory."""
    return Files(str(temp_dir))


@fixture
def sample_files(files_tool=files_tool, temp_dir=temp_dir):
    """Create sample files for testing."""
    # Create test files
    (temp_dir / "test.txt").write_text("Line 1\nLine 2\nLine 3\n")
    (temp_dir / "hello.py").write_text("print('Hello')\nprint('World')\n")
    (temp_dir / "subdir").mkdir()
    (temp_dir / "subdir" / "nested.txt").write_text("Nested content\n")
    return files_tool


# ============================================
# Read Operations
# ============================================

@test("read_file returns file content with line numbers")
def _(files_tool=sample_files):
    """Tests that read_file returns complete file content with line numbers."""
    result = files_tool.read_file.handler(files_tool, path="test.txt")

    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0] == "1: Line 1"
    assert result[1] == "2: Line 2"
    assert result[2] == "3: Line 3"


@test("read_file handles non-existent file gracefully")
def _(files_tool=sample_files):
    """Tests that read_file returns error for non-existent file."""
    result = files_tool.read_file.handler(files_tool, path="nonexistent.txt")

    assert isinstance(result, list)
    assert len(result) == 1
    assert "Error reading file" in result[0]


@test("read_partial extracts specific line range")
def _(files_tool=sample_files):
    """Tests that read_partial can extract specific lines."""
    result = files_tool.read_partial.handler(
        files_tool,
        path="test.txt",
        start_line=2,
        end_line=3
    )

    assert isinstance(result, list)
    assert len(result) == 2
    assert "2: Line 2" in result
    assert "3: Line 3" in result


@test("read_partial searches for term with context")
def _(files_tool=sample_files):
    """Tests that read_partial can search for terms."""
    result = files_tool.read_partial.handler(
        files_tool,
        path="test.txt",
        term="Line 2",
        context=1
    )

    assert isinstance(result, list)
    # Should return Line 1, Line 2, Line 3 (context=1)
    assert any("Line 1" in line for line in result)
    assert any("Line 2" in line for line in result)
    assert any("Line 3" in line for line in result)


# ============================================
# Search Operations
# ============================================

@test("search finds term across all files")
def _(files_tool=sample_files):
    """Tests that search finds terms in multiple files."""
    result = files_tool.search.handler(
        files_tool,
        term="Line",
        extension=None
    )

    assert isinstance(result, list)
    assert len(result) > 0
    # Should find "Line" in test.txt (3 times)
    matching = [r for r in result if "test.txt" in r and "Line" in r]
    assert len(matching) == 3


@test("search filters by extension")
def _(files_tool=sample_files):
    """Tests that search can filter by file extension."""
    result = files_tool.search.handler(
        files_tool,
        term="print",
        extension=".py"
    )

    assert isinstance(result, list)
    assert len(result) >= 2  # Two print statements in hello.py
    assert all(".py" in r or "Error" in r for r in result)


# ============================================
# Directory Operations
# ============================================

@test("list_dir lists directory contents non-recursively")
def _(files_tool=sample_files):
    """Tests that list_dir can list directory contents."""
    result = files_tool.list_dir.handler(
        files_tool,
        path=".",
        recursive=False
    )

    assert isinstance(result, list)
    assert len(result) >= 3
    # Should have test.txt, hello.py, subdir/
    assert "test.txt" in result or any("test.txt" in r for r in result)
    assert "hello.py" in result or any("hello.py" in r for r in result)
    assert any("subdir" in r for r in result)


@test("list_dir lists recursively when requested")
def _(files_tool=sample_files):
    """Tests that list_dir can list recursively."""
    result = files_tool.list_dir.handler(
        files_tool,
        path=".",
        recursive=True
    )

    assert isinstance(result, list)
    # Should include nested.txt from subdir/
    assert any("nested.txt" in r for r in result)


@test("create_folder creates directory structure")
def _(files_tool=files_tool, temp_dir=temp_dir):
    """Tests that create_folder creates directories."""
    result = files_tool.create_folder.handler(
        files_tool,
        path="new/nested/folder"
    )

    assert "created" in result.lower()
    assert (temp_dir / "new" / "nested" / "folder").exists()
    assert (temp_dir / "new" / "nested" / "folder").is_dir()


# ============================================
# File Writing Operations
# ============================================

@test("create_file uses dry-run system and returns change_id")
def _(files_tool=files_tool):
    """Tests that create_file uses dry-run pattern."""
    result = files_tool.create_file.handler(
        files_tool,
        path="newfile.txt"
    )

    assert isinstance(result, dict)
    assert "change_id" in result
    assert "message" in result
    assert "dry run" in result["message"].lower()


@test("apply_change executes deferred operation")
def _(files_tool=files_tool, temp_dir=temp_dir):
    """Tests that apply_change executes the deferred operation."""
    # Create a file with dry-run
    dry_result = files_tool.create_file.handler(
        files_tool,
        path="deferred.txt"
    )
    change_id = dry_result["change_id"]

    # File should not exist yet
    assert not (temp_dir / "deferred.txt").exists()

    # Apply the change
    apply_result = files_tool.apply_change.handler(
        files_tool,
        change_id=change_id
    )

    # Now file should exist
    assert (temp_dir / "deferred.txt").exists()
    assert "created" in apply_result.lower()


@test("insert_lines appends to file by default")
def _(files_tool=sample_files, temp_dir=temp_dir):
    """Tests that insert_lines can append lines."""
    result = files_tool.insert_lines.handler(
        files_tool,
        path="test.txt",
        lines=["Line 4", "Line 5"],
        line_number=None
    )

    assert "appended" in result.lower()
    content = (temp_dir / "test.txt").read_text()
    assert "Line 4" in content
    assert "Line 5" in content


@test("insert_lines can insert at specific position")
def _(files_tool=sample_files, temp_dir=temp_dir):
    """Tests that insert_lines can insert at specific line."""
    result = files_tool.insert_lines.handler(
        files_tool,
        path="test.txt",
        lines=["Inserted Line"],
        line_number=2
    )

    assert "inserted" in result.lower()
    lines = (temp_dir / "test.txt").read_text().splitlines()
    assert lines[1] == "Inserted Line"


# ============================================
# File Operations
# ============================================

@test("copy duplicates file successfully")
def _(files_tool=sample_files, temp_dir=temp_dir):
    """Tests that copy duplicates files."""
    result = files_tool.copy.handler(
        files_tool,
        src="test.txt",
        dest="test_copy.txt"
    )

    assert "copied" in result.lower()
    assert (temp_dir / "test_copy.txt").exists()
    assert (temp_dir / "test_copy.txt").read_text() == (temp_dir / "test.txt").read_text()


@test("move relocates file successfully")
def _(files_tool=sample_files, temp_dir=temp_dir):
    """Tests that move relocates files."""
    # Create a file to move
    (temp_dir / "tomove.txt").write_text("Move me")

    result = files_tool.move.handler(
        files_tool,
        src="tomove.txt",
        dest="moved.txt"
    )

    assert "moved" in result.lower()
    assert not (temp_dir / "tomove.txt").exists()
    assert (temp_dir / "moved.txt").exists()
    assert (temp_dir / "moved.txt").read_text() == "Move me"


@test("delete_file uses dry-run system")
def _(files_tool=sample_files):
    """Tests that delete_file uses dry-run pattern."""
    result = files_tool.delete_file.handler(
        files_tool,
        path="test.txt"
    )

    assert isinstance(result, dict)
    assert "change_id" in result
    assert "message" in result


# ============================================
# Advanced Operations
# ============================================

@test("scaffold_folder_structure creates complete structure")
def _(files_tool=files_tool, temp_dir=temp_dir):
    """Tests that scaffold can create folder/file structure."""
    entries = [
        {"path": "project/src", "type": "folder"},
        {"path": "project/src/main.py", "type": "file", "content": "# Main file"},
        {"path": "project/README.md", "type": "file", "content": "# Project"},
    ]

    result = files_tool.scaffold_folder_structure.handler(
        files_tool,
        entries=entries
    )

    assert "created" in result.lower()
    assert (temp_dir / "project" / "src").is_dir()
    assert (temp_dir / "project" / "src" / "main.py").exists()
    assert (temp_dir / "project" / "README.md").exists()
    assert "# Main file" in (temp_dir / "project" / "src" / "main.py").read_text()


@test("update_lines validates expected content before changes")
def _(files_tool=sample_files):
    """Tests that update_lines validates expected lines."""
    result = files_tool.update_lines.handler(
        files_tool,
        path="test.txt",
        expected_text=[
            {"line": 1, "content": "Line 1"},
            {"line": 2, "content": "Line 2"}
        ],
        new_content=[
            {"line": 2, "content": "Updated Line 2"}
        ]
    )

    assert result["status"] == "dry_run"
    assert "diff" in result
    assert "change_id" in result


@test("update_lines detects mismatches")
def _(files_tool=sample_files):
    """Tests that update_lines detects content mismatches."""
    result = files_tool.update_lines.handler(
        files_tool,
        path="test.txt",
        expected_text=[
            {"line": 1, "content": "Wrong Content"}
        ],
        new_content=[
            {"line": 1, "content": "New Content"}
        ]
    )

    assert result["status"] == "error"
    assert "mismatches" in result
    assert len(result["mismatches"]) > 0
