type Json = Record<string, unknown> | unknown[] | string | number | boolean | null;

export type RequestOptions = Omit<RequestInit, "body"> & {
  body?: BodyInit | Json;
  skipAuth?: boolean;
};

export interface SsePostCallbacks<TDone = unknown> {
  onMessage?: (data: string, event?: string) => void;
  onDone?: (data?: TDone) => void;
  onError?: (error: Error) => void;
  signal?: AbortSignal;
}

const TOKEN_KEY = "secondbrain.token";
const CORRELATION_KEY = "secondbrain.correlation_id";

export const baseUrl = (import.meta.env.VITE_API_BASE || "http://localhost:8000").replace(/\/$/, "");

function correlationEnabled(): boolean {
  return import.meta.env.VITE_CORRELATION_ID_ENABLED !== "false";
}

function generateCorrelationId(): string {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }
  return `cid-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) {
    sessionStorage.setItem(TOKEN_KEY, token);
  } else {
    sessionStorage.removeItem(TOKEN_KEY);
  }
}

export function getCorrelationId(): string {
  if (!correlationEnabled()) {
    return "";
  }
  const existing = sessionStorage.getItem(CORRELATION_KEY);
  if (existing) {
    return existing;
  }
  const next = generateCorrelationId();
  sessionStorage.setItem(CORRELATION_KEY, next);
  return next;
}

export function setCorrelationId(id?: string): string {
  const next = id || generateCorrelationId();
  sessionStorage.setItem(CORRELATION_KEY, next);
  return next;
}

export function clearCorrelationId(): void {
  sessionStorage.removeItem(CORRELATION_KEY);
}

function toUrl(path: string): string {
  if (/^https?:\/\//.test(path)) {
    return path;
  }
  return `${baseUrl}${path.startsWith("/") ? path : `/${path}`}`;
}

function buildHeaders(init?: HeadersInit, skipAuth?: boolean): Headers {
  const headers = new Headers(init);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (!skipAuth) {
    const token = getToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }
  const correlationId = getCorrelationId();
  if (correlationId) {
    headers.set("X-Correlation-ID", correlationId);
  }
  return headers;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: unknown,
    public correlationId: string = getCorrelationId()
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function logApiError(context: string, error: unknown, extra: Record<string, unknown> = {}): void {
  if (error instanceof ApiError) {
    console.error(`[API] ${context}`, {
      status: error.status,
      detail: error.detail,
      correlationId: error.correlationId,
      message: error.message,
      ...extra
    });
    return;
  }
  if (error instanceof Error) {
    console.error(`[API] ${context}`, {
      name: error.name,
      message: error.message,
      ...extra
    });
    return;
  }
  console.error(`[API] ${context}`, {
    error,
    ...extra
  });
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { skipAuth, headers, body, ...rest } = options;
  const response = await fetch(toUrl(path), {
    ...rest,
    headers: buildHeaders(headers, skipAuth),
    body: typeof body === "string" || body instanceof FormData ? body : body ? JSON.stringify(body) : undefined
  });

  const text = await response.text();
  const data = text ? safeJson(text) : null;

  if (!response.ok) {
    const detail = data && typeof data === "object" && "detail" in data ? data.detail : data;
    throw new ApiError(`Request failed with status ${response.status}`, response.status, detail);
  }

  return data as T;
}

export async function ssePost<TDone = unknown>(path: string, body: Json, callbacks: SsePostCallbacks<TDone> = {}): Promise<void> {
  const response = await fetch(toUrl(path), {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify(body),
    signal: callbacks.signal
  });

  if (!response.ok) {
    throw new ApiError(`SSE request failed with status ${response.status}`, response.status, await response.text());
  }
  if (!response.body) {
    throw new ApiError("SSE response did not include a readable body", response.status);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const flushEvent = (rawEvent: string): void => {
    const lines = rawEvent.split(/\r?\n/);
    let event = "message";
    const dataLines: string[] = [];
    for (const line of lines) {
      if (line.startsWith("event:")) {
        event = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trimStart());
      }
    }
    if (dataLines.length === 0) {
      return;
    }
    const data = dataLines.join("\n");
    if (data === "[DONE]") {
      callbacks.onDone?.();
      return;
    }
    if (event === "error") {
      const error = new Error(data);
      callbacks.onError?.(error);
      return;
    }
    const parsed = safeJson(data);
    if (parsed && typeof parsed === "object" && "done" in parsed) {
      callbacks.onDone?.(parsed as TDone);
      return;
    }
    callbacks.onMessage?.(data, event);
  };

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split(/\r?\n\r?\n/);
      buffer = events.pop() || "";
      for (const rawEvent of events) {
        flushEvent(rawEvent);
      }
    }
    buffer += decoder.decode();
    if (buffer.trim()) {
      flushEvent(buffer);
    }
  } catch (error) {
    if ((error as Error).name === "AbortError") {
      throw error;
    }
    callbacks.onError?.(error as Error);
    throw error;
  }
}

function safeJson(text: string): any {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}
