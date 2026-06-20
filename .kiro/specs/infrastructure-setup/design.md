# Design Document — Infrastructure Setup

## Overview

Tài liệu này mô tả thiết kế kỹ thuật cho việc bootstrap toàn bộ Docker Compose stack của SecondBrain.
Không có application code mới được viết trong spec này — tất cả deliverables là file cấu hình,
file compose, environment templates, và utility scripts.

Ngôn ngữ chính: **Shell/Python** (scripts), **YAML** (compose), **INI** (env files), **Plain text** (prompts).

---

## 1. Kiến trúc tổng thể

### 1.1 Service Map

```
┌──────────────────────────────────────────────────────────┐
│                    Docker Network                        │
│                                                          │
│  ┌─────────────┐    ┌─────────────┐   ┌──────────────┐  │
│  │  frontend   │    │   backend   │   │ nas-connector│  │
│  │  :3000      │───▶│   :8000     │◀──│   (no port)  │  │
│  └─────────────┘    └──────┬──────┘   └──────────────┘  │
│                             │                            │
│         ┌───────────────────┼───────────────────┐        │
│         ▼                   ▼                   ▼        │
│  ┌─────────────┐    ┌─────────────┐   ┌──────────────┐  │
│  │  lightrag   │    │  graphiti   │   │    postgres  │  │
│  │  :9621      │    │  :9622      │   │    :5432     │  │
│  └──────┬──────┘    └─────────────┘   └──────────────┘  │
│         │                                                │
│  ┌──────▼──────┐    ┌─────────────┐   ┌──────────────┐  │
│  │    redis    │    │    minio    │   │     seq      │  │
│  │  :6379      │    │  :9000/9001 │   │  :80 / :5341 │  │
│  └─────────────┘    └─────────────┘   └──────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### 1.2 Service Details

| Service | Image | Port(s) | Role |
|---|---|---|---|
| `postgres` | `pgvector/pgvector:pg18` | 5432 | Primary DB: relational + vector + graph |
| `redis` | `redis:7-alpine` | 6379 | Queue và cache |
| `minio` | `minio/minio` | 9000, 9001 | Object storage (NAS originals) |
| `lightrag` | `ghcr.io/hkuds/lightrag:v1.5.4` | 9621 | Knowledge graph + vector engine |
| `graphiti-service` | build: `./graphiti-service` | 9622 | Conversation memory |
| `nas-connector` | build: `./nas-connector` | — | NAS file watcher |
| `backend` | build: `./backend` | 8000 | FastAPI orchestrator |
| `frontend` | build: `./frontend` | 3000 | React UI |
| `seq` | `datalust/seq:latest` | 80, 5341 | Centralized logging |
| `ollama` | `ollama/ollama` | 11434 | **COMMENTED OUT** — Phase 2 GPU only |

---

## 2. File Structure Deliverables

```
SecondBrain/
├── docker-compose.yml           ← Production stack (Req 1)
├── docker-compose.dev.yml       ← Dev override: hot-reload (Req 5)
├── .env.example                 ← Stack-wide env template (Req 3)
│
├── lightrag/
│   └── .env                     ← LightRAG-specific config (Req 2)
│
├── prompts/
│   └── extraction.txt           ← Robolinks EXTRACT LLM prompt (Req 4)
│
└── scripts/
    ├── setup.sh                 ← First-time env init (Req 6)
    └── seed-test-data.py        ← Upload test doc + query LightRAG (Req 6)
```

---

## 3. docker-compose.yml — Design chi tiết

### 3.1 Service definitions

```yaml
version: "3.9"

services:
  postgres:
    image: pgvector/pgvector:pg18
    environment:
      POSTGRES_USER: secondbrain
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: secondbrain
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    restart: unless-stopped

  lightrag:
    image: ghcr.io/hkuds/lightrag:v1.5.4
    env_file: ./lightrag/.env
    depends_on:
      - postgres
      - redis
    ports:
      - "9621:9621"
    volumes:
      - ./lightrag/storage:/app/storage
      - ./prompts:/app/prompts
    restart: unless-stopped

  graphiti-service:
    build: ./graphiti-service
    env_file: .env
    depends_on:
      - postgres
    ports:
      - "9622:9622"
    restart: unless-stopped

  nas-connector:
    build: ./nas-connector
    env_file: .env
    depends_on:
      - lightrag
      - backend
    volumes:
      - /mnt/synology:/mnt/nas:ro
    restart: unless-stopped

  backend:
    build: ./backend
    env_file: .env
    depends_on:
      - postgres
      - redis
      - lightrag
      - graphiti-service
    ports:
      - "8000:8000"
    restart: unless-stopped

  frontend:
    build: ./frontend
    depends_on:
      - backend
    ports:
      - "3000:3000"
    restart: unless-stopped

  seq:
    image: datalust/seq:latest
    environment:
      ACCEPT_EULAS: "Y"
    volumes:
      - seq_data:/data
    ports:
      - "80:80"
      - "5341:5341"
    restart: unless-stopped

  # ─── Phase 2: GPU server only ───────────────────────────────────
  # Uncomment khi có server RTX 4060 Ti 16GB
  # ollama:
  #   image: ollama/ollama
  #   ports:
  #     - "11434:11434"
  #   volumes:
  #     - ollama_data:/root/.ollama
  #   deploy:
  #     resources:
  #       reservations:
  #         devices:
  #           - driver: nvidia
  #             count: 1
  #             capabilities: [gpu]
  # ────────────────────────────────────────────────────────────────

