import type { ChatMessage as ChatMessageType } from "../../types";
import { CitationCard } from "./CitationCard";

export function ChatMessage({ message }: { message: ChatMessageType }) {
  return (
    <article className={`message ${message.role === "user" ? "message-user" : "message-assistant"}`}>
      <div className="message-role">{message.role === "user" ? "You" : "SecondBrain"}</div>
      <p>{message.content || (message.streaming ? <span role="status" aria-label="Generating response">Thinking...</span> : "")}</p>
      {message.citations?.length ? (
        <div className="citations" aria-label="Citations">
          {message.citations.map((citation, index) => <CitationCard citation={citation} key={`${citation.file || citation.entity || index}-${index}`} />)}
        </div>
      ) : null}
    </article>
  );
}
