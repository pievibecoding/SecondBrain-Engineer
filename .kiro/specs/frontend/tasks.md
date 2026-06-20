# Implementation Plan — Spec 9: Frontend

Implement frontend features for Chat, Wiki, Admin and Graph embed. Prioritise core Chat streaming and citation behaviour for MVP demo.

---

## Tasks

- [x] 1. Project scaffolding and README
  - Add `frontend/README.md` with run/test instructions
  - Add `.env.example` entries: `VITE_API_BASE`, `VITE_CORRELATION_ID_ENABLED`
  - Add npm scripts: `dev`, `build`, `preview`, `test`, `test:e2e`
  - Est: 4h — Owner: FE

- [x] 2. Implement `src/api/client.ts`
  - Base client, auth header, X-Correlation-ID helpers, `ssePost` implementation
  - Unit tests mocking fetch streaming responses
  - Est: 8h — Owner: FE

- [x] 3. Auth context and `useAuth` hook
  - AuthContext, login/logout, token persistence, isAdmin
  - `_protected.tsx` redirect behavior
  - Est: 8h — Owner: FE

- [x] 4. Chat API (`src/api/chat.ts`) and `useChat` hook
  - Streaming wrapper, AbortController, messages state and assembly
  - Unit tests for streaming assembly and citations parsing
  - Est: 14h — Owner: FE

- [x] 5. Chat UI components and page
  - ChatInput, MessageList, ChatMessage, CitationCard, routes/chat/index.tsx
  - Accessibility: aria-live for streaming
  - Est: 12h — Owner: FE

- [x] 6. Wiki API, hooks and pages
  - `src/api/wiki.ts`, `useWikiCategories`, `useWikiEntity`, `routes/wiki/*`
  - RelationGraph component using vis.js or react-force-graph-lite
  - Est: 12h — Owner: FE

- [x] 7. Admin API, hooks and pages
  - `src/api/admin.ts`, `useNasQueue`, `useDocuments`, `useFolders`, `routes/admin/*`
  - Bulk approve, confirmation modals, optimistic UI
  - Est: 12h — Owner: FE

- [x] 8. Graph embed (`routes/graph.tsx`) and placeholder
  - iframe embed with sandbox attributes and messaging docs
  - Est: 3h — Owner: FE

- [x] 9. Mini graph component (`RelationGraph.tsx`)
  - Render nodes/edges, basic pan/zoom and tooltips
  - Unit test with fixture
  - Est: 6h — Owner: FE

- [x] 10. Tests: Unit + Playwright E2E
  - Vitest unit tests for client, hooks, key components
  - Playwright tests for login→chat→citation, wiki browse→entity, admin approve (mocked)
  - Est: 12h — Owner: FE + QA

- [x] 11. Polish, accessibility and demo artifacts
  - Accessibility checks, demo GIFs for PR, update docs
  - Est: 6h — Owner: FE

---

Estimated total: 97 hours. Prioritise tasks 1–5 for MVP demo (chat streaming, citations, auth). Keep tasks small and create PRs per feature group.
