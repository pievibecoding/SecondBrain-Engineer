import { useCallback, useEffect, useState } from "react";
import * as adminApi from "../api/admin";
import { logApiError } from "../api/client";
import type { DocumentCompareResponse, DocumentItem } from "../types";

export function useDocuments(status?: string) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [compareReport, setCompareReport] = useState<DocumentCompareResponse | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setDocuments(await adminApi.getDocuments(status));
    } catch (nextError) {
      setError(nextError as Error);
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const reindex = async (fileId: string) => {
    try {
      const updated = await adminApi.reindexDocument(fileId);
      setDocuments((items) => items.map((item) => item.id === fileId ? updated : item));
      if (updated.status === "failed" || updated.error_msg) {
        logApiError("reindexDocument completed with failed status", new Error(updated.error_msg || "Document reindex failed"), {
          fileId,
          documentStatus: updated.status,
          nasPath: updated.nas_path,
        });
        setError(new Error(updated.error_msg || "Document reindex failed."));
      } else {
        setError(null);
      }
    } catch (error) {
      logApiError("reindexDocument failed", error, { fileId });
      setError(error as Error);
      throw error;
    }
  };

  const remove = async (fileId: string) => {
    if (!window.confirm("Delete this document from the index?")) {
      return;
    }
    try {
      await adminApi.deleteDocument(fileId);
      setDocuments((items) => items.filter((item) => item.id !== fileId));
    } catch (error) {
      logApiError("deleteDocument failed", error, { fileId });
      throw error;
    }
  };

  const removeAll = async () => {
    if (!documents.length) {
      return;
    }
    if (!window.confirm(`Delete all ${documents.length} documents from the index?`)) {
      return;
    }

    let failedCount = 0;
    const remainingDocuments: DocumentItem[] = [];
    for (const document of documents) {
      try {
        await adminApi.deleteDocument(document.id);
      } catch (error) {
        logApiError("deleteDocument failed during removeAll", error, { fileId: document.id, nasPath: document.nas_path });
        failedCount += 1;
        remainingDocuments.push(document);
      }
    }

    if (failedCount > 0) {
      setDocuments(remainingDocuments);
      setError(new Error(`Deleted with ${failedCount} failure(s).`));
      return;
    }

    setDocuments([]);
  };

  const compare = async (fileId: string) => {
    try {
      const report = await adminApi.compareDocument(fileId);
      setCompareReport(report);
      setError(null);
      return report;
    } catch (nextError) {
      logApiError("compareDocument failed", nextError, { fileId });
      setError(nextError as Error);
      throw nextError;
    }
  };

  return { documents, loading, error, compareReport, refresh, reindex, remove, removeAll, compare };
}
