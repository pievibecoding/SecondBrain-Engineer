import { request } from "./client";
import type {
  DiagnosticRequest,
  DiagnosticResponse,
  AdaptiveChunkingReportDetail,
  AdaptiveChunkingReportList,
  AdaptiveChunkingRunRequest,
  ParserComparisonReportDetail,
  ParserComparisonReportList,
  ParserComparisonRunRequest,
  DocumentCompareResponse,
  DocumentItem,
  NasFile,
  NasFolder,
  NasFolderScanResult
} from "../types";

export function getNasQueue(): Promise<NasFile[]> {
  return request<NasFile[]>("/api/admin/nas/queue");
}

export function approveFile(fileId: string): Promise<NasFile> {
  return request<NasFile>(`/api/admin/nas/queue/${encodeURIComponent(fileId)}/action`, {
    method: "POST",
    body: { approve: true }
  });
}

export function rejectFile(fileId: string, rejectReason: string): Promise<NasFile> {
  return request<NasFile>(`/api/admin/nas/queue/${encodeURIComponent(fileId)}/action`, {
    method: "POST",
    body: { approve: false, reject_reason: rejectReason }
  });
}

export function getDocuments(status?: string): Promise<DocumentItem[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return request<DocumentItem[]>(`/api/admin/documents${query}`);
}

export function reindexDocument(fileId: string): Promise<DocumentItem> {
  return request<DocumentItem>(`/api/admin/documents/${encodeURIComponent(fileId)}/reindex`, { method: "POST" });
}

export function deleteDocument(fileId: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/api/admin/documents/${encodeURIComponent(fileId)}`, { method: "DELETE" });
}

export function compareDocument(fileId: string): Promise<DocumentCompareResponse> {
  return request<DocumentCompareResponse>(`/api/admin/documents/${encodeURIComponent(fileId)}/compare`);
}

export function getFolders(): Promise<NasFolder[]> {
  return request<NasFolder[]>("/api/admin/nas/folders");
}

export function createFolder(path: string, folderType: "auto" | "manual", isActive = true): Promise<NasFolder> {
  return request<NasFolder>("/api/admin/nas/folders", {
    method: "POST",
    body: { path, folder_type: folderType, is_active: isActive }
  });
}

export function deleteFolder(folderId: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/api/admin/nas/folders/${encodeURIComponent(folderId)}`, { method: "DELETE" });
}

export function scanFolder(folderId: string): Promise<NasFolderScanResult> {
  return request<NasFolderScanResult>(`/api/admin/nas/folders/${encodeURIComponent(folderId)}/scan`, {
    method: "POST"
  });
}

export function runDiagnostic(payload: DiagnosticRequest): Promise<DiagnosticResponse> {
  return request<DiagnosticResponse>("/api/admin/diagnostics", {
    method: "POST",
    body: { ...payload }
  });
}

export function listAdaptiveChunkingReports(): Promise<AdaptiveChunkingReportList> {
  return request<AdaptiveChunkingReportList>("/api/admin/evaluations/adaptive-chunking");
}

export function getAdaptiveChunkingReport(reportId: string): Promise<AdaptiveChunkingReportDetail> {
  return request<AdaptiveChunkingReportDetail>(`/api/admin/evaluations/adaptive-chunking/${encodeURIComponent(reportId)}`);
}

export function runAdaptiveChunkingEvaluation(payload: AdaptiveChunkingRunRequest): Promise<AdaptiveChunkingReportDetail> {
  return request<AdaptiveChunkingReportDetail>("/api/admin/evaluations/adaptive-chunking/run", {
    method: "POST",
    body: { ...payload }
  });
}

export function listPdfParserComparisonReports(): Promise<ParserComparisonReportList> {
  return request<ParserComparisonReportList>("/api/admin/evaluations/pdf-parser-comparison");
}

export function getPdfParserComparisonReport(reportId: string): Promise<ParserComparisonReportDetail> {
  return request<ParserComparisonReportDetail>(`/api/admin/evaluations/pdf-parser-comparison/${encodeURIComponent(reportId)}`);
}

export function runPdfParserComparison(payload: ParserComparisonRunRequest): Promise<ParserComparisonReportDetail> {
  return request<ParserComparisonReportDetail>("/api/admin/evaluations/pdf-parser-comparison/run", {
    method: "POST",
    body: { ...payload }
  });
}
