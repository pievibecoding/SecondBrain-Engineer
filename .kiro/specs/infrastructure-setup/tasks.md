# Implementation Plan: Infrastructure Setup

## Overview

Bootstrap toàn bộ Docker Compose stack cho SecondBrain: postgres, redis, minio, lightrag, seq cùng
các custom services (graphiti-service, nas-connector, backend, frontend). Cung cấp cấu hình LightRAG
cho Phase 1 (Gemini API), template env, Robolinks extraction prompt, dev override, và validation scripts.

Không có application code mới — tất cả tasks là tạo/chỉnh sửa file cấu hình.

---

## Tasks

- [x] 1. Tạo cấu trúc thư mục cơ bản
  - Tạo các thư mục: `lightrag/storage/`, `lightrag/` (nếu chưa có), `prompts/`, `scripts/`
  - Tạo `lightrag/.gitignore` để loại trừ `storage/` (chứa LightRAG working data)
  - Tạo `lightrag/storage/.gitkeep` để giữ thư mục trong git
  - _Requirements: 1.13_

- [x] 2. Viết `docker-compose.yml` — production stack
    - [x] 2.1 Định nghĩa infrastructure services: `postgres`, `redis`, `minio`, `seq`
    - `postgres`: image `pgvector/pgvector:pg18`, port 5432, volume `postgres_data`, env vars từ `${POSTGRES_*}`
    - `redis`: image `redis:7-alpine`, port 6379
    - `minio`: image `minio/minio`, command `server /data --console-address ":9001"`, ports 9000/9001, volume `minio_data`
    - `seq`: image `datalust/seq:latest`, `ACCEPT_EULAS=Y`, ports 80/5341, volume `seq_data`
    - _Requirements: 1.1, 1.3, 1.4, 1.6, 1.7, 1.8, 1.9, 1.12, 1.15, 1.16_
    - [x] 2.2 Định nghĩa `lightrag` service
    - Image pinned: `ghcr.io/hkuds/lightrag:v1.5.4`
    - `env_file: ./lightrag/.env`
    - `depends_on: [postgres, redis]`
    - Port 9621, volumes: `./lightrag/storage:/app/storage` và `./prompts:/app/prompts`
    - _Requirements: 1.2, 1.5, 1.13, 1.19_
    - [x] 2.3 Định nghĩa custom services: `graphiti-service`, `nas-connector`, `backend`, `frontend`
    - `graphiti-service`: build `./graphiti-service`, port 9622, depends_on postgres
    - `nas-connector`: build `./nas-connector`, depends_on lightrag + backend, volume `/mnt/synology:/mnt/nas:ro`
    - `backend`: build `./backend`, port 8000, depends_on postgres/redis/lightrag/graphiti-service
    - `frontend`: build `./frontend`, port 3000, depends_on backend
    - _Requirements: 1.1, 1.10, 1.11, 1.14, 1.20, 1.21_
    - [x] 2.4 Thêm commented-out `ollama` service và định nghĩa volumes
    - Comment block `ollama` với ghi chú "Phase 2: uncomment khi có GPU server"
    - Named volumes: `postgres_data`, `minio_data`, `seq_data`
    - _Requirements: 1.12, 1.17_

- [x] 3. Viết `lightrag/.env` — LightRAG configuration (tạoed `lightrag/.env.example`)
    - [x] 3.1 Cấu hình LLM và embedding
    - Phase 1: `LLM_BINDING=gemini`, `LLM_MODEL=gemini-2.0-flash-lite`, `GEMINI_API_KEY=AIza...`
    - Embedding: `EMBEDDING_BINDING=ollama`, `EMBEDDING_MODEL=nomic-embed-text`, `EMBEDDING_DIM=768`
    - Comment block Phase 2 Ollama models với role-specific variables (EXTRACT/QUERY/KEYWORDS)
    - _Requirements: 2.1, 2.2, 2.10, 2.11, 2.14, 2.15_
    - [x] 3.2 Cấu hình storage và document processing
    - Storage: `KV_STORAGE=PGKVStorage`, `VECTOR_STORAGE=PGVectorStorage`, `GRAPH_STORAGE=PGGraphStorage`, `DOC_STATUS_STORAGE=PGDocStatusStorage`
    - `POSTGRES_URL=postgresql://secondbrain:password@postgres:5432/lightrag`
    - `LIGHTRAG_PARSER=*:native-iteP,*:mineru-iteP,*:legacy-R`
    - `SUMMARY_LANGUAGE=Vietnamese`, `ENABLE_LLM_CACHE=false`
    - NAS variables: `NAS_HOST`, `NAS_USER`, `NAS_PASS`, `NAS_SHARE`, `NAS_MOUNT_PATH`
    - _Requirements: 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.12, 2.16_
    - [x] 3.3 Cấu hình performance tuning
    - `MAX_ASYNC_LLM=4`, `MAX_PARALLEL_INSERT=2`, `EMBEDDING_FUNC_MAX_ASYNC=8`, `EMBEDDING_BATCH_NUM=16`
    - `VLM_PROCESS_ENABLE=false`
    - _Requirements: 2.13_

