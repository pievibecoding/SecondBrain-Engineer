import { useLocation } from "react-router-dom";
import { ChatInput } from "../../components/chat/ChatInput";
import { MessageList } from "../../components/chat/MessageList";
import { useChat } from "../../hooks/useChat";

export function ChatPage() {
  const { messages, send, streaming, cancel, error } = useChat();
  const params = new URLSearchParams(useLocation().search);
  const context = params.get("q") ? `Hỏi AI về ${params.get("q")}` : "";
  return (
    <div className="chat-page">
      <section className="hero card">
        <h1>Robolinks technical memory</h1>
        <p>Ask in Vietnamese or English. Answers stream live and preserve source citations.</p>
      </section>
      {error ? <p className="error">{error.message}</p> : null}
      <MessageList messages={messages} streaming={streaming} />
      <ChatInput onSubmit={send} onCancel={cancel} streaming={streaming} initialValue={context} />
    </div>
  );
}
