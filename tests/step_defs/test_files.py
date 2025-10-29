"""
BDD tests for Files Tool - File System Operations.

Validates that:
- Files tool can read, write, and manage files
- Search functionality works across files
- Directory operations create proper structures
- Dry-run system works for write operations
"""
import sys
import importlib.util
from pathlib import Path
from pytest_bdd import scenarios, given, when, then, parsers
from pytest import fixture
import asyncio
import functools


def async_to_sync(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))
    return wrapper


# Load all scenarios from files.feature
scenarios('../features/files.feature')


# ==================== FIXTURES ====================

@fixture
def temp_dir(tmp_path):
    """Temporary directory for file operations."""
    return tmp_path


@fixture
def files_tool_fixture(temp_dir):
    """Loads Files tool without going through __init__.py to avoid optional dependencies."""
    spec = importlib.util.spec_from_file_location("files_tools", "liteagent/tools/files.py")
    files_module = importlib.util.module_from_spec(spec)
    sys.modules["files_tools"] = files_module
    spec.loader.exec_module(files_module)

    return files_module.Files(str(temp_dir))


@fixture
def files_context():
    """Context to store test state."""
    return {}


# ==================== GIVEN STEPS ====================

@given("a temporary directory with sample files")
def given_temp_dir_with_samples(temp_dir, files_tool_fixture):
    """Create sample files for testing."""
    # Create test.txt
    (temp_dir / "test.txt").write_text("Line 1\nLine 2\nLine 3\n")

    # Create hello.py
    (temp_dir / "hello.py").write_text("print('Hello')\nprint('World')\n")

    # Create subdir/nested.txt
    (temp_dir / "subdir").mkdir(parents=True, exist_ok=True)
    (temp_dir / "subdir" / "nested.txt").write_text("Nested content\n")


@given(parsers.parse('a file "{filename}" with content "{content}"'))
def given_file_with_content(temp_dir, filename, content):
    """Create a specific file with given content."""
    file_path = temp_dir / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)


# ==================== WHEN STEPS ====================

@when(parsers.parse('I read file "{filename}"'), target_fixture="read_result")
def when_read_file(files_tool_fixture, filename, files_context):
    """Read a file."""
    result = files_tool_fixture.read_file.handler(files_tool_fixture, path=filename)
    files_context['result'] = result
    return result


@when(parsers.parse('I read partial "{filename}" from line {start:d} to line {end:d}'), target_fixture="read_result")
def when_read_partial_range(files_tool_fixture, filename, start, end, files_context):
    """Read partial file with line range."""
    result = files_tool_fixture.read_partial.handler(
        files_tool_fixture,
        path=filename,
        start_line=start,
        end_line=end
    )
    files_context['result'] = result
    return result


@when(parsers.parse('I read partial "{filename}" searching for "{term}" with context {context:d}'), target_fixture="read_result")
def when_read_partial_search(files_tool_fixture, filename, term, context, files_context):
    """Read partial file by searching for term."""
    result = files_tool_fixture.read_partial.handler(
        files_tool_fixture,
        path=filename,
        term=term,
        context=context
    )
    files_context['result'] = result
    return result


@when(parsers.parse('I search for term "{term}" in all files'), target_fixture="search_result")
def when_search_all_files(files_tool_fixture, term, files_context):
    """Search for term across all files."""
    result = files_tool_fixture.search.handler(files_tool_fixture, term=term, extension=None)
    files_context['result'] = result
    return result


@when(parsers.parse('I search for term "{term}" in files with extension "{extension}"'), target_fixture="search_result")
def when_search_with_extension(files_tool_fixture, term, extension, files_context):
    """Search for term in files with specific extension."""
    result = files_tool_fixture.search.handler(files_tool_fixture, term=term, extension=extension)
    files_context['result'] = result
    return result


@when(parsers.parse('I list directory "{path}" non-recursively'), target_fixture="list_result")
def when_list_dir_non_recursive(files_tool_fixture, path, files_context):
    """List directory contents non-recursively."""
    result = files_tool_fixture.list_dir.handler(files_tool_fixture, path=path, recursive=False)
    files_context['result'] = result
    return result


@when(parsers.parse('I list directory "{path}" recursively'), target_fixture="list_result")
def when_list_dir_recursive(files_tool_fixture, path, files_context):
    """List directory contents recursively."""
    result = files_tool_fixture.list_dir.handler(files_tool_fixture, path=path, recursive=True)
    files_context['result'] = result
    return result


@when(parsers.parse('I create folder "{path}"'), target_fixture="folder_result")
def when_create_folder(files_tool_fixture, path, files_context):
    """Create a folder."""
    result = files_tool_fixture.create_folder.handler(files_tool_fixture, path=path)
    files_context['result'] = result
    return result


@when(parsers.parse('I create file "{filename}"'), target_fixture="create_result")
def when_create_file(files_tool_fixture, filename, files_context):
    """Create a file using dry-run."""
    result = files_tool_fixture.create_file.handler(files_tool_fixture, path=filename)
    files_context['result'] = result
    files_context['change_id'] = result.get('change_id')
    return result


