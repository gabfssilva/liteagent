Feature: Files Tool - File System Operations
  As a developer using LiteAgent
  I want to perform file system operations
  So that agents can read, write, and manage files

  Background:
    Given a temporary directory with sample files

  # Read Operations
  Scenario: Read file returns content with line numbers
    When I read file "test.txt"
    Then I should get 3 lines
    And line 1 should be "1: Line 1"
    And line 2 should be "2: Line 2"
    And line 3 should be "3: Line 3"

  Scenario: Read file handles non-existent file gracefully
    When I read file "nonexistent.txt"
    Then I should get 1 line
    And the result should contain "Error reading file"

  Scenario: Read partial extracts specific line range
    When I read partial "test.txt" from line 2 to line 3
    Then I should get 2 lines
    And the result should contain "2: Line 2"
    And the result should contain "3: Line 3"

  Scenario: Read partial searches for term with context
    When I read partial "test.txt" searching for "Line 2" with context 1
    Then the result should contain "Line 1"
    And the result should contain "Line 2"
    And the result should contain "Line 3"

  # Search Operations
  Scenario: Search finds term across all files
    When I search for term "Line" in all files
    Then I should find at least 1 result
    And the results should contain "test.txt"

  Scenario: Search filters by extension
    When I search for term "print" in files with extension ".py"
    Then I should find at least 2 results
    And all results should contain ".py"

  # Directory Operations
  Scenario: List directory contents non-recursively
    When I list directory "." non-recursively
    Then I should find at least 3 entries
    And the results should contain "test.txt"
    And the results should contain "hello.py"
    And the results should contain "subdir"

  Scenario: List directory recursively
    When I list directory "." recursively
    Then the results should contain "nested.txt"

  Scenario: Create folder creates directory structure
    When I create folder "new/nested/folder"
    Then the result should contain "created"
    And the directory "new/nested/folder" should exist

  # File Writing Operations
  Scenario: Create file uses dry-run system
    When I create file "newfile.txt"
    Then I should get a change_id
    And the message should contain "dry run"

  Scenario: Apply change executes deferred operation
    When I create file "deferred.txt" with dry-run
    And I apply the change
    Then the file "deferred.txt" should exist
    And the result should contain "created"

  Scenario: Insert lines appends to file by default
    When I insert lines "Line 4", "Line 5" to "test.txt"
    Then the result should contain "appended"
    And the file "test.txt" should contain "Line 4"
    And the file "test.txt" should contain "Line 5"

  Scenario: Insert lines at specific position
    When I insert line "Inserted Line" at position 2 in "test.txt"
    Then the result should contain "inserted"
    And line 2 of "test.txt" should be "Inserted Line"

  # File Operations
  Scenario: Copy duplicates file successfully
    When I copy "test.txt" to "test_copy.txt"
    Then the result should contain "copied"
    And the file "test_copy.txt" should exist
    And "test_copy.txt" should have same content as "test.txt"

  Scenario: Move relocates file successfully
    Given a file "tomove.txt" with content "Move me"
    When I move "tomove.txt" to "moved.txt"
    Then the result should contain "moved"
    And the file "tomove.txt" should not exist
    And the file "moved.txt" should exist
    And the file "moved.txt" should contain "Move me"

  Scenario: Delete file uses dry-run system
    When I delete file "test.txt"
    Then I should get a change_id
    And the result should have key "message"

  # Advanced Operations
  Scenario: Scaffold folder structure creates complete structure
    When I scaffold structure with folders and files
    Then the result should contain "created"
    And the directory "project/src" should exist
    And the file "project/src/main.py" should exist
    And the file "project/README.md" should exist
    And the file "project/src/main.py" should contain "# Main file"

  Scenario: Update lines validates expected content
    When I update "test.txt" line 2 expecting "Line 2" with "Updated Line 2"
    Then the result status should be "dry_run"
    And the result should have key "diff"
    And the result should have key "change_id"

  Scenario: Update lines detects mismatches
    When I update "test.txt" line 1 expecting "Wrong Content" with "New Content"
    Then the result status should be "error"
    And the result should have key "mismatches"
