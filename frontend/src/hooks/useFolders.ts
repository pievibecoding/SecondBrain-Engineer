import { useCallback, useEffect, useState } from "react";
import * as adminApi from "../api/admin";
import { logApiError } from "../api/client";
import type { NasFolder, NasFolderScanResult } from "../types";

export function useFolders() {
  const [folders, setFolders] = useState<NasFolder[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [scanResult, setScanResult] = useState<NasFolderScanResult | null>(null);
  const [scanningFolderId, setScanningFolderId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setFolders(await adminApi.getFolders());
    } catch (nextError) {
      setError(nextError as Error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const create = async (path: string, folderType: "auto" | "manual") => {
    try {
      const folder = await adminApi.createFolder(path, folderType);
      setFolders((items) => [...items, folder]);
    } catch (error) {
      logApiError("createFolder failed", error, { path, folderType });
      throw error;
    }
  };

  const remove = async (folderId: string) => {
    if (!window.confirm("Delete this NAS folder configuration?")) {
      return;
    }
    try {
      await adminApi.deleteFolder(folderId);
      setFolders((items) => items.filter((item) => item.id !== folderId));
    } catch (error) {
      logApiError("deleteFolder failed", error, { folderId });
      throw error;
    }
  };

  const scan = async (folderId: string) => {
    setScanningFolderId(folderId);
    setError(null);
    try {
      const result = await adminApi.scanFolder(folderId);
      setScanResult(result);
      setFolders((items) => items.map((item) => item.id === folderId ? result.folder : item));
      return result;
    } catch (nextError) {
      logApiError("scanFolder failed", nextError, { folderId });
      setError(nextError as Error);
      throw nextError;
    } finally {
      setScanningFolderId(null);
    }
  };

  return { folders, loading, error, refresh, create, remove, scan, scanResult, scanningFolderId };
}
