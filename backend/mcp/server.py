"""
MCP Server for SecondBrain — Robolinks Knowledge Hub.
Mounted at /mcp in backend/main.py.

Uses fastmcp-slim for tool definitions. Falls back gracefully if
server support is not available (no client extra installed).
"""
from backend.mcp.tools.search import search_knowledge
from backend.mcp.tools.entity import get_entity
from backend.logger import logger

try:
    from fastmcp import FastMCP

    mcp = FastMCP("SecondBrain — Robolinks Knowledge Hub")

    @mcp.tool()
    async def search_knowledge_tool(query: str, mode: str = "mix") -> str:
        """Tìm kiếm trong knowledge base Robolinks. mode: 'mix' (mặc định), 'local', 'global'"""
        return await search_knowledge(query=query, mode=mode)

    @mcp.tool()
    async def get_entity_tool(entity_name: str) -> dict:
        """Lấy thông tin chi tiết về một entity. Trả về: description, relations, source documents."""
        return await get_entity(entity_name=entity_name)

    logger.info("mcp_server_initialized", server_name="SecondBrain — Robolinks Knowledge Hub")

except ImportError:
    # FastMCP server support not installed — MCP endpoint will be unavailable
    # Install fastmcp (full) to enable: pip install fastmcp
    logger.warning("mcp_server_unavailable", reason="fastmcp server support not installed")

    class _FallbackMCP:
        """Minimal stub so backend/main.py can still mount /mcp without crashing."""
        def http_app(self):
            from starlette.applications import Starlette
            from starlette.responses import JSONResponse
            from starlette.routing import Route

            async def unavailable(request):
                return JSONResponse(
                    {"error": "MCP server not available", "hint": "Install fastmcp to enable"},
                    status_code=503
                )

            return Starlette(routes=[Route("/{path:path}", unavailable)])

    mcp = _FallbackMCP()