@when(parsers.parse('I create file "{filename}" with dry-run'), target_fixture="create_result")
def when_create_file_dry_run(files_tool_fixture, filename, files_context):
    """Create a file with dry-run."""
    result = files_tool_fixture.create_file.handler(files_tool_fixture, path=filename)
    files_context['result'] = result
    files_context['change_id'] = result.get('change_id')
    return result


@when("I apply the change", target_fixture="apply_result")
def when_apply_change(files_tool_fixture, files_context):
    """Apply a deferred change."""
    change_id = files_context.get('change_id')
    result = files_tool_fixture.apply_change.handler(files_tool_fixture, change_id=change_id)
    files_context['result'] = result
    return result


@when(parsers.parse('I insert lines "{line1}", "{line2}" to "{filename}"'), target_fixture="insert_result")
def when_insert_lines(files_tool_fixture, line1, line2, filename, files_context):
    """Insert lines to file."""
    result = files_tool_fixture.insert_lines.handler(
        files_tool_fixture,
        path=filename,
        lines=[line1, line2]
    )
    files_context['result'] = result
    return result


@when(parsers.parse('I insert line "{line}" at position {position:d} in "{filename}"'), target_fixture="insert_result")
def when_insert_line_at_position(files_tool_fixture, line, position, filename, files_context):
    """Insert line at specific position."""
    result = files_tool_fixture.insert_lines.handler(
        files_tool_fixture,
        path=filename,
        lines=[line],
        line_number=position
    )
    files_context['result'] = result
    return result


@when(parsers.parse('I copy "{src}" to "{dest}"'), target_fixture="copy_result")
def when_copy_file(files_tool_fixture, src, dest, files_context):
    """Copy a file."""
    result = files_tool_fixture.copy.handler(files_tool_fixture, src=src, dest=dest)
    files_context['result'] = result
    return result


@when(parsers.parse('I move "{src}" to "{dest}"'), target_fixture="move_result")
def when_move_file(files_tool_fixture, src, dest, files_context):
    """Move a file."""
    result = files_tool_fixture.move.handler(files_tool_fixture, src=src, dest=dest)
    files_context['result'] = result
    return result


@when(parsers.parse('I delete file "{filename}"'), target_fixture="delete_result")
def when_delete_file(files_tool_fixture, filename, files_context):
    """Delete a file."""
    result = files_tool_fixture.delete_file.handler(files_tool_fixture, path=filename)
    files_context['result'] = result
    files_context['change_id'] = result.get('change_id')
    return result


@when("I scaffold structure with folders and files", target_fixture="scaffold_result")
def when_scaffold_structure(files_tool_fixture, files_context):
    """Scaffold folder structure."""
    entries = [
        {"path": "project", "type": "folder"},
        {"path": "project/src", "type": "folder"},
        {"path": "project/src/main.py", "type": "file", "content": "# Main file\n"},
        {"path": "project/README.md", "type": "file", "content": "# Project\n"}
    ]
    result = files_tool_fixture.scaffold_folder_structure.handler(files_tool_fixture, entries=entries)
    files_context['result'] = result
    return result


@when(parsers.parse('I update "{filename}" line {line:d} expecting "{expected}" with "{new}"'), target_fixture="update_result")
def when_update_lines(files_tool_fixture, filename, line, expected, new, files_context):
    """Update lines with expected content validation."""
    expected_text = [{"line": line, "content": expected}]
    new_content = [{"line": line, "content": new}]
    result = files_tool_fixture.update_lines.handler(
        files_tool_fixture,
        path=filename,
        expected_text=expected_text,
        new_content=new_content
    )
    files_context['result'] = result
    files_context['change_id'] = result.get('change_id')
    return result


# ==================== THEN STEPS ====================

@then(parsers.parse('I should get {count:d} lines'))
def then_should_get_lines(files_context, count):
    """Validate number of lines."""
    result = files_context['result']
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) == count, f"Expected {count} lines, got {len(result)}"


@then(parsers.parse('I should get {count:d} line'))
def then_should_get_line(files_context, count):
    """Validate number of lines (singular)."""
    then_should_get_lines(files_context, count)


@then(parsers.parse('line {line_num:d} should be "{expected}"'))
def then_line_should_be(files_context, line_num, expected):
    """Validate specific line content."""
    result = files_context['result']
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) >= line_num, f"Not enough lines, expected at least {line_num}"
    assert result[line_num - 1] == expected, f"Line {line_num} expected '{expected}', got '{result[line_num - 1]}'"


@then(parsers.parse('the result should contain "{text}"'))
def then_result_contains(files_context, text):
    """Validate result contains text."""
    result = files_context['result']
    if isinstance(result, list):
        result_str = "\n".join(str(r) for r in result)
    else:
        result_str = str(result)
    # Case-insensitive comparison
    assert text.lower() in result_str.lower(), f"Expected '{text}' in result: {result_str}"


@then(parsers.parse('I should find at least {count:d} results'))
def then_should_find_results(files_context, count):
    """Validate minimum number of results."""
    result = files_context['result']
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) >= count, f"Expected at least {count} results, got {len(result)}"