volumes:
  postgres_data:
  minio_data:
  seq_data:
  # ollama_data:  # uncomment Phase 2
```

### 3.2 Volume strategy

- `postgres_data`: Persistent — tất cả data: relational, pgvector, graph
- `minio_data`: Persistent — file gốc từ NAS (backup)
- `seq_data`: Persistent — log history cho debugging
- `./lightrag/storage`: Bind mount — gitignored, LightRAG working directory
- `./prompts`: Bind mount — version-controlled extraction prompts
- `/mnt/synology:/mnt/nas:ro`: Host bind mount — Synology SMB mount, read-only

### 3.3 Network

Tất cả services ở cùng default bridge network. Services giao tiếp với nhau qua service name (e.g., `http://lightrag:9621`, `http://backend:8000`).

---

## 4. LightRAG .env — Design chi tiết

### 4.1 Cấu trúc file `lightrag/.env`

File này được load bởi `env_file: ./lightrag/.env` trong docker-compose.

```ini
# ─── NAS — Synology SMB (LAN) ────────────────────────────────────
NAS_HOST=192.168.1.x
NAS_USER=secondbrain
NAS_PASS=your_nas_password
NAS_SHARE=documents
NAS_MOUNT_PATH=/mnt/synology

# ─── LLM — Phase 1: Gemini Flash Lite ───────────────────────────
LLM_BINDING=gemini
LLM_MODEL=gemini-2.0-flash-lite
GEMINI_API_KEY=AIza...

# ─── LLM — Phase 2: Ollama (commented out) ──────────────────────
# Uncomment khi có GPU server RTX 4060 Ti 16GB
# LLM_BINDING=ollama
# LLM_MODEL=qwen2.5:14b
# OLLAMA_HOST=http://ollama:11434

# Role-specific LLM (Phase 2 Ollama, commented out)
# EXTRACT_LLM_BINDING=ollama
# EXTRACT_LLM_MODEL=qwen2.5:14b
# QUERY_LLM_BINDING=ollama
# QUERY_LLM_MODEL=qwen2.5:7b
# KEYWORDS_LLM_BINDING=ollama
# KEYWORDS_LLM_MODEL=qwen2.5:3b

# ─── Embedding ───────────────────────────────────────────────────
EMBEDDING_BINDING=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIM=768
# Upgrade: bge-m3 khi có GPU (requires EMBEDDING_DIM=1024)
# EMBEDDING_MODEL=bge-m3
# EMBEDDING_DIM=1024

# ─── Storage — PostgreSQL all-in-one ─────────────────────────────
KV_STORAGE=PGKVStorage
VECTOR_STORAGE=PGVectorStorage
GRAPH_STORAGE=PGGraphStorage
DOC_STATUS_STORAGE=PGDocStatusStorage
POSTGRES_URL=postgresql://secondbrain:password@postgres:5432/lightrag

# ─── Document Processing ─────────────────────────────────────────
LIGHTRAG_PARSER=*:native-iteP,*:mineru-iteP,*:legacy-R
VLM_PROCESS_ENABLE=false
SUMMARY_LANGUAGE=Vietnamese

# ─── Performance ─────────────────────────────────────────────────
MAX_ASYNC_LLM=4
MAX_PARALLEL_INSERT=2
EMBEDDING_FUNC_MAX_ASYNC=8
EMBEDDING_BATCH_NUM=16

# ─── Query ───────────────────────────────────────────────────────
# BẮTBUỘC false — tài liệu Robolinks cập nhật thường xuyên, cache cũ = sai
ENABLE_LLM_CACHE=false
```

### 4.2 Giải thích quyết định quan trọng

