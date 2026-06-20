# Requirements Document

## Introduction

Spec này thiết lập toàn bộ Docker Compose infrastructure cho dự án SecondBrain của Robolinks.
Stack gồm: PostgreSQL 18 + pgvector, Redis, MinIO, LightRAG v1.5.4, và Seq.
Ngoài ra cần cung cấp file cấu hình LightRAG `.env`, file `.env.example` cho toàn bộ stack,
prompt extraction tùy chỉnh cho domain Robolinks, và override dev với hot-reload.

Kết quả mong đợi: `docker compose up -d` chạy thành công, LightRAG Web UI accessible tại port 9621,
Seq accessible tại port 80, và LightRAG có thể nhận file + trả về kết quả query (kể cả empty).

---

## Glossary

- **Stack**: Toàn bộ tập hợp Docker services định nghĩa trong `docker-compose.yml`
- **LightRAG**: Graph + vector search engine, image `ghcr.io/hkuds/lightrag:v1.5.4`
- **Seq**: Centralized structured logging server, image `datalust/seq:latest`
- **MinIO**: Object storage server tương thích S3
- **pgvector**: PostgreSQL extension cho vector similarity search
- **EXTRACT LLM prompt**: Prompt tùy chỉnh hướng dẫn LightRAG trích xuất entity/relation theo taxonomy Robolinks
- **Phase 1 LLM**: `gemini-2.0-flash-lite` qua Gemini API — dùng khi chưa có GPU server
- **Phase 2 LLM**: Ollama local models — dùng khi có GPU server RTX 4060 Ti 16GB
- **Correlation ID**: UUID được inject vào mọi HTTP request/response để trace log

---

## Requirements

### Requirement 1 — Docker Compose Stack

**User Story:** As a developer, I want a single `docker compose up -d` command to start all required services, so that I can run the full SecondBrain stack locally without manual setup.

## Steering & Skills

- **Steering:** project-context.md
- **Skills:** task-breakdown
- **Reference:** pa3-design Section 6.1 (Services và ports), Section 6.3 (docker-compose.yml skeleton)

#### Acceptance Criteria

1. THE `docker-compose.yml` SHALL define services: `postgres`, `redis`, `minio`, `lightrag`, `seq`, `graphiti-service`, `nas-connector`, `backend`, `frontend` với đúng image và port mappings.
2. THE `docker-compose.yml` SHALL pin `lightrag` service tại image `ghcr.io/hkuds/lightrag:v1.5.4` (không dùng `:latest`).
3. THE `docker-compose.yml` SHALL pin `postgres` service tại image `pgvector/pgvector:pg18`.
4. THE `docker-compose.yml` SHALL pin `redis` service tại image `redis:7-alpine`.
5. THE `docker-compose.yml` SHALL expose `lightrag` tại port `9621:9621`.
6. THE `docker-compose.yml` SHALL expose `seq` tại ports `80:80` và `5341:5341`.
7. THE `docker-compose.yml` SHALL expose `postgres` tại port `5432:5432`.
8. THE `docker-compose.yml` SHALL expose `redis` tại port `6379:6379`.
9. THE `docker-compose.yml` SHALL expose `minio` tại ports `9000:9000` và `9001:9001`.
10. THE `docker-compose.yml` SHALL expose `backend` tại port `8000:8000` và `frontend` tại port `3000:3000`.
11. THE `docker-compose.yml` SHALL expose `graphiti-service` tại port `9622:9622`.
12. THE `docker-compose.yml` SHALL định nghĩa named volumes: `postgres_data`, `minio_data`, `seq_data`.
13. THE `docker-compose.yml` SHALL mount `./lightrag/storage:/app/storage` và `./prompts:/app/prompts` cho `lightrag` service.
14. THE `docker-compose.yml` SHALL mount `/mnt/synology:/mnt/nas:ro` (read-only) cho `nas-connector` service.
15. THE `seq` service SHALL set environment variable `ACCEPT_EULAS=Y`.
16. THE `minio` service SHALL run với command `server /data --console-address ":9001"`.
17. THE `docker-compose.yml` SHALL comment out `ollama` service (Phase 2 only) với ghi chú rõ ràng.
18. WHEN `docker compose up -d` is executed, THE Stack SHALL start tất cả services mà không có lỗi exit code.
19. THE `lightrag` service SHALL depend_on `postgres` và `redis`.
20. THE `backend` service SHALL depend_on `postgres`, `redis`, `lightrag`, và `graphiti-service`.
21. THE `nas-connector` service SHALL depend_on `lightrag` và `backend`.

