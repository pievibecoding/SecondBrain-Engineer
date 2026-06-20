# SecondBrain — AI Agent Instructions

> Auto-discovered by Kilo Code, Cursor, Windsurf, and other AGENTS.md-compatible tools.
> Source of truth: `.kiro/steering/` — edit files there, then run `scripts/sync-ai-rules.ps1`

---

## Project Summary

**SecondBrain** là bộ nhớ kỹ thuật của **Robolinks** — middleware app lưu tài liệu từ Synology NAS,
tạo knowledge graph, cho kỹ sư chat hỏi đáp với AI, và làm giàu graph từ hội thoại hàng ngày.

**Stack:** React + Vite (port 3000) · FastAPI (8000) · LightRAG v1.5 (9621) · Graphiti (9622) · PostgreSQL 18 + pgvector + AGE · Redis · MinIO · Seq

---

## Critical Rules (không có ngoại lệ)

- `schemas/` = Pydantic only · `models/` = SQLAlchemy only · `services/` = no httpx · `integrations/` = HTTP clients only
- LightRAG query mode = **`mix`** mặc định — KHÔNG hardcode mode khác
- `ENABLE_LLM_CACHE=false` — tài liệu cập nhật thường xuyên
- nas-connector KHÔNG lưu SQLite — single source of truth là PostgreSQL
- Frontend: Component → Hook → api/ → Backend (component KHÔNG gọi api/ trực tiếp)
- Mọi integration call PHẢI forward `X-Correlation-ID` header

---

## Full Rules

Chi tiết đầy đủ trong `.kiro/steering/`:

| File | Nội dung |
|---|---|
| `project-context.md` | Stack, data flows, key decisions |
| `backend-rules.md` | Folder structure, Pydantic V2, async SQLAlchemy |
| `frontend-rules.md` | Component/Hook/api chain, SSE streaming |
| `lightrag-api.md` | LightRAG endpoints, query modes, Docker config |
| `graphiti-api.md` | Graphiti endpoints, conversation memory pattern |
| `nas-rules.md` | NAS state machine, file detection, folder types |
| `test-conventions.md` | Test structure, fixtures, naming convention |
| `spec-creation-rules.md` | Steering & Skills section trong requirements.md |

---

*Kilo Code users: `kilo.jsonc` tự động load tất cả files trên — không cần làm gì thêm.*
