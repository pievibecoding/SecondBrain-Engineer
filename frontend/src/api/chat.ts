import { request, ssePost } from "./client";
import type { ChatMessage, CitationItem } from "../types";

interface StreamCallbacks {
  onToken: (token: string) => void;
  onCitations?: (citations: CitationItem[]) => void;
  onDone?: () => void;
  onError?: (error: Error) => void;
  signal?: AbortSignal;
}

export function streamChat(conversationId: string | null, message: string, callbacks: StreamCallbacks): Promise<void> {
  return ssePost("/api/chat/stream", { conversation_id: conversationId, message }, {
    signal: callbacks.signal,
    onMessage(data) {
      const parsed = parseMaybeJson(data);
      if (parsed && typeof parsed === "object" && Array.isArray(parsed.citations)) {
        callbacks.onCitations?.(parsed.citations);
        return;
      }
      callbacks.onToken(data);
    },
    onDone() {
      callbacks.onDone?.();
    },
    onError: callbacks.onError
  });
}

export function getChatHistory(conversationId: string): Promise<ChatMessage[]> {
  return request<ChatMessage[]>(`/api/chat/conversations/${encodeURIComponent(conversationId)}/messages`);
}

function parseMaybeJson(data: string): any {
  try {
    return JSON.parse(data);
  } catch {
    return null;
  }
}
