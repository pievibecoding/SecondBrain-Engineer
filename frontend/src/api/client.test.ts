import { beforeEach, describe, expect, it, vi } from "vitest";
import { getCorrelationId, request, setCorrelationId, setToken, ssePost } from "./client";

describe("api client", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it("propagates auth and correlation headers", async () => {
    setToken("abc");
    setCorrelationId("cid-1");
    vi.stubGlobal("fetch", vi.fn(async (_url, init) => {
      const headers = init?.headers as Headers;
      expect(headers.get("Authorization")).toBe("Bearer abc");
      expect(headers.get("X-Correlation-ID")).toBe("cid-1");
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    }));

    await expect(request<{ ok: boolean }>("/api/test")).resolves.toEqual({ ok: true });
    expect(getCorrelationId()).toBe("cid-1");
  });

  it("parses SSE chunks", async () => {
    const encoder = new TextEncoder();
    vi.stubGlobal("fetch", vi.fn(async () => new Response(new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode("data: Hel"));
        controller.enqueue(encoder.encode("lo\n\ndata: [DONE]\n\n"));
        controller.close();
      }
    }), { status: 200 })));

    const tokens: string[] = [];
    let done = false;
    await ssePost("/api/chat/stream", { message: "Hi" }, {
      onMessage: (token) => tokens.push(token),
      onDone: () => { done = true; }
    });

    expect(tokens).toEqual(["Hello"]);
    expect(done).toBe(true);
  });
});