| Setting | Giá trị | Lý do |
|---|---|---|
| `ENABLE_LLM_CACHE=false` | false | **Bắtbuộc** — tài liệu Robolinks cập nhật thường xuyên; cache LLM cũ sẽ trả kết quả sai |
| `SUMMARY_LANGUAGE=Vietnamese` | Vietnamese | Entity names phải bằng tiếng Việt để match câu hỏi của kỹ sư |
| `LIGHTRAG_PARSER` | `*:native-iteP,*:mineru-iteP,*:legacy-R` | Thứ tự: Native → MinerU (PDF phức tạp) → Legacy fallback. MinerU cloud có quota |
| `KV/VECTOR/GRAPH_STORAGE` | PG* | All-in-one PostgreSQL — không cần thêm graph DB riêng |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Phase 1: Ollama local, 768 dim, đủ cho MVP. Nâng lên bge-m3 khi có GPU |

---

## 5. .env.example — Design chi tiết

File template này được copy thành `.env` khi setup lần đầu:

```ini
# =================================================================
# SecondBrain — Stack-wide Environment Template
# Copy file này thành .env và điền vào các giá trị thực
# KHÔNG commit file .env vào git
# =================================================================

# ─── NAS — Synology ──────────────────────────────────────────────
NAS_HOST=192.168.1.x
NAS_USER=secondbrain
NAS_PASS=your_nas_password
NAS_SHARE=documents
NAS_MOUNT_PATH=/mnt/synology

# ─── LLM — Gemini (Phase 1) ──────────────────────────────────────
GEMINI_API_KEY=AIza...

# ─── Database — PostgreSQL ───────────────────────────────────────
POSTGRES_USER=secondbrain
POSTGRES_PASSWORD=your_strong_password_here
POSTGRES_DB=secondbrain
POSTGRES_URL=postgresql://secondbrain:your_strong_password_here@postgres:5432/secondbrain

# ─── MinIO — Object Storage ──────────────────────────────────────
MINIO_USER=secondbrain
MINIO_PASSWORD=your_minio_password_here
MINIO_URL=http://minio:9000

# ─── Seq — Logging ───────────────────────────────────────────────
SEQ_URL=http://seq:5341
SEQ_API_KEY=

# ─── Service URLs (internal Docker network) ──────────────────────
LIGHTRAG_URL=http://lightrag:9621
GRAPHITI_URL=http://graphiti-service:9622
BACKEND_API_URL=http://backend:8000

# ─── Auth ────────────────────────────────────────────────────────
JWT_SECRET_KEY=your_jwt_secret_here_min_32_chars
JWT_EXPIRE_HOURS=24
```

---

## 6. prompts/extraction.txt — Design chi tiết

Prompt này được LightRAG load từ `./prompts` volume khi thực hiện entity extraction.
Viết bằng tiếng Việt để model hiểu context domain Robolinks.

```
Bạn là chuyên gia phân tích tài liệu kỹ thuật của công ty tự động hóa Robolinks.
Nhiệm vụ: trích xuất entity và relation từ đoạn văn bản dưới đây.

Entity types cần nhận diện:
- PROJECT: tên dự án (thường kèm tên khách hàng + năm, ví dụ "Heineken Bình Dương 2024")
- CLIENT: tên khách hàng/đối tác
- EQUIPMENT: tên thiết bị/máy móc cụ thể trong dự án (conveyor, robot, tủ điện...)
- COMPONENT: linh kiện, module với model cụ thể (Motor Siemens 1LE1, Inverter G120...)
- SUPPLIER: nhà cung cấp (Siemens, Mitsubishi, Sick, Omron, ABB, Schneider, Pilz...)
- PERSON: tên người + vai trò (kỹ sư điện, PM, kỹ thuật viên cơ khí...)
- PROCESS: tên quy trình/thủ tục (FAT, SAT, nghiệm thu, bảo trì định kỳ...)
- ERROR_CODE: mã lỗi thiết bị (F0011, E007, Alarm 32...)
- DOCUMENT: tên/mã tài liệu cụ thể (bản vẽ, BOM, manual...)
- LOCATION: địa điểm nhà máy, khu vực lắp đặt

Chỉ extract entity rõ ràng, không suy diễn. Output JSON:
{"entities": [{"name": "...", "type": "...", "description": "..."}],
 "relations": [{"src": "...", "rel_type": "...", "tgt": "...", "description": "..."}]}
```

---

## 7. docker-compose.dev.yml — Design chi tiết

Override file này chỉ chứa sự khác biệt so với `docker-compose.yml`.
Chạy bằng: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up`

```yaml
version: "3.9"

services:
  backend:
    build:
      context: ./backend
      target: development
    volumes:
      - ./backend:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      - DEBUG=true

  frontend:
    build:
      context: ./frontend
      target: development
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev

  nas-connector:
    build:
      context: ./nas-connector
      target: development
    volumes:
      - ./nas-connector:/app
    command: watchmedo auto-restart --directory=. --pattern="*.py" --recursive -- python main.py

  graphiti-service:
    build:
      context: ./graphiti-service
      target: development
    volumes:
      - ./graphiti-service:/app
    command: uvicorn main:app --host 0.0.0.0 --port 9622 --reload
