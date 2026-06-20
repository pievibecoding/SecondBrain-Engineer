import { useState } from "react";
import * as wikiApi from "../api/wiki";
import type { EntitySummary } from "../types";

const cache = new Map<string, EntitySummary[]>();

export function useWikiSearch() {
  const [results, setResults] = useState<EntitySummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const search = async (q: string) => {
    const trimmed = q.trim();
    if (!trimmed) {
      setResults([]);
      return;
    }
    if (cache.has(trimmed)) {
      setResults(cache.get(trimmed)!);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const items = await wikiApi.searchEntities(trimmed);
      cache.set(trimmed, items);
      setResults(items);
    } catch (nextError) {
      setError(nextError as Error);
    } finally {
      setLoading(false);
    }
  };

  return { results, loading, error, search };
}
