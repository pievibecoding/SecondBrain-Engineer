# Graphiti Service API Reference — SecondBrain

> Load khi làm việc với graphiti-service/ hoặc backend/integrations/graphiti.py.

---

## Graphiti là gì

Graphiti xử lý **conversation memory** — extract entity/relation từ hội thoại,
lưu vào temporal graph (biết info được nói khi nào, mark edge "expired" nếu cũ).

**Khác LightRAG:** LightRAG xử lý tài liệu tĩnh. Graphiti xử lý hội thoại động.

---

## graphiti-service endpoints (port 9622)

### Extract từ conversation
```
POST /extract
Content-Type: application/json
X-Correlation-ID: {uuid}   ← BẮTBUỘC forward từ backend

{
  "conversation_id": "conv-uuid-123",
  "turns": [
    {"role": "user", "content": "Dự án Alpha dùng tech stack gì?"},
    {"role": "assistant", "content": "Dự án Alpha dùng React 18, FastAPI..."}
  ],
  "timestamp": "2026-06-15T10:32:00"
}
→ { "ok": true, "entities_added": 4, "relations_added": 2 }
```

### Get episode status
```
GET /episodes/{conversation_id}
→ { "conversation_id": "...", "synced": true, "entities": [...] }
```

---

## Khi nào trigger Graphiti

Graphiti chạy **background sau khi chat response đã trả về** — không blocking user.

```python
# backend/services/conversation_service.py

async def save_message_and_trigger_graphiti(
    db: AsyncSession,
    conversation_id: str,
    user_message: str,
    assistant_response: str,
    correlation_id: str
) -> None:
    # 1. Lưu message vào DB
    message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=assistant_response,
        graphiti_synced=False  # chưa sync
    )
    db.add(message)
    await db.commit()

    # 2. Trigger Graphiti background (không await — fire and forget)
    asyncio.create_task(
        graphiti_client.extract(
            conversation_id=conversation_id,
            turns=[
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_response}
            ],
            correlation_id=correlation_id
        )
    )
```

---

## Graphiti integration code pattern

```python
# backend/integrations/graphiti.py
import httpx
from backend.config import settings

GRAPHITI_URL = settings.GRAPHITI_URL  # http://graphiti-service:9622

async def extract(
    conversation_id: str,
    turns: list[dict],
    correlation_id: str  # BẮTBUỘC — để log trace được
) -> dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{GRAPHITI_URL}/extract",
                json={
                    "conversation_id": conversation_id,
                    "turns": turns,
                    "timestamp": datetime.utcnow().isoformat()
                },
                headers={
                    "X-Correlation-ID": correlation_id  # BẮTBUỘC forward
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # Log nhưng không raise — Graphiti failure không block user
            logger.warning(
                "Graphiti extract failed",
                status=e.response.status_code,
                correlation_id=correlation_id
            )
            return {"ok": False}
        except Exception as e:
            logger.warning("Graphiti extract error", error=str(e))
            return {"ok": False}
```

---

## graphiti-service internal structure

```python
# graphiti-service/services/extractor.py
# Dùng graphiti-core để extract entity/relation từ chat turns

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

async def extract_from_turns(
    turns: list[dict],
    conversation_id: str,
    timestamp: str
) -> None:
    client = Graphiti(neo4j_uri, neo4j_user, neo4j_password)
    await client.add_episode(
        name=f"conversation-{conversation_id}",
        episode_body=format_turns_as_text(turns),
        source=EpisodeType.text,
        source_description="SecondBrain chat conversation",
        reference_time=datetime.fromisoformat(timestamp)
    )
```

---

## Graphiti vs LightRAG — không lẫn lộn

| | LightRAG | Graphiti |
|---|---|---|
| Input | Tài liệu (PDF, DOCX...) | Hội thoại (chat turns) |
| Graph update | Batch khi ingest | Real-time sau mỗi chat |
| Temporal | Không | Có — biết khi nào info được nói |
| Port | 9621 | 9622 |
| Integration | `backend/integrations/lightrag/` | `backend/integrations/graphiti.py` |

---

## Docker setup

```yaml
# docker-compose.yml — pin version
graphiti-service:
  build: ./graphiti-service
  env_file: .env
  depends_on: [postgres]
  ports: ["9622:9622"]

# graphiti-service/requirements.txt
graphiti-core==0.4.2  # pin version — KHÔNG dùng >=
```
