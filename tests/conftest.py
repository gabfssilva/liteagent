"""
Shared configurations and fixtures for all tests.
"""


async def extract_text(result) -> str:
    """
    Helper to extract text from different agent return types.

    Agents can return:
    - str directly
    - Message with content TextStream
    - Message with content str
    """
    if isinstance(result, str):
        return result

    if hasattr(result, 'content'):
        content = result.content
        if hasattr(content, 'await_complete'):
            return await content.await_complete()
        return str(content)

    return str(result)
