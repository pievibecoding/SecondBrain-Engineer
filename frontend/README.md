# SecondBrain Frontend

React + Vite frontend for SecondBrain chat, wiki, admin workflows, and graph inspection.

## Setup

```bash
cd frontend
pnpm install
```

Create `frontend/.env.local` if you need to override defaults:

```ini
VITE_API_BASE=http://localhost:8000
VITE_CORRELATION_ID_ENABLED=true
```

## Commands

```bash
pnpm dev
pnpm build
pnpm test
pnpm test:e2e
```

## Notes

- Frontend data flow is Component → Hook → `src/api/*` → Backend.
- POST SSE streaming is implemented with `fetch` and `ReadableStream` in `src/api/client.ts`.
- All API calls attach `Authorization: Bearer <token>` when available and `X-Correlation-ID` when enabled.
- Session auth is MVP-only and stores the token in `sessionStorage`.

## Accessibility

Key accessibility features implemented:
- `aria-live="polite"` + `aria-busy` on message list — screen readers announce streaming responses
- `aria-label` on all interactive controls (citation cards, cancel button, checkboxes)
- `sr-only` label on chat textarea
- Keyboard navigation: Tab order follows visual flow; citation cards and admin actions are keyboard-operable

Full WCAG 2.1 AA validation requires manual testing with assistive technologies.

## Demo artifacts

See [`docs/demo-artifacts.md`](../docs/demo-artifacts.md) for recording instructions and accessibility checklist.
