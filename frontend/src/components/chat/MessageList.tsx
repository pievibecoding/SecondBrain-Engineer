import type { ChatMessage } from "../../types";
import { ChatMessage as ChatMessageView } from "./ChatMessage";

export function MessageList({ messages, streaming = false }: { messages: ChatMessage[]; streaming?: boolean }) {
  return (
    <section
      className="message-list"
      aria-live="polite"
      aria-label="Chat messages"
      aria-busy={streaming}
    >
      {messages.length === 0 ? <div className="empty-state">Ask a question to start a technical memory search.</div> : null}
      {messages.map((message) => <ChatMessageView key={message.id} message={message} />)}
    </section>
  );
}
