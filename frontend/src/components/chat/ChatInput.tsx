import { useState } from "react";

interface ChatInputProps {
  onSubmit: (message: string) => Promise<void> | void;
  onCancel: () => void;
  streaming: boolean;
  initialValue?: string;
}

export function ChatInput({ onSubmit, onCancel, streaming, initialValue = "" }: ChatInputProps) {
  const [value, setValue] = useState(initialValue);

  return (
    <form className="chat-input" onSubmit={(event) => {
      event.preventDefault();
      const message = value.trim();
      if (!message) {
        return;
      }
      setValue("");
      void onSubmit(message);
    }}>
      <label className="sr-only" htmlFor="chat-message">Message</label>
      <textarea
        id="chat-message"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="Ask about a Robolinks project, equipment, SOP, or error code..."
        rows={3}
      />
      <div className="chat-input-actions">
        {streaming ? (
          <button
            type="button"
            className="secondary"
            onClick={onCancel}
            aria-label="Cancel streaming response"
          >
            Cancel
          </button>
        ) : null}
        <button type="submit" disabled={streaming || !value.trim()}>Send</button>
      </div>
    </form>
  );
}
