import { useEffect, useState } from "react";
import * as adminApi from "../api/admin";
import { logApiError } from "../api/client";
import type { ParserComparisonReportDetail, ParserComparisonReportSummary, ParserComparisonRunRequest } from "../types";

export function usePdfParserComparison() {
  const [reports, setReports] = useState<ParserComparisonReportSummary[]>([]);
  const [selectedReport, setSelectedReport] = useState<ParserComparisonReportDetail | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const loadReports = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await adminApi.listPdfParserComparisonReports();
      setReports(response.reports);
      if (response.reports.length && !selectedId) {
        setSelectedId(response.reports[0].id);
      }
    } catch (nextError) {
      logApiError("listPdfParserComparisonReports failed", nextError);
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
      const response = await adminApi.getPdfParserComparisonReport(reportId);
      setSelectedReport(response);
    } catch (nextError) {
      logApiError("getPdfParserComparisonReport failed", nextError, { reportId });
      setError(nextError as Error);
    } finally {
      setDetailLoading(false);
    }
  };

  const runComparison = async (payload: ParserComparisonRunRequest) => {
    setRunning(true);
    setError(null);
    try {
      const response = await adminApi.runPdfParserComparison(payload);
      setSelectedReport(response);
      setSelectedId(response.id);
      await loadReports();
      return response;
    } catch (nextError) {
      logApiError("runPdfParserComparison failed", nextError);
      setError(nextError as Error);
      throw nextError;
    } finally {
      setRunning(false);
    }
  };

  useEffect(() => {
    void loadReports();
  }, []);

  useEffect(() => {
    void loadReport(selectedId);
  }, [selectedId]);

  return {
    reports,
    selectedReport,
    selectedId,
    setSelectedId,
    loading,
    detailLoading,
    running,
    error,
    runComparison,
    refresh: loadReports
  };
}
