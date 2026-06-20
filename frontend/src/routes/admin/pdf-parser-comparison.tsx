import { FormEvent, useMemo, useState } from "react";
import { usePdfParserComparison } from "../../hooks/usePdfParserComparison";
import type { ParserComparisonRunRequest } from "../../types";

const tabs = ["summary", "parsed", "tables", "metrics", "matrix", "raw"] as const;
type Tab = typeof tabs[number];

const defaultSources = "ball-screw | /local-nas/DATN_TLTK/7. Ball Screws Selection Guide.pdf";
const defaultAnchors = [
  "Ball Screw Selection Procedure",
  "Selection of Ball Screw Shaft Length",
  "Ball Screw Lead Accuracy",
  "Allowable Rotational Speed",
  "Axial Load Capacity",
  "Basic Dynamic Load Rating",
  "Service Life",
  "Support Units"
].join("\n");
const defaultCandidates = [
  "Lead: lead, screw lead, ball screw lead",
  "Diameter: shaft diameter, screw shaft diameter",
  "Accuracy: lead accuracy, accuracy grade, positioning accuracy",
  "Load: axial load, dynamic load rating, static load rating",
  "Speed: allowable rotational speed, critical speed, rotational speed",
  "Life: service life, life calculation, fatigue life",
  "Support: support unit, fixed side, support side",
  "Nut: ball nut, nut bracket, standard nut"
].join("\n");
const defaultExpectedTerms = [
  "application parameters",
  "shaft diameter",
  "lead accuracy grade",
  "axial load capacity",
  "allowable rotational speed",
  "basic dynamic load rating",
  "static safety factor",
  "service life",
  "support unit",
  "positioning accuracy"
].join("\n");
const defaultNoiseTerms = [
  "copyright",
  "contact",
  "company profile",
  "CC__",
  "ccEENNGG",
  "FF1100"
].join("\n");

function asString(value: unknown, fallback = "-"): string {
  return typeof value === "string" && value ? value : fallback;
}

function asNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function formatJson(value: unknown): string {
  return JSON.stringify(value ?? null, null, 2);
}

async function copyText(value: string): Promise<void> {
  await navigator.clipboard.writeText(value);
}

function splitTerms(value: string): string[] {
  return value.split(/\r?\n|,/).map((item) => item.trim()).filter(Boolean);
}

function parseSources(value: string) {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const [maybeId, ...pathParts] = line.split("|");
      const sourcePath = pathParts.length ? pathParts.join("|").trim() : maybeId.trim();
      const documentId = pathParts.length ? maybeId.trim() : `document-${index + 1}`;
      return { document_id: documentId || `document-${index + 1}`, source_path: sourcePath };
    });
}

function parseCandidates(value: string): Record<string, string[]> {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .reduce<Record<string, string[]>>((acc, line) => {
      const [name, ...aliasParts] = line.split(":");
      const key = name.trim();
      const aliases = aliasParts.join(":").split(",").map((item) => item.trim()).filter(Boolean);
      if (key && aliases.length) acc[key] = aliases;
      return acc;
    }, {});
}

function getParserResults(document: Record<string, unknown>): Array<Record<string, unknown>> {
  return Array.isArray(document.parser_results) ? document.parser_results as Array<Record<string, unknown>> : [];
}

function getMetrics(result: Record<string, unknown>): Record<string, any> {
  return result.metrics && typeof result.metrics === "object" ? result.metrics as Record<string, any> : {};
}

function getTermMetrics(result: Record<string, unknown>): Record<string, any> {
  return result.term_metrics && typeof result.term_metrics === "object" ? result.term_metrics as Record<string, any> : {};
}

function getTables(result: Record<string, unknown>): Array<Record<string, unknown>> {
  return Array.isArray(result.tables) ? result.tables as Array<Record<string, unknown>> : [];
}

function getMatrix(result: Record<string, unknown>): Array<Record<string, unknown>> {
  return Array.isArray(result.chunk_matrix) ? result.chunk_matrix as Array<Record<string, unknown>> : [];
}