---

### Requirement 2 — LightRAG Environment Configuration

**User Story:** As a developer, I want LightRAG configured correctly for Phase 1 (Gemini API), so that it can process Vietnamese documents and store all data in PostgreSQL.

## Steering & Skills

- **Steering:** project-context.md, lightrag-api.md
- **Skills:** task-breakdown
- **Reference:** pa3-design Section 6.2 (LightRAG .env config), Section 3 (Key Decisions — ENABLE_LLM_CACHE=false, SUMMARY_LANGUAGE)

#### Acceptance Criteria

1. THE `lightrag/.env` SHALL set `LLM_BINDING=gemini`.
2. THE `lightrag/.env` SHALL set `LLM_MODEL=gemini-2.0-flash-lite`.
3. THE `lightrag/.env` SHALL set `KV_STORAGE=PGKVStorage`.
4. THE `lightrag/.env` SHALL set `VECTOR_STORAGE=PGVectorStorage`.
5. THE `lightrag/.env` SHALL set `GRAPH_STORAGE=PGGraphStorage`.
6. THE `lightrag/.env` SHALL set `DOC_STATUS_STORAGE=PGDocStatusStorage`.
7. THE `lightrag/.env` SHALL set `ENABLE_LLM_CACHE=false`.
8. THE `lightrag/.env` SHALL set `SUMMARY_LANGUAGE=Vietnamese`.
9. THE `lightrag/.env` SHALL set `LIGHTRAG_PARSER=*:native-iteP,*:mineru-iteP,*:legacy-R`.
10. THE `lightrag/.env` SHALL set `EMBEDDING_BINDING=ollama`.
11. THE `lightrag/.env` SHALL set `EMBEDDING_MODEL=nomic-embed-text` và `EMBEDDING_DIM=768`.
12. THE `lightrag/.env` SHALL set `POSTGRES_URL=postgresql://secondbrain:password@postgres:5432/lightrag`.
13. THE `lightrag/.env` SHALL set `MAX_ASYNC_LLM=4`, `MAX_PARALLEL_INSERT=2`, `EMBEDDING_FUNC_MAX_ASYNC=8`, `EMBEDDING_BATCH_NUM=16`.
14. THE `lightrag/.env` SHALL include commented-out Phase 2 Ollama config (LLM_BINDING, LLM_MODEL, EXTRACT/QUERY/KEYWORDS role variables) với ghi chú rõ ràng.
15. THE `lightrag/.env` SHALL include `GEMINI_API_KEY` placeholder với giá trị mẫu `AIza...`.
16. THE `lightrag/.env` SHALL include NAS connection variables: `NAS_HOST`, `NAS_USER`, `NAS_PASS`, `NAS_SHARE`, `NAS_MOUNT_PATH`.

---

### Requirement 3 — Stack-wide Environment Template

**User Story:** As a developer, I want a `.env.example` file at the project root covering all services, so that I can set up a new environment by copying and filling in values.

## Steering & Skills

- **Steering:** project-context.md, nas-rules.md
- **Skills:** task-breakdown
- **Reference:** pa3-design Section 6.1 (Services), Section 6.2 (LightRAG config), nas-rules.md (NAS env vars)

#### Acceptance Criteria

1. THE `.env.example` SHALL exist tại root của project (`SecondBrain/.env.example`).
2. THE `.env.example` SHALL bao gồm section cho từng service: NAS, LLM (Gemini), DB (PostgreSQL), MinIO, Seq.
3. THE `.env.example` SHALL include `POSTGRES_PASSWORD` placeholder.
4. THE `.env.example` SHALL include `MINIO_USER` và `MINIO_PASSWORD` placeholders.
5. THE `.env.example` SHALL include `GEMINI_API_KEY` placeholder.
6. THE `.env.example` SHALL include NAS variables: `NAS_HOST`, `NAS_USER`, `NAS_PASS`, `NAS_SHARE`, `NAS_MOUNT_PATH`.
7. THE `.env.example` SHALL include Seq variables và backend service URLs.
8. THE `.env.example` SHALL NOT chứa giá trị bí mật thực — chỉ dùng placeholders như `your_password_here`, `AIza...`.

