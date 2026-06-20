---
inclusion: fileMatch
fileMatchPattern: '*.tsx,*.jsx,*.ts,frontend/**'
---

# Frontend Rules — SecondBrain

> Load khi làm việc với frontend/ files.

---

## Data Flow Convention (BẮTBUỘC — không có ngoại lệ)

```
Component → Hook → api/ → Backend
```

### Rules
- **Component KHÔNG import từ `api/` trực tiếp**
- **Component KHÔNG gọi `fetch()` hay `axios` trực tiếp**
- **Hook** chịu trách nhiệm: state, loading, error, retry
- **`api/`** chỉ export async functions — KHÔNG có `useState`/`useEffect`
- **Route page** dùng hooks, pass data xuống components qua props

### Ví dụ ĐÚNG
```typescript
// hooks/useWikiEntity.ts
export function useWikiEntity(name: string) {
    const [data, setData] = useState<EntityResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        setLoading(true);
        wikiApi.getEntity(name)
            .then(setData)
            .catch(setError)
            .finally(() => setLoading(false));
    }, [name]);

    return { data, loading, error };
}

// components/wiki/WikiEntityCard.tsx
// NHẬN data qua props — KHÔNG tự fetch
interface WikiEntityCardProps {
    entity: EntityResponse;
    onNavigate: (name: string) => void;
}
export function WikiEntityCard({ entity, onNavigate }: WikiEntityCardProps) { ... }

// routes/wiki/[name].tsx
export function WikiEntityPage() {
    const { name } = useParams();
    const { data, loading, error } = useWikiEntity(name);  // OK — hook
    return <WikiEntityCard entity={data} onNavigate={...} />;
}
```

### Ví dụ SAI
```typescript
// SAI — component gọi api/ trực tiếp
import { getEntity } from '@/api/wiki';  // KHÔNG
export function WikiEntityCard({ name }) {
    const [data] = useState(() => getEntity(name));  // KHÔNG
}
```

---

## Hook Naming Convention

```
use[Domain][Action].ts

useChat.ts           ← SSE streaming, send message
useConversation.ts   ← load history, pagination
useWikiEntity.ts     ← fetch 1 entity + relations + sources
useWikiCategories.ts ← list entity types + counts
useWikiSearch.ts     ← search entity by name
useNasQueue.ts       ← pending files, approve, reject
useDocuments.ts      ← indexed docs, reindex, delete
useFolders.ts        ← NAS folder CRUD
useAuth.ts           ← wrap AuthContext
```

Hook return shape:
```typescript
return { data, loading, error, ...actions }
// Ví dụ: { files, loading, error, approve, reject }
```

---

## SSE Streaming (Chat UI)

```typescript
// hooks/useChat.ts — dùng EventSource cho SSE
const streamChat = (message: string, onToken: (token: string) => void) => {
    const es = new EventSource(
        `/api/chat/stream?message=${encodeURIComponent(message)}`
    );
    es.onmessage = (e) => {
        if (e.data === '[DONE]') { es.close(); return; }
        onToken(e.data);
    };
    es.onerror = () => es.close();
};
```

---

## Auth Guard

- `routes/_protected.tsx` wrap tất cả authenticated routes
- Admin routes cần thêm `require_admin` check
- `AuthContext.tsx` là single source of truth cho auth state
- Dùng `useAuth()` hook, KHÔNG access AuthContext trực tiếp

---

## Component Props Pattern

```typescript
// Props rõ ràng, không pass callback chưa cần thiết
interface NasFileQueueProps {
    files: NasFileResponse[];
    onApprove: (fileId: string) => Promise<void>;
    onReject: (fileId: string, reason: string) => Promise<void>;
    isLoading?: boolean;
}
```

---

## Styling

- Dùng **shadcn/ui** components làm base
- Tailwind utility classes
- Không dùng inline styles trừ khi cần dynamic values
- Responsive: mobile-first