```

---

## 8. scripts/ — Design chi tiết

### 8.1 setup.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== SecondBrain — First-time setup ==="

# 1. Tạo .env từ template nếu chưa có
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Tạo .env từ .env.example — hãy điền các giá trị thực vào .env"
else
    echo "ℹ️  .env đã tồn tại — bỏ qua"
fi

# 2. Tạo lightrag .env từ template nếu chưa có
if [ ! -f lightrag/.env ]; then
    cp lightrag/.env.example lightrag/.env 2>/dev/null || \
    echo "⚠️  Không tìm thấy lightrag/.env.example — cần tạo thủ công"
else
    echo "ℹ️  lightrag/.env đã tồn tại — bỏ qua"
fi

# 3. Tạo thư mục storage cho LightRAG
mkdir -p lightrag/storage
echo "✅ Tạo lightrag/storage/"

echo ""
echo "=== Bước tiếp theo ==="
echo "1. Điền giá trị thực vào .env và lightrag/.env"
echo "2. Mount NAS: sudo mount -t cifs //NAS_HOST/documents /mnt/synology -o username=secondbrain,..."
echo "3. Chạy stack: docker compose up -d"
echo "4. Kiểm tra: python scripts/seed-test-data.py"
```

### 8.2 seed-test-data.py

```python
#!/usr/bin/env python3
"""
SecondBrain — Stack validation script.
Upload 1 test document to LightRAG và query để kiểm tra stack hoạt động.
"""
import httpx
import json
import sys
import time

LIGHTRAG_URL = "http://localhost:9621"

def test_ingest():
    """POST test document, verify status=processing."""
    payload = {
        "file_path": "/tmp/test-robolinks.txt",
        "metadata": {
            "source": "seed-test",
            "nas_path": "/test/test-robolinks.txt",
            "folder": "/test/"
        }
    }
    # Tạo file test tạm
    test_content = (
        "Dự án Heineken Bình Dương 2024. "
        "Motor Siemens 1LE1 7.5kW. "
        "Inverter G120. Kỹ sư Nguyễn Văn A."
    )
    with open("/tmp/test-robolinks.txt", "w", encoding="utf-8") as f:
        f.write(test_content)

    resp = httpx.post(
        f"{LIGHTRAG_URL}/api/v1/docs",
        json=payload,
        timeout=30.0
    )
    resp.raise_for_status()
    result = resp.json()

    assert "status" in result, f"Response missing 'status': {result}"
    assert result["status"] == "processing", f"Expected 'processing', got: {result['status']}"
    print(f"✅ Ingest test passed — doc_id={result.get('id')}, status={result['status']}")
    return result.get("id")

def test_query():
    """POST query, verify no HTTP error (empty result is OK)."""
    payload = {"query": "Heineken motor", "mode": "mix"}
    resp = httpx.post(
        f"{LIGHTRAG_URL}/api/v1/query",
        json=payload,
        timeout=60.0
    )
    resp.raise_for_status()
    result = resp.json()
    print(f"✅ Query test passed — response keys: {list(result.keys())}")

def main():
    print("=== SecondBrain Stack Validation ===")
    print(f"Target: {LIGHTRAG_URL}")
    print()

    try:
        test_ingest()
        # Wait briefly for LightRAG to register the doc
        time.sleep(2)
        test_query()
        print()
        print("✅ All validation tests passed")
    except httpx.ConnectError:
        print(f"❌ Cannot connect to LightRAG at {LIGHTRAG_URL}")
        print("   → Stack chưa chạy? Thử: docker compose up -d")
        sys.exit(1)
    except AssertionError as e:
        print(f"❌ Validation failed: {e}")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP error: {e.response.status_code} — {e.response.text}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## 9. Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do.*

**Lưu ý:** Spec này hoàn toàn là infrastructure configuration (YAML, env files, shell scripts, prompt text). Theo định nghĩa của Property-Based Testing, PBT phù hợp cho pure functions với input/output rõ ràng nơi mà việc chạy 100+ iterations với random inputs có thể tìm thêm bugs.

Tất cả acceptance criteria ở đây là:
- Configuration file correctness checks (deterministic, no input variation)
- Integration tests against a running Docker stack (external services, not our code)
- Shell script behavior (single execution)

**Kết luận: Không có correctness properties phù hợp cho property-based testing trong spec này.**
Tất cả validation nên được thực hiện bằng:
- **Smoke tests**: Kiểm tra file tồn tại, key=value đúng trong config files
- **Integration tests**: `docker compose up -d` → verify endpoints accessible → POST test doc → query

Xem `scripts/seed-test-data.py` (Section 8.2) là implementation của integration test.
