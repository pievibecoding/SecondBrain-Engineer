import pytest
import httpx
import json

from backend.integrations.lightrag.errors import LightRAGError, LightRAGNotFoundError, LightRAGTimeoutError
from backend.integrations.lightrag.graph import LightRAGGraphClient
from backend.integrations.lightrag.ingest import LightRAGIngestClient
from backend.integrations.lightrag.query import LightRAGQueryClient


@pytest.mark.asyncio
async def test_lightrag_ingest_sends_document_payload(httpx_mock):
    httpx_mock.add_response(url="http://lightrag:9621/api/v1/docs", json={"id": "doc-1", "status": "processing"})
    client = LightRAGIngestClient("http://lightrag:9621")

    response = await client.ingest_document("/mnt/nas/a.pdf", {"source": "nas"}, "cid-1")

    request = httpx_mock.get_request()
    assert response["id"] == "doc-1"
    assert request.method == "POST"
    assert request.headers["X-Correlation-ID"] == "cid-1"
    assert request.headers["Content-Type"] == "application/json"
    assert json.loads(request.read()) == {"file_path": "/mnt/nas/a.pdf", "metadata": {"source": "nas"}}


@pytest.mark.asyncio
async def test_lightrag_delete_empty_response_returns_deleted(httpx_mock):
    httpx_mock.add_response(url="http://lightrag:9621/api/v1/docs/doc-1", content=b"")
    client = LightRAGIngestClient("http://lightrag:9621")

    response = await client.delete_document("doc-1", "cid-1")

    request = httpx_mock.get_request()
    assert response == {"status": "deleted"}
    assert request.method == "DELETE"
    assert request.headers["X-Correlation-ID"] == "cid-1"


@pytest.mark.asyncio
async def test_lightrag_query_defaults_to_mix(httpx_mock):
    httpx_mock.add_response(url="http://lightrag:9621/query", json={"response": "ok"})
    client = LightRAGQueryClient("http://lightrag:9621")

    await client.query("Dự án Heineken dùng motor gì?", "cid-1")

    request = httpx_mock.get_request()
    assert request.headers["X-Correlation-ID"] == "cid-1"
    assert json.loads(request.read()) == {"query": "Dự án Heineken dùng motor gì?", "mode": "mix"}


@pytest.mark.asyncio
async def test_lightrag_query_can_request_prompt_debug(httpx_mock):
    httpx_mock.add_response(url="http://lightrag:9621/query", json={"response": "prompt"})
    client = LightRAGQueryClient("http://lightrag:9621")

    await client.query(
        "hello",
        "cid-1",
        include_references=True,
        include_chunk_content=True,
        only_need_prompt=True,
    )

    request = httpx_mock.get_request()
    assert request.headers["X-Correlation-ID"] == "cid-1"
    assert json.loads(request.read()) == {
        "query": "hello",
        "mode": "mix",
        "include_references": True,
        "include_chunk_content": True,
        "only_need_prompt": True,
    }


@pytest.mark.asyncio
async def test_lightrag_query_stream_yields_chunks(httpx_mock):
    httpx_mock.add_response(url="http://lightrag:9621/query/stream", text="chunk-1chunk-2")
    client = LightRAGQueryClient("http://lightrag:9621")

    chunks = [chunk async for chunk in client.query_stream("hello", "cid-1")]

    request = httpx_mock.get_request()
    assert request.headers["X-Correlation-ID"] == "cid-1"
    assert chunks == ["chunk-1chunk-2"]


@pytest.mark.asyncio
async def test_lightrag_graph_gets_entity_and_edges(httpx_mock):
    httpx_mock.add_response(url="http://lightrag:9621/api/v1/graph/entity/Heineken", json={"name": "Heineken"})
    httpx_mock.add_response(url="http://lightrag:9621/api/v1/graph/edges?entity=Heineken", json=[{"src": "a"}])
    client = LightRAGGraphClient("http://lightrag:9621")

    entity = await client.get_entity("Heineken", "cid-1")
    edges = await client.get_edges("Heineken", "cid-1")

    requests = httpx_mock.get_requests()
    assert entity == {"name": "Heineken"}
    assert edges == [{"src": "a"}]
    assert all(request.headers["X-Correlation-ID"] == "cid-1" for request in requests)


@pytest.mark.asyncio
async def test_lightrag_non_2xx_raises_error(httpx_mock):
    httpx_mock.add_response(url="http://lightrag:9621/api/v1/docs", status_code=500, text="boom")
    client = LightRAGIngestClient("http://lightrag:9621")

    with pytest.raises(LightRAGError):
        await client.ingest_document("/mnt/nas/a.pdf", {}, "cid-1")


@pytest.mark.asyncio
async def test_lightrag_graph_404_raises_not_found(httpx_mock):
    httpx_mock.add_response(url="http://lightrag:9621/api/v1/graph/entity/Missing", status_code=404)
    client = LightRAGGraphClient("http://lightrag:9621")

    with pytest.raises(LightRAGNotFoundError):
        await client.get_entity("Missing", "cid-1")


@pytest.mark.asyncio
async def test_lightrag_timeout_raises_timeout(httpx_mock):
    httpx_mock.add_exception(httpx.TimeoutException("timeout"), url="http://lightrag:9621/query")
    client = LightRAGQueryClient("http://lightrag:9621")

    with pytest.raises(LightRAGTimeoutError):
        await client.query("hello", "cid-1")
