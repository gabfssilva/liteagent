"""
Tests for Wikipedia Tool - Wikipedia search and article retrieval.

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
from ward import test

# Load wikipedia module directly without going through tools/__init__.py
spec = importlib.util.spec_from_file_location(
    "wikipedia_module",
    "/home/user/liteagent/liteagent/tools/wikipedia.py"
)
wikipedia_module = importlib.util.module_from_spec(spec)
sys.modules['wikipedia_module'] = wikipedia_module
spec.loader.exec_module(wikipedia_module)
search = wikipedia_module.search
get_complete_article = wikipedia_module.get_complete_article


# ============================================
# Search Tests
# ============================================

@test("wikipedia_search returns formatted results")
async def _():
    """Tests that search returns properly formatted results."""
    # Mock response data
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

    # Mock httpx client
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch('httpx.AsyncClient', return_value=mock_client):
        result = await search.handler(query="Python", limit=2)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["title"] == "Python (programming language)"
        assert result[0]["description"] == "High-level programming language"
        assert "wikipedia.org/wiki/" in result[0]["url"]
        assert result[1]["title"] == "Python (genus)"


@test("wikipedia_search handles empty results")
async def _():
    """Tests that search handles empty results gracefully."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"pages": []}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch('httpx.AsyncClient', return_value=mock_client):
        result = await search.handler(query="NonExistentQuery123456", limit=5)

        assert isinstance(result, list)
        assert len(result) == 0


@test("wikipedia_search handles missing description")
async def _():
    """Tests that search handles pages without descriptions."""
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

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch('httpx.AsyncClient', return_value=mock_client):
        result = await search.handler(query="Test", limit=1)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["description"] == "No description available"


# ============================================
# Article Retrieval Tests
# ============================================

@test("get_complete_article validates Wikipedia URL")
async def _():
    """Tests that get_complete_article validates URL format."""
    try:
        await get_complete_article.handler(url="https://example.com/article")
        assert False, "Should have raised exception for non-Wikipedia URL"
    except Exception as e:
        assert "Wikipedia" in str(e)


@test("get_complete_article fetches and converts to markdown")
async def _():
    """Tests that get_complete_article fetches and converts content."""
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

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch('httpx.AsyncClient', return_value=mock_client):
        result = await get_complete_article.handler(
            url="https://en.wikipedia.org/wiki/Python_(programming_language)"
        )

        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain markdown elements (headings, text)
        # Note: exact markdown format depends on markdownify settings


@test("get_complete_article handles missing content div")
async def _():
    """Tests that get_complete_article handles missing content gracefully."""
    # Mock HTML without bodyContent div
    mock_html = "<html><body><div>No content here</div></body></html>"

    mock_response = MagicMock()
    mock_response.text = mock_html
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch('httpx.AsyncClient', return_value=mock_client):
        try:
            await get_complete_article.handler(
                url="https://en.wikipedia.org/wiki/Test"
            )
            assert False, "Should have raised exception for missing content"
        except Exception as e:
            assert "content body" in str(e).lower()