---

### Requirement 4 — Robolinks EXTRACT LLM Prompt

**User Story:** As a developer, I want a custom extraction prompt specific to Robolinks domain, so that LightRAG extracts entities relevant to automation engineering projects.

## Steering & Skills

- **Steering:** project-context.md, lightrag-api.md
- **Skills:** task-breakdown
- **Reference:** pa3-design Section 14 (Knowledge Graph Schema — Robolinks Domain, entity types, system prompt)

#### Acceptance Criteria

1. THE `prompts/extraction.txt` SHALL tồn tại tại `SecondBrain/prompts/extraction.txt`.
2. THE `prompts/extraction.txt` SHALL định nghĩa các entity types: `PROJECT`, `CLIENT`, `EQUIPMENT`, `COMPONENT`, `SUPPLIER`, `PERSON`, `PROCESS`, `ERROR_CODE`, `DOCUMENT`, `LOCATION`.
3. THE `prompts/extraction.txt` SHALL yêu cầu output JSON format với fields `entities` (array of `{name, type, description}`) và `relations` (array of `{src, rel_type, tgt, description}`).
4. THE `prompts/extraction.txt` SHALL viết bằng tiếng Việt, phù hợp domain tự động hóa công nghiệp Robolinks.
5. THE `prompts/extraction.txt` SHALL chỉ extract entity rõ ràng từ văn bản, không suy diễn.

---

### Requirement 5 — Development Override

**User Story:** As a developer, I want a dev override file for hot reload and debug ports, so that I can iterate faster during local development without modifying the production compose file.

## Steering & Skills

- **Steering:** project-context.md
- **Skills:** task-breakdown
- **Reference:** pa3-design Section 4 (Cấu trúc thư mục — docker-compose.dev.yml)

#### Acceptance Criteria

1. THE `docker-compose.dev.yml` SHALL tồn tại tại root của project.
2. THE `docker-compose.dev.yml` SHALL override `backend` service với hot-reload (mount source code, watch mode).
3. THE `docker-compose.dev.yml` SHALL override `frontend` service với hot-reload.
4. THE `docker-compose.dev.yml` SHALL override `nas-connector` service với hot-reload.
5. WHEN running `docker compose -f docker-compose.yml -f docker-compose.dev.yml up`, THE Stack SHALL start với hot-reload enabled cho custom-built services.

---

### Requirement 6 — Utility Scripts

**User Story:** As a developer, I want setup, seed, backup, and re-embedding scripts, so that I can initialize the environment, validate the stack, backup data, and migrate embeddings when needed.

## Steering & Skills

- **Steering:** project-context.md, lightrag-api.md
- **Skills:** task-breakdown, quality-assurance
- **Reference:** pa3-design Section 6.2 (LightRAG endpoints), Section 4 (Cấu trúc thư mục — scripts/), Section 15 (Test strategy — smoke tests)

#### Acceptance Criteria

1. THE `scripts/setup.sh` SHALL tồn tại và hướng dẫn tạo file `.env` từ `.env.example`.
2. THE `scripts/seed-test-data.py` SHALL tồn tại với example POST request đến LightRAG `/api/v1/docs`.
3. WHEN `scripts/seed-test-data.py` is executed against a running stack, THE Script SHALL upload ít nhất 1 test document và verify response contains `"status": "processing"`.
4. THE `scripts/seed-test-data.py` SHALL thực hiện 1 test query đến LightRAG `/api/v1/query` và verify response không bị HTTP error (kết quả empty là chấp nhận được).
5. THE `scripts/backup-db.sh` SHALL tồn tại và thực hiện `pg_dump` của PostgreSQL database vào file có timestamp.
6. THE `scripts/re-embed.py` SHALL tồn tại với script migration để re-embed toàn bộ documents khi đổi embedding model (dùng khi chuyển từ `nomic-embed-text` sang `bge-m3` ở Phase 2).
7. THE `scripts/re-embed.py` SHALL có warning rõ ràng rằng script này xóa và rebuild toàn bộ vector index.
