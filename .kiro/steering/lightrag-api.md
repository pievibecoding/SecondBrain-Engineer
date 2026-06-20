# LightRAG API Reference — SecondBrain

> Load khi làm việc với backend/integrations/lightrag/ hoặc LightRAG config.

---

## Endpoints (LightRAG v1.5, port 9621)

### Ingest Document
```
POST /api/v1/docs
Content-Type: application/json

{
  "file_path": "/tmp/sop-onboarding.pdf",
  "metadata": {
    "source": "nas",
    "folder": "/auto-sync/HR/",
    "uploaded_by": "system",
    "nas_path": "/HR/SOP/sop-onboarding.pdf"
  }
}
→ { "id": "doc-uuid", "status": "processing" }
```

### Query Knowledge
```
POST /query
Content-Type: application/json

{
  "query": "Dự án Heineken dùng motor gì?",
  "mode": "mix"  ← LUÔN dùng "mix" (default tốt nhất)
}
→ {
    "response": "...",
    "sources": [...],
    "context": {...}
  }
```

### Query với streaming
```python
# backend/integrations/lightrag/query.py
import httpx

async def query_stream(query: str, correlation_id: str):
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{LIGHTRAG_URL}/query/stream",
            json={"query": query, "mode": "mix"},
            headers={"X-Correlation-ID": correlation_id}
        ) as response:
            async for chunk in response.aiter_text():
                yield chunk
```

### Get Entity (Wiki)
```
GET /api/v1/graph/entity/{entity_name}
→ {
    "name": "Heineken Bình Dương 2024",
    "type": "PROJECT",
    "description": "...",
    "relations": [
      {"rel_type": "CLIENT_OF", "target": "Heineken Vietnam"},
      {"rel_type": "USES", "target": "Conveyor CB-01"}
    ],
    "sources": ["BOM-Heineken-2024.xlsx", "DA-CB01-v3.pdf"]
  }

GET /api/v1/graph/edges?entity={entity_name}
→ [{"src": "...", "rel_type": "...", "tgt": "...", "description": "..."}]
```

### Delete Document
```
DELETE /api/v1/docs/{doc_id}
→ { "status": "deleted" }
```

---

## Key Config (KHÔNG thay đổi)

```ini
ENABLE_LLM_CACHE=false       # BẮTBUỘC false — tài liệu cập nhật thường xuyên
SUMMARY_LANGUAGE=Vietnamese  # entity names bằng tiếng Việt
LIGHTRAG_PROMPT_DIR=./prompts  # custom extraction prompt cho Robolinks domain
```

---

## Query Modes

| Mode | Dùng khi | Tốc độ |
|---|---|---|
| `mix` ✅ DEFAULT | Mọi trường hợp — tốt nhất | ~1.5x naive |
| `local` | Entity lookup cụ thể | Fast |
| `global` | Tổng quan, trend analysis | Medium |
| `naive` | Vector search thuần — KHÔNG dùng cho production | Fastest |
| `hybrid` | local + global, không có naive | Medium |

**KHÔNG bao giờ hardcode mode khác `mix` trong production code trừ khi có lý do rõ ràng.**

---

## Parser Pipeline

```ini
LIGHTRAG_PARSER=*:native-iteP,*:mineru-iteP,*:legacy-R
```

Thứ tự: Native → MinerU (cho PDF phức tạp) → Legacy fallback.
MinerU cloud có quota — nếu quota hết, Native vẫn chạy được cho DOCX/XLSX/PPTX.

---

## LightRAG integration code pattern

```python
# backend/integrations/lightrag/query.py
import httpx
from backend.config import settings

LIGHTRAG_URL = settings.LIGHTRAG_URL  # http://lightrag:9621

async def query(
    query_text: str,
    correlation_id: str,
    mode: str = "mix"  # luôn mix nếu không có lý do đặc biệt
) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{LIGHTRAG_URL}/query",
                json={"query": query_text, "mode": mode},
                headers={
                    "X-Correlation-ID": correlation_id,
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise LightRAGError(f"Query failed: {e.response.status_code}")
        except httpx.TimeoutException:
            raise LightRAGError("LightRAG query timeout")
```

---

## LightRAG Docker image

```yaml
# docker-compose.yml — pin version, KHÔNG dùng :latest
lightrag:
  image: ghcr.io/hkuds/lightrag:v1.5.4
  env_file: ./lightrag/.env
  depends_on: [postgres, redis]
  ports: ["9621:9621"]
  volumes:
    - ./lightrag/storage:/app/storage
    - ./prompts:/app/prompts  # custom Robolinks extraction prompt
```
