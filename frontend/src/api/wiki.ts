import { request } from "./client";
import type { EntitySummary, WikiPage } from "../types";

export function getEntities(type?: string): Promise<EntitySummary[]> {
  const query = type ? `?type=${encodeURIComponent(type)}` : "";
  return request<EntitySummary[]>(`/api/wiki/entities${query}`);
}

export function getEntity(name: string): Promise<WikiPage> {
  return request<WikiPage>(`/api/wiki/entity/${encodeURIComponent(name)}`);
}

export function searchEntities(q: string): Promise<EntitySummary[]> {
  return request<EntitySummary[]>(`/api/wiki/search?q=${encodeURIComponent(q)}`);
}