@then(parsers.parse('I should find at least {count:d} result'))
def then_should_find_result(files_context, count):
    """Validate minimum number of results (singular)."""
    then_should_find_results(files_context, count)


@then(parsers.parse('the results should contain "{text}"'))
def then_results_contain(files_context, text):
    """Validate results contain text."""
    then_result_contains(files_context, text)


@then(parsers.parse('all results should contain "{text}"'))
def then_all_results_contain(files_context, text):
    """Validate all results contain text."""
    result = files_context['result']
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    for item in result:
        assert text in str(item), f"Expected '{text}' in '{item}'"


@then(parsers.parse('I should find at least {count:d} entries'))
def then_should_find_entries(files_context, count):
    """Validate minimum number of directory entries."""
    then_should_find_results(files_context, count)


@then(parsers.parse('the directory "{path}" should exist'))
def then_directory_exists(temp_dir, path):
    """Validate directory exists."""
    dir_path = temp_dir / path
    assert dir_path.exists(), f"Directory '{dir_path}' does not exist"
    assert dir_path.is_dir(), f"Path '{dir_path}' is not a directory"


@then("I should get a change_id")
def then_should_get_change_id(files_context):
    """Validate change_id is present."""
    result = files_context['result']
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert 'change_id' in result, f"Expected 'change_id' in result: {result}"


@then(parsers.parse('the message should contain "{text}"'))
def then_message_contains(files_context, text):
    """Validate message contains text."""
    result = files_context['result']
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert 'message' in result, f"Expected 'message' in result: {result}"
    assert text in result['message'], f"Expected '{text}' in message: {result['message']}"


@then(parsers.parse('the file "{filename}" should exist'))
def then_file_exists(temp_dir, filename):
    """Validate file exists."""
    file_path = temp_dir / filename
    assert file_path.exists(), f"File '{file_path}' does not exist"


@then(parsers.parse('file "{filename}" should contain "{text}"'))
def then_file_contains(temp_dir, filename, text):
    """Validate file contains text."""
    file_path = temp_dir / filename
    assert file_path.exists(), f"File '{file_path}' does not exist"
    content = file_path.read_text()
    assert text in content, f"Expected '{text}' in file content: {content}"


@then(parsers.parse('the file "{filename}" should contain "{text}"'))
def then_the_file_contains(temp_dir, filename, text):
    """Validate file contains text (with 'the')."""
    then_file_contains(temp_dir, filename, text)


@then(parsers.parse('line {line_num:d} of "{filename}" should be "{expected}"'))
def then_file_line_should_be(temp_dir, line_num, filename, expected):
    """Validate specific line in file."""
    file_path = temp_dir / filename
    assert file_path.exists(), f"File '{file_path}' does not exist"
    lines = file_path.read_text().splitlines()
    assert len(lines) >= line_num, f"Not enough lines in file, expected at least {line_num}"
    assert lines[line_num - 1] == expected, f"Line {line_num} expected '{expected}', got '{lines[line_num - 1]}'"


@then(parsers.parse('"{dest}" should have same content as "{src}"'))
def then_files_same_content(temp_dir, dest, src):
    """Validate two files have same content."""
    src_path = temp_dir / src
    dest_path = temp_dir / dest
    assert src_path.exists(), f"Source file '{src_path}' does not exist"
    assert dest_path.exists(), f"Destination file '{dest_path}' does not exist"
    src_content = src_path.read_text()
    dest_content = dest_path.read_text()
    assert src_content == dest_content, f"Files have different content"


@then(parsers.parse('file "{filename}" should not exist'))
def then_file_not_exists(temp_dir, filename):
    """Validate file does not exist."""
    file_path = temp_dir / filename
    assert not file_path.exists(), f"File '{file_path}' should not exist"


@then(parsers.parse('the file "{filename}" should not exist'))
def then_the_file_not_exists(temp_dir, filename):
    """Validate file does not exist (with 'the')."""
    then_file_not_exists(temp_dir, filename)


@then("the result should have key \"message\"")
def then_result_has_message(files_context):
    """Validate result has message key."""
    result = files_context['result']
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert 'message' in result, f"Expected 'message' in result: {result}"


@then(parsers.parse('the result status should be "{status}"'))
def then_result_status(files_context, status):
    """Validate result status."""
    result = files_context['result']
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert 'status' in result, f"Expected 'status' in result: {result}"
    assert result['status'] == status, f"Expected status '{status}', got '{result['status']}'"


@then("the result should have key \"diff\"")
def then_result_has_diff(files_context):
    """Validate result has diff key."""
    result = files_context['result']
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert 'diff' in result, f"Expected 'diff' in result: {result}"


@then("the result should have key \"change_id\"")
def then_result_has_change_id(files_context):
    """Validate result has change_id key."""
    then_should_get_change_id(files_context)


@then("the result should have key \"mismatches\"")
def then_result_has_mismatches(files_context):
    """Validate result has mismatches key."""
    result = files_context['result']
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert 'mismatches' in result, f"Expected 'mismatches' in result: {result}"
