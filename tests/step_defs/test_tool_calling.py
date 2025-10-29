"""
BDD tests for Tool Calling - Agents using custom tools.

Validates that agents can:
- Call individual tools and use returned data
- Orchestrate multiple tools in sequence
- Pass structured parameters to tools correctly
"""
from pytest_bdd import scenarios, given

# Load all scenarios from the feature file
scenarios('../features/tool_calling.feature')


# Additional Given step for this specific feature
@given("the OpenAI provider is available")
def given_openai_available():
    """Verify OpenAI provider is available (no-op, will fail if OPENAI_API_KEY missing)."""
    import os
    assert os.environ.get("OPENAI_API_KEY"), "OPENAI_API_KEY environment variable is required"


# All other steps (Given/When/Then) are imported from step_defs/conftest.py
# No need to redefine them here - they're automatically available
