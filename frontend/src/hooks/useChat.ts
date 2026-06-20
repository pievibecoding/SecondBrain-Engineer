import { useCallback, useRef, useState } from "react";
import * as chatApi from "../api/chat";
import type { ChatMessage, CitationItem } from "../types";

const CONVERSATION_KEY = "secondbrain.current_conversation_id";

function makeId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function useChat(initialConversationId?: string | null) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(() => initialConversationId || sessionStorage.getItem(CONVERSATION_KEY));
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(async (message: string) => {
    const trimmed = message.trim();
    if (!trimmed || streaming) {
      return;
    }
    const userMessage: ChatMessage = {
      id: makeId("user"),
      conversation_id: currentConversationId || "pending",
      role: "user",
      content: trimmed,
      citations: []
    };
    const assistantId = makeId("assistant");
    const assistantMessage: ChatMessage = {
      id: assistantId,
      conversation_id: currentConversationId || "pending",
      role: "assistant",
      content: "",
      citations: [],
      streaming: true
    };
    const controller = new AbortController();
    abortRef.current = controller;
    setError(null);
    setStreaming(true);
    setMessages((prev) => [...prev, userMessage, assistantMessage]);

    let citations: CitationItem[] = [];
    try {
      await chatApi.streamChat(currentConversationId, trimmed, {
        signal: controller.signal,
        onToken(token) {
          setMessages((prev) => prev.map((item) => item.id === assistantId ? { ...item, content: item.content + token } : item));
        },
        onCitations(next) {
          citations = next;
          setMessages((prev) => prev.map((item) => item.id === assistantId ? { ...item, citations: next } : item));
        },
        onDone() {
          setMessages((prev) => prev.map((item) => item.id === assistantId ? { ...item, citations, streaming: false } : item));
        },
        onError(nextError) {
          setError(nextError);
        }
      });
    } catch (nextError) {
      if ((nextError as Error).name !== "AbortError") {
        setError(nextError as Error);
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
      if (currentConversationId) {
        sessionStorage.setItem(CONVERSATION_KEY, currentConversationId);
      }
      setMessages((prev) => prev.map((item) => item.id === assistantId ? { ...item, streaming: false } : item));
    }
  }, [currentConversationId, streaming]);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    setStreaming(false);
  }, []);

  const loadHistory = useCallback(async (conversationId: string) => {
    const history = await chatApi.getChatHistory(conversationId);
    setCurrentConversationId(conversationId);
    sessionStorage.setItem(CONVERSATION_KEY, conversationId);
    setMessages(history);
  }, []);

  return { messages, send, streaming, cancel, currentConversationId, setCurrentConversationId, loadHistory, error };
}
