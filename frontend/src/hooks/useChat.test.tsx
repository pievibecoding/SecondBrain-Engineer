import { renderHook, act } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useChat } from "./useChat";

vi.mock("../api/chat", () => ({
  streamChat: async (_conversationId: string | null, _message: string, callbacks: any) => {
    callbacks.onToken("Motor ");
    callbacks.onToken("Siemens");
    callbacks.onCitations([{ type: "document", file: "BOM.xlsx" }]);
    callbacks.onDone();
  },
  getChatHistory: async () => []
}));

describe("useChat", () => {
  it("assembles streaming response and citations", async () => {
    const { result } = renderHook(() => useChat());
    await act(async () => {
      await result.current.send("Dùng motor gì?");
    });
    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[1].content).toBe("Motor Siemens");
    expect(result.current.messages[1].citations?.[0].file).toBe("BOM.xlsx");
    expect(result.current.streaming).toBe(false);
  });
});
