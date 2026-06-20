# Frontend — Technical Design (Spec 9)

Overview

This document describes the technical architecture, data flow, component contracts, runtime behaviour and operational considerations for the Frontend (React + Vite) described in Spec 9.

Goals

- Implement Chat (SSE streaming + citations), Wiki (entity pages + mini-graph), Admin (NAS queue, documents, folders) and Graph embed.
- Follow the project's Data Flow convention: Component → Hook → api/ → Backend.
- Forward X-Correlation-ID on every request and surface it in UI error logs.
- Keep the UI minimal and performant for MVP; prioritize correctness and testability.

Architecture

- Tech: React 18+, Vite, TypeScript, shadcn/ui (design primitives), vis.js (or react-force-graph-lite) for mini graph, Playwright for E2E, Vitest for unit tests.
- Directory contract (essential):
  - src/api/* — HTTP adapters only (no React). Exports async functions.
  - src/hooks/* — stateful logic, useContext, caching, SSE lifecycle.
  - src/components/* — presentational, receive data through props from hooks.
  - src/routes/* — pages, consume hooks and compose components.
  - src/contexts/AuthContext.tsx — auth state, token management.

Data flow and lifecycle

- Startup: when app mounts, useAuth generates/reads a correlation id (UUID v4) and sets it in client.ts. For first-time sessions store in sessionStorage and rotate on logout.
- Sending a Chat message:
  1. Component calls useChat.send(message).
  2. useChat opens an EventSource or fetch-based SSE wrapper to POST /api/chat/stream.
  3. client.ts attaches Authorization and X-Correlation-ID headers; server replies with SSE tokens.
  4. useChat appends incoming tokens to an in-memory buffer and writes to state to re-render MessageList progressively.
  5. Final SSE payload (or a final JSON event) includes citations; useChat merges citations into message state and persists the assembled Message to backend DB if applicable.
  6. Background: useChat triggers conversation updates; Graphiti call is done by backend.

SSE Implementation details

- Use a lightweight SSE wrapper that supports POST-based SSE (EventSource doesn't support POST). Implement using fetch with ReadableStream reader and incremental text decode.
- Pattern:
  - fetch(url, { method: 'POST', body: JSON.stringify(payload), headers: {...} });
  - const reader = response.body.getReader(); const decoder = new TextDecoder(); read loop accumulating chunks; parse lines separated by "\n\n" and handle lines that start with "data: ".
  - Emit token events for each `data: <token>` chunk. When `data: [DONE]` is received, resolve/complete with final assembled content.
- Cancelation: expose an AbortController so user can cancel streaming.

API client (client.ts)

- Minimal responsibilities:
  - Base URL from VITE_API_BASE
  - Attach Bearer token when present
  - Attach X-Correlation-ID header on every outgoing request
  - Centralize JSON parsing and response error mapping
  - Expose `setCorrelationId(id?: string)` and `getCorrelationId()` for hooks/tests
  - Export a `ssePost(url, body, {onMessage, onDone, signal})` helper implementing ReadableStream parsing.

Auth

- useAuth must: login(username,password) → store token in memory and optionally in secure httpOnly cookie (server must set cookie) — for MVP we store token in memory + localStorage with an expiry.
- Expose `isAdmin` derived from user.role.
- _protected.tsx uses useAuth.currentUser and redirects if not logged in; AdminLayout enforces isAdmin.

Hooks contracts (summary)

- useChat:
  - API: { messages, send(message), streaming, cancelLast, currentConversationId }
  - Persist messages client-side (session), and optionally reconcile with GET /api/chat/conversations/:id/messages
- useConversation:
  - API: { load(conversationId, page?), messages, hasMore }
- useWikiEntity:
  - API: { data, loading, error, refresh }

Components

- ChatInput: receives onSubmit callback. Does not call any api directly.
- ChatMessage: presentational — shows content and a list of CitationCard components.
- CitationCard: props match backend CitationItem; clicking document opens MinIO URL and clicking graph entity navigates to wiki route.

Mini graph

- Use lightweight library (vis.js provided in pa3-design, or react-force-graph-lite). Input shape: nodes[] {id,label,type}, edges[] {source,target,label}.
- Keep graph rendering isolated in RelationGraph.tsx and accept nodes/edges via props so it can be tested with static fixtures.

Admin flows

- NAS queue: useNasQueue returns actions approve(fileId), reject(fileId, reason). Approve triggers optimistic update then calls /api/admin/nas/approve. On API error, rollback and show toast with correlation id.

Error handling & logging

- UI always surface correlation id in toast when an unexpected error occurs so devs can trace in Seq.
- client.ts should map common 401 → useAuth.logout() trigger and redirect to sign-in.

Performance & accessibility

- Use virtualized message list if messages grow large (react-window) but MVP can skip until needed.
- Streaming tokens should be appended with aria-live="polite" for screen readers.

Environment variables (.env.example keys)

- VITE_API_BASE (e.g. http://localhost:8000)
- VITE_CORRELATION_ID_ENABLED (true|false)

Testing strategy

- Unit tests (Vitest): client.sse parsing, hooks behaviour (mock fetch), CitationCard snapshot.
- Playwright E2E: run against dev backend (or mocked dev server). Tests should assert streaming behaviour ends with citations and citation click works.

CI

- Add frontend workflow to run: install deps, run lint, run unit tests, run Playwright tests (headed or headless in container) in integration stage.

Security

- Do not store tokens in localStorage in plain text for long-lived sessions in production; prefer httpOnly cookies set by backend. Document this as follow-up.

Open questions (implementation notes)

- How backend exposes SSE final citations: final event with JSON or last chunk — implement tolerant parser that accepts both (final JSON event or a `data: [DONE]` then a follow-up JSON fetch).
- MinIO signed URL expiry — backend should return a pre-signed URL. Frontend must open it in new tab.