export function AdminPdfParserComparisonPage() {
  const { reports, selectedReport, selectedId, setSelectedId, loading, detailLoading, running, error, runComparison, refresh } = usePdfParserComparison();
  const [activeTab, setActiveTab] = useState<Tab>("summary");
  const [runId, setRunId] = useState("ball-screw-parser-comparison");
  const [title, setTitle] = useState("Ball Screw Parser Comparison");
  const [sources, setSources] = useState(defaultSources);
  const [enabledParsers, setEnabledParsers] = useState<Record<string, boolean>>({ pdfplumber: true, pymupdf: true, docling: true, marker: false });
  const [anchors, setAnchors] = useState(defaultAnchors);
  const [candidates, setCandidates] = useState(defaultCandidates);
  const [expectedTerms, setExpectedTerms] = useState(defaultExpectedTerms);
  const [noiseTerms, setNoiseTerms] = useState(defaultNoiseTerms);
  const [targetChars, setTargetChars] = useState(2200);
  const [overlapChars, setOverlapChars] = useState(220);
  const [maxChars, setMaxChars] = useState(4200);
  const [formError, setFormError] = useState<string | null>(null);

  const summary = selectedReport?.summary ?? {};
  const documents = selectedReport?.documents ?? [];
  const rawJson = formatJson(selectedReport?.raw ?? selectedReport);
  const markdown = selectedReport?.markdown || "";
  const cards = useMemo(() => [
    { label: "Recommendation", value: asString(summary.recommendation, "inconclusive") },
    { label: "Recommended Parser", value: asString(summary.recommended_parser, "-") },
    { label: "Documents", value: `${asNumber(summary.evaluable_document_count)}/${asNumber(summary.document_count)}` },
  ], [summary]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setFormError(null);
    const documentsPayload = parseSources(sources);
    const parsers = Object.entries(enabledParsers).filter(([, enabled]) => enabled).map(([parser]) => parser);
    if (!documentsPayload.length) {
      setFormError("Cần ít nhất 1 PDF source.");
      return;
    }
    if (!parsers.length) {
      setFormError("Cần chọn ít nhất 1 parser.");
      return;
    }
    const payload: ParserComparisonRunRequest = {
      run_id: runId,
      title,
      documents: documentsPayload,
      parsers,
      semantic_anchors: splitTerms(anchors),
      candidate_terms: parseCandidates(candidates),
      expected_terms: splitTerms(expectedTerms),
      noise_terms: splitTerms(noiseTerms),
      target_chars: targetChars,
      overlap_chars: overlapChars,
      max_chars: maxChars
    };
    await runComparison(payload);
    setActiveTab("summary");
  };

  return (
    <section className="stack">
      <div className="card eval-hero">
        <div className="section-header">
          <div>
            <p className="eyebrow">Parser Evaluation</p>
            <h1>PDF Parser Comparison</h1>
            <p>So sánh `pdfplumber` với `PyMuPDF`, xem parsed text, table candidates, metrics và chunk matrix.</p>
          </div>
          <button className="secondary" type="button" onClick={() => void refresh()} disabled={loading}>Refresh reports</button>
        </div>
      </div>

      <form className="card eval-runner" onSubmit={(event) => void handleSubmit(event)}>
        <div className="section-header">
          <div>
            <h2>Run Parser Test</h2>
            <p className="placeholder">Mỗi source dùng format: <code>document-id | /local-nas/path/file.pdf</code></p>
          </div>
          <button type="submit" disabled={running}>{running ? "Running..." : "Run parser comparison"}</button>
        </div>
        {formError ? <p className="error">{formError}</p> : null}
        {error ? <p className="error">{error.message}</p> : null}
        <div className="eval-form-grid">
          <label>Run ID<input value={runId} onChange={(event) => setRunId(event.target.value)} /></label>
          <label>Title<input value={title} onChange={(event) => setTitle(event.target.value)} /></label>
        </div>
        <label>Source files<textarea rows={3} value={sources} onChange={(event) => setSources(event.target.value)} /></label>
        <div className="eval-chip-grid">
          {Object.entries(enabledParsers).map(([parser, enabled]) => (
            <label className="eval-checkbox" key={parser}>
              <input type="checkbox" checked={enabled} onChange={(event) => setEnabledParsers({ ...enabledParsers, [parser]: event.target.checked })} />
              {parser}{parser === "docling" ? " (slow)" : ""}{parser === "marker" ? " (very slow)" : ""}
            </label>
          ))}
        </div>
        <p className="placeholder">
          Khuyến nghị: dùng `pdfplumber + pymupdf + docling` để so sánh chất lượng. `marker` rất nặng,
          có thể timeout sau 5 phút trên máy local.
        </p>
        <div className="eval-form-grid">
          <label>Semantic anchors<textarea rows={7} value={anchors} onChange={(event) => setAnchors(event.target.value)} /></label>
          <label>Candidate terms<textarea rows={7} value={candidates} onChange={(event) => setCandidates(event.target.value)} /></label>
        </div>
        <div className="eval-form-grid">
          <label>Expected terms<textarea rows={6} value={expectedTerms} onChange={(event) => setExpectedTerms(event.target.value)} /></label>
          <label>Noise terms<textarea rows={6} value={noiseTerms} onChange={(event) => setNoiseTerms(event.target.value)} /></label>
        </div>
        <div className="eval-form-grid eval-number-grid">
          <label>Target chars<input type="number" value={targetChars} onChange={(event) => setTargetChars(Number(event.target.value))} /></label>
          <label>Overlap chars<input type="number" value={overlapChars} onChange={(event) => setOverlapChars(Number(event.target.value))} /></label>
          <label>Max chars<input type="number" value={maxChars} onChange={(event) => setMaxChars(Number(event.target.value))} /></label>
        </div>
      </form>

      <section className="card stack">
        <div className="section-header">
          <h2>Reports</h2>
          {reports.length ? (
            <label className="eval-selector">
              Report
              <select value={selectedId} onChange={(event) => { setSelectedId(event.target.value); setActiveTab("summary"); }}>
                {reports.map((report) => (
                  <option key={report.id} value={report.id}>{report.title} ({report.recommended_parser || report.recommendation})</option>
                ))}
              </select>
            </label>
          ) : null}
        </div>
        {!reports.length ? <div className="empty-state">Chưa có report. Bấm Run parser comparison để tạo report đầu tiên.</div> : null}
        {detailLoading ? <p>Loading report...</p> : null}

        {selectedReport ? (
          <div className="eval-result">
            <div className="eval-cards">
              {cards.map((card) => (
                <article key={card.label} className="eval-card">
                  <span>{card.label}</span>
                  <strong>{card.value}</strong>
                </article>
              ))}
            </div>
            <div className="tabs">
              {tabs.map((tab) => (
                <button key={tab} className={activeTab === tab ? "" : "secondary"} type="button" onClick={() => setActiveTab(tab)}>{tab}</button>
              ))}
            </div>
            <div className="section-header">
              <h2>{activeTab}</h2>
              <div className="actions">
                <button className="secondary" type="button" onClick={() => void copyText(markdown || rawJson)}>Copy Markdown</button>
                <button className="secondary" type="button" onClick={() => void copyText(rawJson)}>Copy JSON</button>
              </div>
            </div>

            {activeTab === "summary" ? (
              <table>
                <thead><tr><th>Document</th><th>Status</th><th>Recommended</th><th>Source</th></tr></thead>
                <tbody>
                  {documents.map((document) => (
                    <tr key={asString(document.document_id)}>
                      <td>{asString(document.document_id)}</td>
                      <td>{asString(document.status)}</td>
                      <td>{asString(document.recommended_parser)}</td>
                      <td className="eval-path">{asString(document.source_path)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : null}

            {activeTab === "metrics" ? (
              <div className="stack">
                {documents.map((document) => (
                  <article className="eval-document" key={asString(document.document_id)}>
                    <h3>{asString(document.document_id)}</h3>
                    <table>
                      <thead><tr><th>Parser</th><th>Status</th><th>Score</th><th>Anchors</th><th>Numeric</th><th>Artifacts</th><th>Broken</th><th>Tables</th><th>Latency</th></tr></thead>
                      <tbody>
                        {getParserResults(document).map((result) => {
                          const metrics = getMetrics(result);
                          return (
                            <tr key={asString(result.parser)}>
                              <td>{asString(result.parser)}</td>
                              <td>{asString(result.status)} {result.error ? <span className="error">{asString(result.error)}</span> : null}</td>
                              <td>{asNumber(result.score).toFixed(2)}</td>
                              <td>{asNumber(metrics.semantic_anchor_hit_rate).toFixed(2)}</td>
                              <td>{asNumber(metrics.numeric_density).toFixed(3)}</td>
                              <td>{asNumber(metrics.header_footer_artifact_count)}</td>
                              <td>{asNumber(metrics.broken_token_count)}</td>
                              <td>{asNumber(metrics.table_candidate_count)}/{asNumber(metrics.reconstructed_table_count)}</td>
                              <td>{asNumber(metrics.latency_ms).toFixed(0)}ms</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </article>
                ))}
              </div>
            ) : null}

            {activeTab === "parsed" ? (
              <div className="stack">
                {documents.map((document) => getParserResults(document).map((result) => {
                  const text = asString(result.normalized_text, asString(result.text, ""));
                  return (
                    <article className="eval-document" key={`${asString(document.document_id)}-${asString(result.parser)}`}>
                      <div className="section-header">
                        <h3>{asString(document.document_id)} / {asString(result.parser)}</h3>
                        <button className="secondary" type="button" onClick={() => void copyText(text)}>Copy Parsed Text</button>
                      </div>
                      <pre className="diagnostics-log">{text || asString(result.error, "No parsed text")}</pre>
                    </article>
                  );
                }))}
              </div>
            ) : null}

            {activeTab === "tables" ? (
              <div className="stack">
                {documents.map((document) => getParserResults(document).map((result) => (
                  <article className="eval-document" key={`${asString(document.document_id)}-${asString(result.parser)}-tables`}>
                    <h3>{asString(document.document_id)} / {asString(result.parser)}</h3>
                    {getTables(result).length ? getTables(result).map((table, index) => (
                      <pre className="eval-chunk" key={index}>{asString(table.markdown, asString(table.text, ""))}</pre>
                    )) : <p className="placeholder">No table candidates detected.</p>}
                  </article>
                )))}
              </div>
            ) : null}

            {activeTab === "matrix" ? (
              <div className="stack">
                {documents.map((document) => getParserResults(document).map((result) => (
                  <article className="eval-document" key={`${asString(document.document_id)}-${asString(result.parser)}-matrix`}>
                    <h3>{asString(document.document_id)} / {asString(result.parser)}</h3>
                    <table>
                      <thead><tr><th>Strategy</th><th>Chunks</th><th>Avg chars</th><th>Max chars</th><th>Candidates</th><th>Expected</th><th>Noise</th></tr></thead>
                      <tbody>
                        {getMatrix(result).map((row) => {
                          const terms = row.term_metrics && typeof row.term_metrics === "object" ? row.term_metrics as Record<string, any> : {};
                          return (
                            <tr key={asString(row.strategy)}>
                              <td>{asString(row.strategy)}</td>
                              <td>{asNumber(row.chunk_count)}</td>
                              <td>{asNumber(row.avg_chunk_chars).toFixed(1)}</td>
                              <td>{asNumber(row.max_chunk_chars)}</td>
                              <td>{asNumber(terms.candidate_coverage?.rate).toFixed(2)}</td>
                              <td>{asNumber(terms.expected_term_coverage?.rate).toFixed(2)}</td>
                              <td>{asNumber(terms.noise_hit_count)}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </article>
                )))}
              </div>
            ) : null}

            {activeTab === "raw" ? <pre className="diagnostics-log">{rawJson}</pre> : null}
          </div>
        ) : null}
      </section>
    </section>
  );
}
