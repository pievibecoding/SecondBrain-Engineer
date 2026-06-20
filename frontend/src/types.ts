export interface User {
  id: string;
  username: string;
  email: string;
  role: string;
  created_at?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface CitationItem {
  type: "document" | "graph_entity" | string;
  file?: string | null;
  page?: number | null;
  excerpt?: string | null;
  entity?: string | null;
  relation?: string | null;
  target?: string | null;
  url?: string | null;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | string;
  content: string;
  citations?: CitationItem[] | null;
  graphiti_synced?: boolean;
  created_at?: string;
  streaming?: boolean;
}

export interface EntitySummary {
  name: string;
  type: string;
  description?: string | null;
  score?: number | null;
}

export interface RelationItem {
  src: string;
  rel_type: string;
  tgt: string;
  description?: string | null;
  source?: string | null;
}

export interface SourceDocument {
  file: string;
  nas_path?: string | null;
  url?: string | null;
  page?: number | null;
  excerpt?: string | null;
}

export interface GraphNode {
  id: string;
  label: string;
  type?: string | null;
}

export interface GraphEdge {
  source: string;
  target: string;
  label?: string | null;
}

export interface WikiPage {
  name: string;
  type: string;
  description?: string | null;
  relations: RelationItem[];
  sources: SourceDocument[];
  graph_nodes: GraphNode[];
  graph_edges: GraphEdge[];
}

export interface NasFile {
  id: string;
  nas_path: string;
  folder_type: string;
  status: string;
  file_hash?: string | null;
  lightrag_doc_id?: string | null;
  approved_by?: string | null;
  reject_reason?: string | null;
  created_at: string;
  indexed_at?: string | null;
}

export interface DocumentItem extends NasFile {
  error_msg?: string | null;
  chunk_count?: number | null;
}

export interface DocumentCompareChunk {
  chunk_order_index?: number | null;
  tokens?: number | null;
  content?: string | null;
}

export interface DocumentCompareSection {
  success: boolean;
  parser_used?: string | null;
  char_count: number;
  line_count: number;
  text: string;
}

export interface DocumentCompareChunks {
  count: number;
  char_count: number;
  line_count: number;
  text: string;
  items: DocumentCompareChunk[];
  error?: string | null;
}

export interface DocumentCompareResult {
  similarity_ratio: number;
  first_diff_index?: number | null;
  parsed_window: string;
  chunk_window: string;
  diff_preview: string;
}

export interface DocumentCompareResponse {
  file_id: string;
  nas_path: string;
  status: string;
  folder_type: string;
  lightrag_doc_id?: string | null;
  parsed: DocumentCompareSection;
  chunks: DocumentCompareChunks;
  compare: DocumentCompareResult;
}

export interface DiagnosticRequest {
  query: string;
  file_id?: string | null;
  folder_path?: string | null;
  expected_terms?: string[];
  expected_source_paths?: string[];
}

export interface DiagnosticDiagnosis {
  code: "parse_failed" | "chunk_failed" | "retrieval_failed" | "context_bad" | "llm_bad" | "api_failed" | "ok";
  reason: string;
  next_action: string;
}

export interface DiagnosticResponse {
  correlation_id: string;
  query: string;
  diagnosis: DiagnosticDiagnosis;
  stages: Record<string, unknown>;
  raw_log: Record<string, unknown>;
}

export interface AdaptiveChunkingReportSummary {
  id: string;
  title: string;
  created_at?: string | null;
  recommendation: string;
  document_count: number;
  path: string;
}

export interface AdaptiveChunkingReportList {
  reports: AdaptiveChunkingReportSummary[];
}

export interface AdaptiveChunkingReportDetail {
  id: string;
  title: string;
  created_at?: string | null;
  summary: Record<string, unknown>;
  documents: Array<Record<string, unknown>>;
  markdown?: string | null;
  raw: Record<string, unknown>;
}

export interface AdaptiveChunkingRunDocument {
  document_id?: string | null;
  source_path: string;
}

export interface AdaptiveChunkingRunRequest {
  run_id?: string | null;
  title?: string | null;
  documents: AdaptiveChunkingRunDocument[];
  candidate_terms: Record<string, string[]>;
  expected_terms: string[];
  noise_terms: string[];
  target_chars: number;
  overlap_chars: number;
  max_chars: number;
}

export interface ParserRunDocument {
  document_id?: string | null;
  source_path: string;
}

export interface ParserComparisonRunRequest {
  run_id?: string | null;
  title?: string | null;
  documents: ParserRunDocument[];
  parsers: string[];
  semantic_anchors: string[];
  candidate_terms: Record<string, string[]>;
  expected_terms: string[];
  noise_terms: string[];
  target_chars: number;
  overlap_chars: number;
  max_chars: number;
}

export interface ParserComparisonReportSummary {
  id: string;
  title: string;
  created_at?: string | null;
  recommendation: string;
  recommended_parser?: string | null;
  document_count: number;
  path: string;
}

export interface ParserComparisonReportList {
  reports: ParserComparisonReportSummary[];
}

export interface ParserComparisonReportDetail {
  id: string;
  title: string;
  created_at?: string | null;
  summary: Record<string, unknown>;
  documents: Array<Record<string, unknown>>;
  markdown?: string | null;
  raw: Record<string, unknown>;
}

export interface NasFolder {
  id: string;
  path: string;
  folder_type: "auto" | "manual" | string;
  is_active: boolean;
  last_scanned?: string | null;
  created_at: string;
}

export interface NasFolderScanResult {
  folder: NasFolder;
  scanned_count: number;
  new_count: number;
  updated_count: number;
  deleted_count: number;
  queued_count: number;
  ingested_count: number;
  error_count: number;
  last_scanned: string;
  errors: string[];
}
