"""
BDD tests for Stateful Sessions - Conversations with memory.

Validates that sessions:
- Accumulate multiple facts throughout conversation
- Can reset to clear memory
- Maintain context between messages
"""
from pytest_bdd import scenarios

# Load all scenarios from the feature file
scenarios('../features/sessions.feature')


# All steps (Given/When/Then) are imported from step_defs/conftest.py
# No need to redefine them here - they're automatically available
