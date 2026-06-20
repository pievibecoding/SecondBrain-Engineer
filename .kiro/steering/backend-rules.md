# Backend Rules — SecondBrain

> Load khi làm việc với backend/ hoặc bất kỳ Python service nào.

---

## Folder Structure Rules (BẮTBUỘC)

| Folder | Chứa gì | KHÔNG chứa |
|---|---|---|
| `backend/schemas/` | Pydantic request/response models | SQLAlchemy models |
| `backend/models/` | SQLAlchemy ORM models (DB tables) | Pydantic models |
| `backend/services/` | Business logic thuần | httpx, requests, HTTP calls |
| `backend/integrations/` | External HTTP clients | Business logic |
| `backend/routers/` | Thin layer: validate → call service → return schema | Business logic |
| `backend/dependencies/` | FastAPI Depends functions only | — |
| `backend/middleware/` | ASGI middleware only | — |
| `backend/mcp/tools/` | Public MCP tools | Internal-only tools |
| `backend/mcp/tools/internal/` | Internal-only MCP tools | Public tools |
| `backend/migrations/` | Alembic migrations | — |

---

## Import Rules

```python
# Router imports from:
from backend.schemas.chat import ChatRequest, ChatResponse  # OK
from backend.services.auth_service import get_current_user  # OK
from backend.dependencies.auth import require_admin          # OK

# Router KHÔNG import from:
from backend.integrations.lightrag.query import ...  # KHÔNG — dùng DI
from backend.models.user import User                 # KHÔNG trực tiếp

# Service imports from:
from backend.models.nas_file import NasFile          # OK
from backend.schemas.nas import NasFileResponse      # OK

# Service KHÔNG import from:
import httpx                                         # KHÔNG trong services/
from backend.integrations.lightrag import ...        # KHÔNG — inject qua DI
```

---

## Pydantic V2 (FastAPI)

```python
# ĐÚNG — Pydantic V2 syntax
from pydantic import BaseModel, field_validator, model_config

class ChatRequest(BaseModel):
    model_config = model_config(str_strip_whitespace=True)
    message: str
    conversation_id: str | None = None  # Dùng X | None, KHÔNG Optional[X]

    @field_validator("message")         # KHÔNG @validator (V1)
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be empty")
        return v

# ĐÚNG — response_model với from_attributes
class UserResponse(BaseModel):
    model_config = model_config(from_attributes=True)
    id: str
    email: str
```

---

## Async SQLAlchemy

```python
# ĐÚNG — always async
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def get_nas_file(db: AsyncSession, file_id: str) -> NasFile | None:
    result = await db.execute(select(NasFile).where(NasFile.id == file_id))
    return result.scalar_one_or_none()

# KHÔNG dùng synchronous DB operations
```

---

## Correlation ID (BẮTBUỘC cho integrations/)

```python
# Trong backend/integrations/graphiti.py — luôn forward header
async def extract_from_conversation(
    turns: list[dict],
    correlation_id: str  # lấy từ request header
) -> None:
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{GRAPHITI_URL}/extract",
            json={"turns": turns},
            headers={"X-Correlation-ID": correlation_id}  # BẮTBUỘC
        )
```

---

## Error Handling

```python
# Dùng HTTPException với detail rõ ràng
from fastapi import HTTPException, status

raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail=f"NasFile not found: {file_id}"
)

# Integrations/ phải handle httpx errors
try:
    response = await client.post(...)
    response.raise_for_status()
except httpx.HTTPStatusError as e:
    logger.error(f"LightRAG error: {e.response.status_code}", correlation_id=cid)
    raise HTTPException(status_code=502, detail="LightRAG service error")
```

---

## Structured Logging

```python
# Luôn include correlation_id trong log
from backend.logger import logger

logger.info("Ingestion started", nas_path=nas_path, correlation_id=cid)
logger.error("LightRAG query failed", error=str(e), correlation_id=cid)
```
