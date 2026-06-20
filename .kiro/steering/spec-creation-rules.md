# Spec Creation Rules — SecondBrain

> Load khi tạo hoặc review file requirements.md trong .kiro/specs/

---

## Bắtbuộc: Mỗi Requirement phải có section Steering & Skills

Mỗi requirement trong `requirements.md` PHẢI có section sau ngay sau User Story,
trước Acceptance Criteria:

```markdown
## Steering & Skills

- **Steering:** [danh sách steering files áp dụng cho requirement này]
- **Skills:** [danh sách skills cần activate khi implement]
- **Reference:** [section cụ thể trong pa3-design.md hoặc tài liệu khác]
```

---

## Ví dụ đúng

```markdown
### Requirement 3 — Chat API với SSE Streaming

**User Story:** As a Robolinks engineer, I want to ask questions in Vietnamese and
receive streaming answers with citations, so that I get real-time feedback.

## Steering & Skills

- **Steering:** project-context.md, backend-rules.md, lightrag-api.md, graphiti-api.md
- **Skills:** fastapi-expert, task-breakdown, quality-assurance
- **Reference:** pa3-design Section 5.2 (Chat workflow), Section 8.2 (Chat request/response format)

#### Acceptance Criteria
...
```

---

## Cách chọn Steering phù hợp

| Loại requirement | Steering files cần include |
|---|---|
| Backend API, models, services | `project-context.md`, `backend-rules.md` |
| LightRAG calls (ingest/query/graph) | + `lightrag-api.md` |
| Graphiti calls (conversation memory) | + `graphiti-api.md` |
| NAS connector, file state machine | + `nas-rules.md` |
| Frontend components, hooks, routing | `project-context.md`, `frontend-rules.md` |
| Tests, quality gates | + `test-conventions.md` |
| Docker, infrastructure config | `project-context.md` |
| MCP server tools | `project-context.md`, `backend-rules.md` |

---

## Cách chọn Skills phù hợp

| Loại requirement | Skills cần activate |
|---|---|
| FastAPI endpoints, Pydantic schemas | `fastapi-expert` |
| Breaking design into tasks | `task-breakdown` |
| Test strategy, quality gates | `quality-assurance` |
| MCP server implementation | `mcp-builder` |
| Frontend UI components | `frontend-design` |
| Playwright E2E tests | `webapp-testing` |
| Tất cả requirements | `task-breakdown` (luôn cần) |

---

## Cách chọn Reference phù hợp

Luôn trỏ đến section cụ thể trong `docs/brainstorm/pa3-design.md`:

| Nội dung | Section trong pa3-design |
|---|---|
| API endpoints, request/response shapes | Section 8 (API contracts) |
| Database schema, ORM models | Section 7 (Data model) |
| Ingestion workflow | Section 5.1 |
| Chat + conversation memory workflow | Section 5.2 |
| Admin panel workflow | Section 5.3 |
| Services, ports, docker-compose | Section 6 (Stack & config) |
| LightRAG .env config | Section 6.2 |
| Knowledge graph entity/relation taxonomy | Section 14 |
| Test strategy, QA checklist | Section 15 |
| NAS state machine, folder types | nas-rules.md hoặc Section 5.1 |
| Wiki engine design | Section 11 |
| MCP server tools | Section 11b |

---

## Template đầy đủ cho 1 requirement

```markdown
### Requirement N — [Tên ngắn gọn]

**User Story:** As a [role], I want [feature], so that [benefit].

## Steering & Skills

- **Steering:** project-context.md, [thêm files phù hợp]
- **Skills:** task-breakdown, [thêm skills phù hợp]
- **Reference:** pa3-design Section X ([tên section]), Section Y ([tên section])

#### Acceptance Criteria

1. THE [system] SHALL [behavior] WHEN [condition].
2. ...
```

---

## Lỗi thường gặp khi thiếu section này

- AI implement sai folder structure vì không biết `schemas/` vs `models/` convention
- AI gọi LightRAG sai endpoint hoặc sai mode vì không có `lightrag-api.md` context
- AI không forward `X-Correlation-ID` vì không đọc `backend-rules.md`
- AI implement frontend component tự gọi API trực tiếp vì không có `frontend-rules.md`
