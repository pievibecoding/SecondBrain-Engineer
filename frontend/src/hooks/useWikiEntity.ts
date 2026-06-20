import { useCallback, useEffect, useState } from "react";
import * as wikiApi from "../api/wiki";
import type { WikiPage } from "../types";

const cache = new Map<string, WikiPage>();

export function useWikiEntity(name: string | undefined) {
  const [data, setData] = useState<WikiPage | null>(name && cache.has(name) ? cache.get(name)! : null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(async () => {
    if (!name) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const page = await wikiApi.getEntity(name);
      cache.set(name, page);
      setData(page);
    } catch (nextError) {
      setError(nextError as Error);
    } finally {
      setLoading(false);
    }
  }, [name]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { data, loading, error, refresh };
}