- [x] 4. Viết `.env.example` — stack-wide template
  - Tạo file `.env.example` tại project root
  - Sections: NAS, LLM (Gemini), Database, MinIO, Seq, Service URLs, Auth
  - Tất cả values là placeholders: `your_password_here`, `AIza...`, `192.168.1.x`
  - Thêm comment hướng dẫn: "Copy thành .env và điền giá trị thực, KHÔNG commit .env"
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

- [x] 5. Viết `prompts/extraction.txt` — Robolinks EXTRACT prompt
  - Viết prompt tiếng Việt theo domain tự động hóa công nghiệp Robolinks
  - Định nghĩa đầy đủ 10 entity types: PROJECT, CLIENT, EQUIPMENT, COMPONENT, SUPPLIER, PERSON, PROCESS, ERROR_CODE, DOCUMENT, LOCATION
  - Quy tắc "chỉ extract entity rõ ràng, không suy diễn"
  - Output JSON format: `{"entities": [...], "relations": [...]}`
  - Xem nội dung đầy đủ trong Section 6 của design.md
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 6. Checkpoint — Kiểm tra tính nhất quán của cấu hình
  - Verify `POSTGRES_URL` trong `lightrag/.env` khớp với credentials trong `docker-compose.yml`
  - Verify tất cả `${VAR}` trong `docker-compose.yml` có tương ứng trong `.env.example`
  - Verify các port không bị conflict giữa các services
  - Đảm bảo `lightrag/storage/` được gitignore, `prompts/extraction.txt` được track
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Viết `docker-compose.dev.yml` — development override
  - Override `backend`: mount `./backend:/app`, command `uvicorn main:app --reload`
  - Override `frontend`: mount `./frontend:/app`, command `npm run dev`
  - Override `nas-connector`: mount `./nas-connector:/app`, dùng `watchmedo auto-restart`
  - Override `graphiti-service`: mount `./graphiti-service:/app`, command với `--reload`
  - Chỉ define services cần override — infrastructure services (postgres, redis, minio, seq, lightrag) KHÔNG cần thay đổi
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 8. Viết scripts
    - [x] 8.1 Viết `scripts/setup.sh`
    - Check và tạo `.env` từ `.env.example` nếu chưa tồn tại
    - Check và tạo `lightrag/.env` nếu chưa tồn tại
    - Tạo `lightrag/storage/` directory
    - In hướng dẫn tiếp theo (mount NAS, điền .env, docker compose up)
    - `chmod +x scripts/setup.sh`
    - _Requirements: 6.1_
    - [x] 8.2 Viết `scripts/seed-test-data.py`
    - Import `httpx` (add to requirements nếu cần)
    - `test_ingest()`: POST 1 file text test đến `/api/v1/docs`, assert response chứa `"status": "processing"`
    - `test_query()`: POST query `"Heineken motor"` mode=mix đến `/api/v1/query`, assert no HTTP error
    - `main()`: xử lý connection errors rõ ràng với helpful error messages
    - Xem implementation đầy đủ trong Section 8.2 của design.md
    - _Requirements: 6.2, 6.3, 6.4_

- [x] 9. Cập nhật root `.gitignore`
  - Thêm `.env` (không commit secrets)
  - Thêm `lightrag/.env` (chứa API keys)
  - Thêm `lightrag/storage/` (LightRAG working data, có thể lớn)
  - Giữ track: `.env.example`, `lightrag/.env.example` (nếu tạo), `prompts/`, `scripts/`

- [x] 10. Final checkpoint — Verify stack integrity
  - Chạy `docker compose config` để validate YAML syntax của `docker-compose.yml`
  - Chạy `docker compose -f docker-compose.yml -f docker-compose.dev.yml config` để validate dev override
  - Kiểm tra tất cả required files tồn tại: `docker-compose.yml`, `docker-compose.dev.yml`, `.env.example`, `lightrag/.env`, `prompts/extraction.txt`, `scripts/setup.sh`, `scripts/seed-test-data.py`
  - Ensure all tests pass, ask the user if questions arise.

---

## Task Dependency Graph

- Task 1 có thể làm độc lập (tạo cấu trúc thư mục)
- Tasks 2, 3, 4, 5 có thể làm song song sau Task 1 — không phụ thuộc nhau
- Task 6 (checkpoint) phụ thuộc Tasks 2, 3, 4, 5
- Task 7 (docker-compose.dev.yml) nên làm sau Task 2 để có context
- Task 8 (scripts) nên làm sau Task 2 để có context
- Task 9 (.gitignore) có thể làm bất cứ lúc nào, nên làm sớm
- Task 10 (final checkpoint) phụ thuộc tất cả Tasks 2–9

## Notes

- Tasks 2–5 có thể làm song song — không phụ thuộc nhau
- Tasks 7–8 nên làm sau task 2 để có context đầy đủ
- `lightrag/storage/` và `.env` phải được gitignore TRƯỚC khi commit bất cứ thứ gì
- Để chạy stack thực sự: cần Gemini API key thực, NAS mount thực, và Ollama running cho embedding
- **Verify thực tế** với `scripts/seed-test-data.py` chỉ sau khi stack đang chạy với credentials thực
- Không có property-based tests trong spec này — toàn bộ là config files và integration scripts
