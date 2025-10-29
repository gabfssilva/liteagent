"""
BDD tests for Wikipedia Tool - Wikipedia Search and Article Retrieval.

Validates that:
- Wikipedia search returns results
- Article retrieval works correctly
- URL validation works
- Error handling is proper

NOTE: Uses mocked HTTP responses for determinism.
"""
import sys
import importlib.util
from unittest.mock import AsyncMock, patch, MagicMock
from pytest_bdd import scenarios, given, when, then, parsers
from pytest import fixture
import asyncio
import functools


def async_to_sync(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))
    return wrapper


# Load all scenarios from wikipedia.feature
scenarios('../features/wikipedia.feature')


# ==================== FIXTURES ====================

@fixture
def wikipedia_context():
    """Context to store test state."""
    return {}


@fixture
def wikipedia_modules():
    """Load Wikipedia module directly without going through tools/__init__.py."""
    spec = importlib.util.spec_from_file_location(
        "wikipedia_module",
        "/home/user/liteagent/liteagent/tools/wikipedia.py"
    )
    wikipedia_module = importlib.util.module_from_spec(spec)
    sys.modules['wikipedia_module'] = wikipedia_module
    spec.loader.exec_module(wikipedia_module)

    return {
        'search': wikipedia_module.search,
        'get_complete_article': wikipedia_module.get_complete_article
    }


# ==================== WHEN STEPS ====================

