"""
Shared configurations and fixtures for all tests.
"""
from ward import fixture


@fixture
async def extract_text():
    """
    Fixture that provides text extraction helper for different agent return types.

    Agents can return:
    - str directly
    - Message with content TextStream
    - Message with content str
    """
    async def _extract(result) -> str:
        if isinstance(result, str):
            return result

        if hasattr(result, 'content'):
            content = result.content
            if hasattr(content, 'await_complete'):
                return await content.await_complete()
            return str(content)

        return str(result)

    return _extract
