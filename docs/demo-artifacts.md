# SecondBrain — Demo Artifacts

> Sprint demo guide for Spec 9 (Frontend) sign-off.
> Demo GIFs are generated after the first running deployment — see instructions below.

---

## How to record demo GIFs

### Prerequisites
1. Stack running: `docker compose up -d`
2. Frontend dev server: `cd frontend && pnpm dev`
3. At least 3 documents indexed via NAS or manual upload

### Recordings needed

| # | Flow | Tool | Output file |
|---|---|---|---|
| 1 | Chat streaming + citation click | LICEcap / Kap / peek | `docs/demo-chat-streaming.gif` |
| 2 | Wiki browse → entity page → mini graph | LICEcap / Kap | `docs/demo-wiki-entity.gif` |
| 3 | Admin NAS queue approve → document indexed | LICEcap / Kap | `docs/demo-admin-approve.gif` |

### Steps for GIF 1 — Chat streaming + citation
1. Open `http://localhost:3000/chat`
2. Type: `Dự án Heineken dùng motor gì?`
3. Click **Send** — show tokens streaming in real time
4. When complete, click a **citation chip** — show wiki page opens
5. Stop recording

### Steps for GIF 2 — Wiki entity
1. Open `http://localhost:3000/wiki`
2. Search `Heineken`
3. Click entity card — show entity page with description, relations, mini graph
4. Click **Hỏi AI về Heineken** — show chat pre-filled
5. Stop recording

### Steps for GIF 3 — Admin approve
1. Open `http://localhost:3000/admin/queue`
2. Select one or more files with checkboxes
3. Click **Bulk approve** — show optimistic removal from list
4. Navigate to `/admin/documents` — show document appears with status `indexed`
5. Stop recording

---

## Accessibility checklist (manual verification)

Run these checks with keyboard-only navigation before demo:

- [ ] **Chat input**: Tab to textarea → type message → Tab to Send → Enter submits
- [ ] **Cancel button**: visible and focusable during streaming; Escape key cancels
- [ ] **Citation cards**: focusable by Tab; Enter/Space activates navigation
- [ ] **MessageList**: screen reader announces new assistant message (aria-live=polite)
- [ ] **Admin table**: checkbox column has aria-label per file; approve/reject buttons labeled
- [ ] **Wiki search**: search input labeled; results list navigable by keyboard
- [ ] **_protected redirect**: unauthenticated users redirected before page content renders

Run with VoiceOver (macOS) or NVDA (Windows) to verify aria-live announcements work correctly
during streaming. Note: full WCAG 2.1 AA audit requires expert review and assistive technology
testing beyond this checklist.

---

## Run instructions (PR)

```bash
cd frontend
pnpm install
pnpm dev        # → http://localhost:3000
pnpm test       # vitest unit tests
pnpm test:e2e   # playwright (requires running dev server)
```

## Spec mapping

| Spec | Path |
|---|---|
| Requirements | `.kiro/specs/frontend/requirements.md` |
| Design | `.kiro/specs/frontend/design.md` |
| Tasks | `.kiro/specs/frontend/tasks.md` |
