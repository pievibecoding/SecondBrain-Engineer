"""
Unit tests for backend/integrations/graphiti.py.
Uses pytest-httpx to mock HTTP — no real Graphiti service needed.
"""
import pytest
from unittest.mock import patch
from pytest_httpx import HTTPXMock

from backend.integrations.graphiti import extract

# Use a fixed URL so tests are independent of .env GRAPHITI_URL value
MOCK_GRAPHITI_URL = "http://graphiti-test:9622"
EXTRACT_URL = f"{MOCK_GRAPHITI_URL}/extract"

TURNS = [
    {"role": "user", "content": "test question"},
    {"role": "assistant", "content": "test answer"},
]


@pytest.fixture(autouse=True)
def patch_graphiti_url():
    """Patch settings.GRAPHITI_URL so all tests use the mock URL."""
    with patch("backend.integrations.graphiti.settings") as mock_settings:
        mock_settings.GRAPHITI_URL = MOCK_GRAPHITI_URL
        yield mock_settings


@pytest.mark.asyncio
async def test_extract_forwards_correlation_id(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url=EXTRACT_URL,
        json={"ok": True, "entities_added": 2, "relations_added": 1},
    )

    await extract("conv-1", TURNS, correlation_id="test-cid-123")

    request = httpx_mock.get_request()
    assert request.headers.get("X-Correlation-ID") == "test-cid-123"


@pytest.mark.asyncio
async def test_extract_sends_correct_payload(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url=EXTRACT_URL,
        json={"ok": True},
    )

    await extract("conv-abc", TURNS, correlation_id="cid")

    import json
    request = httpx_mock.get_request()
    body = json.loads(request.content)
    assert body["conversation_id"] == "conv-abc"
    assert body["turns"] == TURNS
    assert "timestamp" in body


@pytest.mark.asyncio
async def test_extract_returns_ok_on_success(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url=EXTRACT_URL,
        json={"ok": True, "entities_added": 1, "relations_added": 0},
    )

    result = await extract("conv-1", TURNS, "cid")
    assert result.get("ok") is True


@pytest.mark.asyncio
async def test_extract_returns_ok_false_on_http_error(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url=EXTRACT_URL,
        status_code=500,
        text="Internal Server Error",
    )

    result = await extract("conv-1", TURNS, "cid")
    assert result.get("ok") is False
    assert "500" in result.get("error", "")


@pytest.mark.asyncio
async def test_extract_returns_ok_false_on_connection_error(httpx_mock: HTTPXMock):
    import httpx
    httpx_mock.add_exception(
        httpx.ConnectError("connection refused"),
        method="POST",
        url=EXTRACT_URL,
    )

    result = await extract("conv-1", TURNS, "cid")
    assert result.get("ok") is False


@pytest.mark.asyncio
async def test_extract_no_correlation_id_still_works(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url=EXTRACT_URL,
        json={"ok": True},
    )

    result = await extract("conv-1", TURNS)  # no correlation_id
    assert result.get("ok") is True
