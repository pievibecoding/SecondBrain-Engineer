from backend.config import settings
from backend.integrations.lightrag.graph import LightRAGGraphClient
from backend.integrations.lightrag.ingest import LightRAGIngestClient
from backend.integrations.lightrag.query import LightRAGQueryClient
from backend.integrations.graphiti import extract as graphiti_extract


async def get_lightrag_query_client() -> LightRAGQueryClient:
    return LightRAGQueryClient(base_url=settings.LIGHTRAG_URL, timeout=settings.LIGHTRAG_TIMEOUT_SECONDS)


async def get_lightrag_ingest_client() -> LightRAGIngestClient:
    return LightRAGIngestClient(base_url=settings.LIGHTRAG_URL)


async def get_lightrag_graph_client() -> LightRAGGraphClient:
    return LightRAGGraphClient(base_url=settings.LIGHTRAG_URL)


async def get_graphiti_client():
    # Return the function as the injectable client. This keeps the router/service
    # code free of httpx usage and allows tests to override the dependency.
    return graphiti_extract
