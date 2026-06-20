import { useEffect, useState } from "react";
import * as adminApi from "../api/admin";
import { logApiError } from "../api/client";
import type { AdaptiveChunkingReportDetail, AdaptiveChunkingReportSummary, AdaptiveChunkingRunRequest } from "../types";

export function useAdaptiveChunkingEvaluations() {
  const [reports, setReports] = useState<AdaptiveChunkingReportSummary[]>([]);
  const [selectedReport, setSelectedReport] = useState<AdaptiveChunkingReportDetail | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const loadReports = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await adminApi.listAdaptiveChunkingReports();
      setReports(response.reports);
      if (response.reports.length && !selectedId) {
        setSelectedId(response.reports[0].id);
      }
    } catch (nextError) {
      logApiError("listAdaptiveChunkingReports failed", nextError);
      setError(nextError as Error);
    } finally {
      setLoading(false);
    }
  };

  const loadReport = async (reportId: string) => {
    if (!reportId) {
      setSelectedReport(null);
      return;
    }
    setDetailLoading(true);
    setError(null);
    try {
      const response = await adminApi.getAdaptiveChunkingReport(reportId);
      setSelectedReport(response);
    } catch (nextError) {
      logApiError("getAdaptiveChunkingReport failed", nextError, { reportId });
      setError(nextError as Error);
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    void loadReports();
  }, []);

  useEffect(() => {
    void loadReport(selectedId);
  }, [selectedId]);

  const runEvaluation = async (payload: AdaptiveChunkingRunRequest) => {
    setRunning(true);
    setError(null);
    try {
      const response = await adminApi.runAdaptiveChunkingEvaluation(payload);
      setSelectedReport(response);
      setSelectedId(response.id);
      await loadReports();
      return response;
    } catch (nextError) {
      logApiError("runAdaptiveChunkingEvaluation failed", nextError);
      setError(nextError as Error);
      throw nextError;
    } finally {
      setRunning(false);
    }
  };

  return {
    reports,
    selectedReport,
    selectedId,
    setSelectedId,
    loading,
    detailLoading,
    running,
    error,
    runEvaluation,
    refresh: loadReports
  };
}
