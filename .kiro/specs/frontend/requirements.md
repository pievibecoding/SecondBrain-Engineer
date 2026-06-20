# Requirements Document

## Introduction

This spec implements the Frontend for SecondBrain (React + Vite). It provides the Chat UI (SSE streaming + citations), Wiki browsing and entity pages, Admin panel for NAS queue/documents/folders, and a Graph embed for LightRAG Web UI. Frontend follows the project's Data Flow convention: Component → Hook → api/ → Backend.

**Dependency:** Spec 5 (Chat API + Streaming) and Spec 6 (Wiki Engine) must be available (backend endpoints and API contracts implemented).

**Definition of Done (summary):**
- Chat page streams tokens via `POST /api/chat/stream` and displays citations that link to MinIO or wiki pages.
- Wiki pages display entity details, relations and a mini graph; search and categories work.
- Admin panel allows approve/reject of NAS files, documents reindex/delete, and folder CRUD with require_admin guard.
- All frontend code follows frontend-rules: components use hooks, hooks call api/*. Unit tests and Playwright E2E tests exist for core flows.

---

## Glossary

- SSE: Server-Sent Events (token streaming from backend)
- CitationItem: structured citation from backend (document or graph_entity)
- Correlation ID: X-Correlation-ID request tracing header

---

## Requirements

### Requirement 1: Frontend project scaffold and docs

**User Story:** As a developer I want a reproducible frontend project with run/test instructions so that other developers can start the app and run tests.

## Steering & Skills

- **Steering:** project-context.md, frontend-rules.md
- **Skills:** frontend-design, task-breakdown
- **Reference:** pa3-design Section 4 (frontend structure), Spec Plan Spec 9

#### Acceptance Criteria

1. The repo contains `frontend/README.md` with `pnpm install`, `pnpm dev`, `pnpm test`, and `pnpm test:e2e` instructions.
2. `.env.example` contains `VITE_API_BASE` and `VITE_CORRELATION_ID_ENABLED` entries.
3. Package scripts include: `dev`, `build`, `preview`, `test`, `test:e2e`.

---

### Requirement 2: API client and streaming helper (src/api/client.ts)

**User Story:** As a frontend developer I want a single HTTP client and SSE helper so hooks and api modules share consistent headers, error handling, and X-Correlation-ID forwarding.

## Steering & Skills

- **Steering:** project-context.md, frontend-rules.md, backend-rules.md
- **Skills:** frontend-design, task-breakdown
- **Reference:** pa3-design Section 8 (API contracts), frontend-rules.md (api/ layer)

#### Acceptance Criteria

1. `frontend/src/api/client.ts` exposes: baseUrl from env, `getCorrelationId()`, `setCorrelationId(id?)`, `request` wrapper and `ssePost(url, body, {onMessage,onDone,onError,signal})` helper.
2. All requests attach `Authorization: Bearer <token>` when present and `X-Correlation-ID` header.
3. `ssePost` implements POST-based SSE using `fetch` + ReadableStream and supports AbortController cancellation.
4. Unit tests for client validate header propagation and SSE chunk parsing.

---

### Requirement 3: Auth context and routing guard

**User Story:** As a user I want to sign in and be redirected to protected pages; admin routes require admin role.

## Steering & Skills

- **Steering:** project-context.md, frontend-rules.md
- **Skills:** frontend-design, task-breakdown
- **Reference:** pa3-design Section 4 (Auth context), Spec Plan Spec 9 — Auth

#### Acceptance Criteria

1. `AuthContext` and `useAuth` exist and export: `login`, `logout`, `currentUser`, `isAdmin`.
2. Token is stored in sessionStorage (MVP) and cleared on logout.
3. `routes/_protected.tsx` redirects unauthenticated users to `/sign-in` and AdminLayout enforces `isAdmin`.
4. Tests cover login/logout state transitions.

---

### Requirement 4: Chat API layer, hook and streaming UI

**User Story:** As an engineer I want real-time streaming chat with citations so I can read answers immediately and verify sources.

## Steering & Skills

- **Steering:** project-context.md, frontend-rules.md, lightrag-api.md, graphiti-api.md
- **Skills:** frontend-design, webapp-testing, task-breakdown
- **Reference:** pa3-design Section 5.2 (Chat workflow), Section 8.2 (Chat request/response), Spec Plan Spec 9 Chat UI

#### Acceptance Criteria

1. `frontend/src/api/chat.ts` exports `streamChat(conversationId, message, callbacks)` and `getChatHistory(conversationId)`.
2. `frontend/src/hooks/useChat.ts` exposes `{messages, send(message), streaming, cancel, currentConversationId}` and persists conversation id in session state.
3. Chat page (`routes/chat/index.tsx`) displays streaming tokens progressively via aria-live region and final assembled message includes clickable CitationCards.
4. CitationCard click: document opens MinIO URL in new tab; graph_entity navigates to wiki route.
5. Cancelation of streaming works and cleans up state; unit tests simulate SSE stream and verify final message assembly and citations parsing.

---

### Requirement 5: Wiki API layer, hooks and pages

**User Story:** As an engineer I want to browse entities and view wiki pages assembled from graph data so I can find project/equipment information quickly.

## Steering & Skills

- **Steering:** project-context.md, frontend-rules.md, lightrag-api.md
- **Skills:** frontend-design, task-breakdown
- **Reference:** pa3-design Section 11 (Wiki engine), Section 14 (Entity taxonomy)

#### Acceptance Criteria

1. `frontend/src/api/wiki.ts` implements `getEntities(type?)`, `getEntity(name)`, `searchEntities(q)`.
2. Hooks `useWikiCategories`, `useWikiEntity(name)`, `useWikiSearch` provide loading/error states and caching.
3. `routes/wiki/index.tsx` shows categories and search; `routes/wiki/[name].tsx` renders entity page with relations, sources and RelationGraph component.
4. The Wiki page includes an action to "Hỏi AI về [entity]" that navigates to Chat with pre-filled context.

---

### Requirement 6: Admin panel (NAS queue, documents, folders)

**User Story:** As an admin I want to approve or reject NAS files, manage indexed documents and configure folders so ingestion can be controlled.

## Steering & Skills

- **Steering:** project-context.md, frontend-rules.md, nas-rules.md
- **Skills:** frontend-design, task-breakdown
- **Reference:** pa3-design Section 5.1 (NAS workflows), Spec Plan Spec 9 Admin UI

#### Acceptance Criteria

1. `frontend/src/api/admin.ts` provides endpoints used by admin pages: getNasQueue, approveFile, rejectFile, getDocuments, reindexDocument, deleteDocument, getFolders, createFolder, deleteFolder.
2. `routes/admin/*` pages are protected by require_admin and show tables with actions and confirmation modals for destructive actions.
3. Approve action triggers API call and shows optimistic UI update; failures rollback and show toast including correlation id.
4. Bulk approve supported in NAS queue UI.

---

### Requirement 7: Graph embed and mini graph component

**User Story:** As an admin or engineer I want to inspect the LightRAG Web UI and see a mini graph on entity pages.

## Steering & Skills

- **Steering:** project-context.md, frontend-rules.md, lightrag-api.md
- **Skills:** frontend-design, task-breakdown
- **Reference:** pa3-design Section 6 (Stack & config), Spec Plan Spec 9 Graph page

#### Acceptance Criteria

1. `routes/graph.tsx` embeds LightRAG Web UI in an iframe with sandbox attributes and shows a placeholder when not available.
2. `RelationGraph.tsx` renders nodes/edges from props; supports node click events and basic tooltips.

---

### Requirement 8: Testing (unit and E2E)

**User Story:** As a QA engineer I want unit tests for api and hooks and Playwright E2E for core flows so regressions are caught early.

## Steering & Skills

- **Steering:** project-context.md, frontend-rules.md, test-conventions.md
- **Skills:** webapp-testing, frontend-design, quality-assurance
- **Reference:** pa3-design Section 15 (E2E & QA checklist), Spec Plan Spec 9 Tests

#### Acceptance Criteria

1. Vitest unit tests cover client.sse parsing, useChat behavior (mocked SSE), and CitationCard rendering.
2. Playwright tests cover: login → chat → stream completes with citation chip; wiki browse → open entity → relations visible; admin approve flow (mocked API) updates UI.
3. Tests run locally with documented commands; CI job added to run unit tests. E2E may be gated behind infra availability.

---

### Requirement 9: Documentation and deliverables

**User Story:** As a product owner I want clear README, demo artifacts, and spec mapping so the team can evaluate the work.

## Steering & Skills

- **Steering:** project-context.md, frontend-rules.md
- **Skills:** task-breakdown
- **Reference:** Spec Plan Spec 9 Deliverables

#### Acceptance Criteria

1. PR includes demo GIF (chat streaming + citation click) and short run instructions.
2. `.kiro/specs/frontend/` contains `requirements.md`, `design.md`, and `tasks.md` updated.
3. All steering references are present at top of `requirements.md` and `tasks.md` files.
