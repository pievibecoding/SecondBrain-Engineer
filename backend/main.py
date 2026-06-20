from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.middleware.correlation import CorrelationMiddleware
from backend.middleware.logging import LoggingMiddleware
from backend.middleware.rate_limit import RateLimitMiddleware
from backend.routers import auth as auth_router
from backend.routers import chat as chat_router
from backend.routers import wiki as wiki_router
from backend.routers.internal import nas as internal_nas
from backend.routers.admin import diagnostics, documents, evaluations, nas_queue, nas_folders
from backend.config import settings
from backend.logger import logger
from backend.mcp.server import mcp


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting backend app")
    yield
    logger.info("Shutting down backend app")


app = FastAPI(title="SecondBrain Backend", lifespan=lifespan)

# Middleware registration order: CORSMiddleware registered first -> runs last
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(RateLimitMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(CorrelationMiddleware)

app.include_router(auth_router.router, prefix="/api/auth")
app.include_router(internal_nas.router, prefix="/api/internal/nas", tags=["internal-nas"])
app.include_router(nas_queue.router, prefix="/api/admin/nas/queue", tags=["admin-nas-queue"])
app.include_router(nas_folders.router, prefix="/api/admin/nas/folders", tags=["admin-nas-folders"])
app.include_router(documents.router, prefix="/api/admin/documents", tags=["admin-documents"])
app.include_router(diagnostics.router, prefix="/api/admin/diagnostics", tags=["admin-diagnostics"])
app.include_router(evaluations.router, prefix="/api/admin/evaluations", tags=["admin-evaluations"])
app.include_router(chat_router.router, prefix="/api/chat", tags=["chat"])
app.include_router(wiki_router.router, prefix="/api/wiki", tags=["wiki"])
app.mount("/mcp", mcp.http_app())


@app.get("/health")
async def health_check():
    return {"status": "ok"}
