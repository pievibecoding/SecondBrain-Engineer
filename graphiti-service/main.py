"""
Graphiti Service — FastAPI entry point.
Validates required env vars at startup, handles graceful shutdown on SIGTERM/SIGINT.
"""
import os
import signal
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from routers.extract import router as extract_router
from logger import logger

# ── Env validation ────────────────────────────────────────────────────────────

REQUIRED_ENV_VARS = ["GRAPHITI_DB_URL"]

_shutdown_event = asyncio.Event()


def _validate_env() -> None:
    missing = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
    if missing:
        # Log but don't exit in MVP — DB is optional (in-memory fallback)
        logger.warning("missing_env_vars", missing=missing)


# ── Graceful shutdown ─────────────────────────────────────────────────────────

def _handle_signal(sig, frame):
    logger.info("graphiti_service_shutdown_signal", signal=sig)
    _shutdown_event.set()


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_env()
    logger.info("graphiti_service_starting", port=9622)
    yield
    logger.info("graphiti_service_stopped")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Graphiti Service", lifespan=lifespan)
app.include_router(extract_router, prefix="")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "graphiti-service"}


@app.get("/episodes/{conversation_id}")
async def get_episodes(conversation_id: str):
    from repositories.episode_repo import get_episode_by_conversation
    episodes = await get_episode_by_conversation(conversation_id)
    if not episodes:
        return {"conversation_id": conversation_id, "synced": False, "entities": []}
    latest = episodes[-1]
    return {
        "conversation_id": conversation_id,
        "synced": latest.status == "done",
        "status": latest.status,
        "entities_added": latest.entities_added,
        "relations_added": latest.relations_added,
    }
