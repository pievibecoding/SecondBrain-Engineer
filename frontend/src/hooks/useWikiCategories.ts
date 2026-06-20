import { useEffect, useState } from "react";
import * as wikiApi from "../api/wiki";
import type { EntitySummary } from "../types";

const TYPES = ["PROJECT", "CLIENT", "EQUIPMENT", "COMPONENT", "SUPPLIER", "PERSON", "PROCESS", "ERROR_CODE", "DOCUMENT", "LOCATION", "STANDARD"];

export function useWikiCategories() {
  const [categories, setCategories] = useState<{ type: string; count: number }[]>(TYPES.map((type) => ({ type, count: 0 })));
  const [entities, setEntities] = useState<EntitySummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    setLoading(true);
    wikiApi.getEntities()
      .then((items) => {
        setEntities(items);
        const counts = new Map<string, number>();
        for (const item of items) {
          counts.set(item.type, (counts.get(item.type) || 0) + 1);
        }
        setCategories(TYPES.map((type) => ({ type, count: counts.get(type) || 0 })));
      })
      .catch(setError)
      .finally(() => setLoading(false));
  }, []);

  return { categories, entities, loading, error };
}
