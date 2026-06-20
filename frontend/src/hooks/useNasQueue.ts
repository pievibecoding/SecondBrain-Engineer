import { useCallback, useEffect, useState } from "react";
import * as adminApi from "../api/admin";
import { getCorrelationId, logApiError } from "../api/client";
import type { NasFile } from "../types";

export function useNasQueue() {
  const [files, setFiles] = useState<NasFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setFiles(await adminApi.getNasQueue());
    } catch (nextError) {
      setError(nextError as Error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const approve = async (fileId: string) => {
    const previous = files;
    setFiles((items) => items.filter((item) => item.id !== fileId));
    try {
      await adminApi.approveFile(fileId);
    } catch (nextError) {
      logApiError("approveFile failed", nextError, { fileId });
      setFiles(previous);
      setError(new Error(`${(nextError as Error).message} (correlation id: ${getCorrelationId()})`));
    }
  };

  const reject = async (fileId: string, reason: string) => {
    const previous = files;
    setFiles((items) => items.filter((item) => item.id !== fileId));
    try {
      await adminApi.rejectFile(fileId, reason);
    } catch (nextError) {
      logApiError("rejectFile failed", nextError, { fileId, reason });
      setFiles(previous);
      setError(new Error(`${(nextError as Error).message} (correlation id: ${getCorrelationId()})`));
    }
  };

  const bulkApprove = async (fileIds: string[]) => {
    for (const fileId of fileIds) {
      await approve(fileId);
    }
  };

  return { files, loading, error, refresh, approve, reject, bulkApprove };
}