@when(parsers.parse('I search Wikipedia for "{query}" with limit {limit:d}'))
def when_search_wikipedia(wikipedia_modules, wikipedia_context, query, limit):
    """Search Wikipedia with mocked response."""
    search = wikipedia_modules['search']

    # Mock response data based on query
    if query == "Python":
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "pages": [
                {
                    "title": "Python (programming language)",
                    "description": "High-level programming language"
                },
                {
                    "title": "Python (genus)",
                    "description": "Genus of snakes"
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
    elif query == "NonExistentQuery123456":
        mock_response = MagicMock()
        mock_response.json.return_value = {"pages": []}
        mock_response.raise_for_status = MagicMock()
    else:
        mock_response = MagicMock()
        mock_response.json.return_value = {"pages": []}
        mock_response.raise_for_status = MagicMock()

    # Mock httpx client
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    async def _search():
        with patch('httpx.AsyncClient', return_value=mock_client):
            return await search.handler(query=query, limit=limit)

    result = async_to_sync(_search)()
    wikipedia_context['search_results'] = result


@when("I search Wikipedia for a page without description")
def when_search_without_description(wikipedia_modules, wikipedia_context):
    """Search Wikipedia for page without description."""
    search = wikipedia_modules['search']

    # Mock response without description field
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "pages": [
            {
                "title": "Test Page"
                # No description field
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    # Mock httpx client
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    async def _search():
        with patch('httpx.AsyncClient', return_value=mock_client):
            return await search.handler(query="Test", limit=1)

    result = async_to_sync(_search)()
    wikipedia_context['search_results'] = result


@when(parsers.parse('I get article from non-Wikipedia URL "{url}"'))
def when_get_article_invalid_url(wikipedia_modules, wikipedia_context, url):
    """Try to get article from non-Wikipedia URL."""
    get_complete_article = wikipedia_modules['get_complete_article']

    async def _get_article():
        try:
            return await get_complete_article.handler(url=url)
        except Exception as e:
            return {'error': str(e)}

    result = async_to_sync(_get_article)()
    wikipedia_context['result'] = result


@when(parsers.parse('I get article from Wikipedia URL "{url}"'))
def when_get_article_valid_url(wikipedia_modules, wikipedia_context, url):
    """Get article from Wikipedia URL with mocked response."""
    get_complete_article = wikipedia_modules['get_complete_article']

    # Mock HTML response
    mock_html = """
    <html>
        <body>
            <div id="bodyContent">
                <h2>Introduction</h2>
                <p>This is a test article about Python.</p>
                <h3>History</h3>
                <p>Python was created in 1991.</p>
            </div>
        </body>
    </html>
    """

    mock_response = MagicMock()
    mock_response.text = mock_html
    mock_response.raise_for_status = MagicMock()

    # Mock httpx client
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    async def _get_article():
        with patch('httpx.AsyncClient', return_value=mock_client):
            return await get_complete_article.handler(url=url)

    result = async_to_sync(_get_article)()
    wikipedia_context['result'] = result


@when("I get article from Wikipedia URL with missing content")
def when_get_article_missing_content(wikipedia_modules, wikipedia_context):
    """Get article from Wikipedia URL with missing content div."""
    get_complete_article = wikipedia_modules['get_complete_article']

    # Mock HTML without bodyContent div
    mock_html = "<html><body><div>No content here</div></body></html>"

    mock_response = MagicMock()
    mock_response.text = mock_html
    mock_response.raise_for_status = MagicMock()

    # Mock httpx client
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    async def _get_article():
        try:
            with patch('httpx.AsyncClient', return_value=mock_client):
                return await get_complete_article.handler(
                    url="https://en.wikipedia.org/wiki/Test"
                )
        except Exception as e:
            return {'error': str(e)}

    result = async_to_sync(_get_article)()
    wikipedia_context['result'] = result


# ==================== THEN STEPS ====================

@then(parsers.parse("I should get {count:d} search results"))
def then_should_get_search_results(wikipedia_context, count):
    """Validate number of search results."""
    results = wikipedia_context.get('search_results', [])
    assert isinstance(results, list), f"Expected list, got {type(results)}"
    assert len(results) == count, f"Expected {count} results, got {len(results)}"


@then(parsers.parse("I should get {count:d} search result"))
def then_should_get_search_result(wikipedia_context, count):
    """Validate number of search results (singular)."""
    then_should_get_search_results(wikipedia_context, count)


@then(parsers.parse('the first result should have title "{title}"'))
def then_first_result_has_title(wikipedia_context, title):
    """Validate first result title."""
    results = wikipedia_context.get('search_results', [])
    assert len(results) > 0, "No results found"
    assert results[0]["title"] == title, f"Expected title '{title}', got '{results[0]['title']}'"


@then(parsers.parse('the first result should have description "{description}"'))
def then_first_result_has_description(wikipedia_context, description):
    """Validate first result description."""
    results = wikipedia_context.get('search_results', [])
    assert len(results) > 0, "No results found"
    assert results[0]["description"] == description, \
        f"Expected description '{description}', got '{results[0]['description']}'"


@then("the first result should have a valid Wikipedia URL")
def then_first_result_has_valid_url(wikipedia_context):
    """Validate first result has valid Wikipedia URL."""
    results = wikipedia_context.get('search_results', [])
    assert len(results) > 0, "No results found"
    assert "url" in results[0], "URL field missing from result"
    assert "wikipedia.org/wiki/" in results[0]["url"], \
        f"Expected Wikipedia URL, got '{results[0]['url']}'"


@then(parsers.parse('I should get an error containing "{text}"'))
def then_should_get_error(wikipedia_context, text):
    """Validate error message contains text."""
    result = wikipedia_context.get('result')
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert 'error' in result, "Expected error in result"
    assert text in result['error'], f"Expected '{text}' in error: {result['error']}"


@then("I should get a non-empty markdown result")
def then_should_get_non_empty_markdown(wikipedia_context):
    """Validate result is non-empty."""
    result = wikipedia_context.get('result')
    assert result is not None, "Result is None"
    if isinstance(result, dict) and 'error' in result:
        raise AssertionError(f"Got error instead of result: {result['error']}")
    assert len(result) > 0, "Result is empty"


@then("the result should be a string")
def then_result_should_be_string(wikipedia_context):
    """Validate result is a string."""
    result = wikipedia_context.get('result')
    assert isinstance(result, str), f"Expected string, got {type(result)}"
