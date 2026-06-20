import { FormEvent, useMemo, useState } from "react";
import { useAdaptiveChunkingEvaluations } from "../../hooks/useAdaptiveChunkingEvaluations";
import type { AdaptiveChunkingRunRequest } from "../../types";

const tabs = ["overview", "coverage", "chunks", "documents", "evidence", "noise", "raw"] as const;
type Tab = typeof tabs[number];

const defaultSources = [
  "omron-e3z | /local-nas/projects/Demo/Sensor/Omron/Datasheet-cam-bien-tiem-can-Omron-E3Z-Series.pdf",
  "autonics-bms | /local-nas/projects/Demo/Sensor/Autonics/Sensorguong.pdf",
  "autonics-bf4 | /local-nas/projects/Demo/Sensor/Autonics/Khuech dai quang Autonic.pdf"
].join("\n");

const defaultCandidates = [
  "E3Z: E3Z, E3Z-B, E3Z-B61, E3Z-B81, Omron E3Z, Omron E3Z Series",
  "BMS: BMS, BMS Series, Autonics BMS",
  "BF4: BF4, BF4 Series, Autonics BF4"
].join("\n");

const defaultExpectedTerms = [
  "chai nước",
  "water bottle",
  "plastic bottle",
  "transparent bottle",
  "clear object",
  "transparent object",
  "photoelectric sensor",
  "retroreflective sensor"
].join("\n");

const defaultNoiseTerms = [
  "mounting screw",
  "zip tie",
  "maintenance",
  "cleaning",
  "fork sensor",
  "label detection",
  "housing",
  "dimension",
  "cirtceleotohP"
].join("\n");

function asNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function asString(value: unknown, fallback = "-"): string {
  return typeof value === "string" && value ? value : fallback;
}

function formatJson(value: unknown): string {
  return JSON.stringify(value ?? null, null, 2);
}

async function copyText(value: string): Promise<void> {
  await navigator.clipboard.writeText(value);
}

function splitTerms(value: string): string[] {
  return value
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
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
      if (key && aliases.length) {
        acc[key] = aliases;
      }
      return acc;
    }, {});
}

function getStrategies(document: Record<string, unknown>): Array<Record<string, unknown>> {
  return Array.isArray(document.strategies) ? document.strategies as Array<Record<string, unknown>> : [];
}

function getMetrics(strategy: Record<string, unknown>): Record<string, any> {
  return strategy.metrics && typeof strategy.metrics === "object" ? strategy.metrics as Record<string, any> : {};
}

function getWinner(document: Record<string, unknown>): Record<string, unknown> | undefined {
  return getStrategies(document).find((strategy) => strategy.name === document.winner);
}

function getChunks(strategy: Record<string, unknown> | undefined): Array<Record<string, unknown>> {
  if (!strategy) return [];
  if (Array.isArray(strategy.chunks)) return strategy.chunks as Array<Record<string, unknown>>;
  if (Array.isArray(strategy.sample_chunks)) return strategy.sample_chunks as Array<Record<string, unknown>>;
  return [];
}

function recommendationClass(value: unknown): string {
  const recommendation = asString(value, "inconclusive");
  if (recommendation === "recommended") return "eval-good";
  if (recommendation === "not_recommended") return "eval-bad";
  return "eval-warn";
}

function CandidateBadge({ value }: { value: boolean }) {
  return <span className={`eval-badge ${value ? "eval-badge-good" : "eval-badge-bad"}`}>{value ? "hit" : "miss"}</span>;
}

export function AdminAdaptiveChunkingPage() {
  const { reports, selectedReport, selectedId, setSelectedId, loading, detailLoading, running, error, runEvaluation, refresh } = useAdaptiveChunkingEvaluations();
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [runId, setRunId] = useState("sensor-ui-test");
  const [title, setTitle] = useState("Sensor Adaptive Chunking UI Test");
  const [sources, setSources] = useState(defaultSources);
  const [candidates, setCandidates] = useState(defaultCandidates);
  const [expectedTerms, setExpectedTerms] = useState(defaultExpectedTerms);
  const [noiseTerms, setNoiseTerms] = useState(defaultNoiseTerms);
  const [targetChars, setTargetChars] = useState(2200);
  const [overlapChars, setOverlapChars] = useState(220);
  const [maxChars, setMaxChars] = useState(4200);
  const [formError, setFormError] = useState<string | null>(null);

  const documents = selectedReport?.documents ?? [];
  const rawJson = formatJson(selectedReport?.raw ?? selectedReport);
  const markdown = selectedReport?.markdown || "";
  const summary = selectedReport?.summary ?? {};
  const candidateNames = Object.keys(parseCandidates(candidates));

  const aggregateCards = useMemo(() => [
    { label: "Recommendation", value: asString(summary.recommendation, "inconclusive"), className: recommendationClass(summary.recommendation) },
    { label: "Documents", value: `${asNumber(summary.evaluable_document_count)}/${asNumber(summary.document_count)}`, className: "" },
    { label: "Coverage Delta", value: asNumber(summary.avg_candidate_coverage_delta).toFixed(3), className: asNumber(summary.avg_candidate_coverage_delta) >= 0 ? "eval-good" : "eval-bad" },
    { label: "Noise Delta", value: asNumber(summary.avg_noise_delta).toFixed(2), className: asNumber(summary.avg_noise_delta) <= 0 ? "eval-good" : "eval-bad" }
  ], [summary]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setFormError(null);
    const documentsPayload = parseSources(sources);
    const candidateTerms = parseCandidates(candidates);
    if (!documentsPayload.length) {
      setFormError("Cần ít nhất 1 source file.");
      return;
    }
    if (!Object.keys(candidateTerms).length) {
      setFormError("Cần ít nhất 1 candidate, ví dụ: E3Z: E3Z, Omron E3Z.");
      return;
    }
    const payload: AdaptiveChunkingRunRequest = {
      run_id: runId,
      title,
      documents: documentsPayload,
      candidate_terms: candidateTerms,
      expected_terms: splitTerms(expectedTerms),
      noise_terms: splitTerms(noiseTerms),
      target_chars: targetChars,
      overlap_chars: overlapChars,
      max_chars: maxChars
    };
    await runEvaluation(payload);
    setActiveTab("overview");
  };

  return (
    <section className="stack">
      <div className="card eval-hero">
        <div className="section-header">
          <div>
            <p className="eyebrow">Evaluation Console</p>
            <h1>Adaptive Chunking Self-Test</h1>
            <p>
              Chạy thử parse + chunk strategies ngay trên UI, so sánh candidate coverage/noise,
              rồi xem evidence chunks mà không cần mở terminal.
            </p>
          </div>
          <button className="secondary" type="button" onClick={() => void refresh()} disabled={loading}>Refresh reports</button>
        </div>
      </div>

      <form className="card eval-runner" onSubmit={(event) => void handleSubmit(event)}>
        <div className="section-header">
          <div>
            <h2>Run New Test</h2>
            <p className="placeholder">Mỗi source dùng format: <code>document-id | /local-nas/path/file.pdf</code></p>
          </div>
          <button type="submit" disabled={running}>{running ? "Running..." : "Run evaluation"}</button>
        </div>

        {formError ? <p className="error">{formError}</p> : null}
        {error ? <p className="error">{error.message}</p> : null}

        <div className="eval-form-grid">
          <label>
            Run ID
            <input value={runId} onChange={(event) => setRunId(event.target.value)} />
          </label>
          <label>
            Title
            <input value={title} onChange={(event) => setTitle(event.target.value)} />
          </label>
        </div>

        <label>
          Source files
          <textarea rows={5} value={sources} onChange={(event) => setSources(event.target.value)} />
        </label>

        <div className="eval-form-grid">
          <label>
            Candidate terms
            <textarea rows={6} value={candidates} onChange={(event) => setCandidates(event.target.value)} />
          </label>
          <label>
            Expected terms
            <textarea rows={6} value={expectedTerms} onChange={(event) => setExpectedTerms(event.target.value)} />
          </label>
          <label>
            Noise terms
            <textarea rows={6} value={noiseTerms} onChange={(event) => setNoiseTerms(event.target.value)} />
          </label>
        </div>

        <div className="eval-form-grid eval-number-grid">
          <label>
            Target chars
            <input type="number" value={targetChars} onChange={(event) => setTargetChars(Number(event.target.value))} />
          </label>
          <label>
            Overlap chars
            <input type="number" value={overlapChars} onChange={(event) => setOverlapChars(Number(event.target.value))} />
          </label>
          <label>
            Max chars
            <input type="number" value={maxChars} onChange={(event) => setMaxChars(Number(event.target.value))} />
          </label>
        </div>
      </form>

      <section className="card stack">
        <div className="section-header">
          <div>
            <h2>Reports</h2>
            <p className="placeholder">Chọn report cũ hoặc report vừa chạy để soi chi tiết.</p>
          </div>
        </div>

        {reports.length ? (
          <label className="eval-selector">
            Report
            <select value={selectedId} onChange={(event) => { setSelectedId(event.target.value); setActiveTab("overview"); }}>
              {reports.map((report) => (
                <option key={report.id} value={report.id}>{report.title} ({report.recommendation})</option>
              ))}
            </select>
          </label>
        ) : (
          <div className="empty-state">
            <strong>No adaptive chunking reports yet.</strong>
            <p>Điền form phía trên rồi bấm Run evaluation để tạo report đầu tiên.</p>
          </div>
        )}

        {detailLoading ? <p>Loading report...</p> : null}

        {selectedReport ? (
          <div className="eval-result">
            <div className="eval-cards">
              {aggregateCards.map((card) => (
                <article key={card.label} className={`eval-card ${card.className}`}>
                  <span>{card.label}</span>
                  <strong>{card.value}</strong>
                </article>
              ))}
            </div>

            <div className="tabs">
              {tabs.map((tab) => (
                <button key={tab} className={activeTab === tab ? "" : "secondary"} type="button" onClick={() => setActiveTab(tab)}>
                  {tab}
                </button>
              ))}
            </div>

            <div className="section-header">
              <h2>{activeTab}</h2>
              <div className="actions">
                <button className="secondary" type="button" onClick={() => void copyText(markdown || rawJson)}>Copy Markdown</button>
                <button className="secondary" type="button" onClick={() => void copyText(rawJson)}>Copy JSON</button>
              </div>
            </div>

            {activeTab === "overview" ? (
              <div className="stack">
                <table>
                  <thead>
                    <tr><th>Document</th><th>Status</th><th>Winner</th><th>Parser</th><th>Source</th></tr>
                  </thead>
                  <tbody>
                    {documents.map((document) => (
                      <tr key={asString(document.document_id)}>
                        <td>{asString(document.document_id)}</td>
                        <td>{asString(document.status)}</td>
                        <td>{asString(document.winner)}</td>
                        <td>{asString(document.parser)}</td>
                        <td className="eval-path">{asString(document.source_path)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}

            {activeTab === "coverage" ? (
              <div className="stack">
                {documents.map((document) => {
                  const winner = getWinner(document);
                  const metrics = getMetrics(winner ?? {});
                  const byCandidate = metrics.candidate_coverage?.by_candidate ?? {};
                  const byTerm = metrics.expected_term_coverage?.by_term ?? {};
                  return (
                    <article className="eval-document" key={asString(document.document_id)}>
                      <h3>{asString(document.document_id)}</h3>
                      <div className="eval-chip-grid">
                        {candidateNames.map((name) => (
                          <div className="eval-chip" key={name}>
                            <span>{name}</span>
                            <CandidateBadge value={Boolean(byCandidate[name])} />
                          </div>
                        ))}
                      </div>
                      <details>
                        <summary>Expected term hits</summary>
                        <div className="eval-chip-grid">
                          {Object.entries(byTerm).map(([term, hit]) => (
                            <div className="eval-chip" key={term}>
                              <span>{term}</span>
                              <CandidateBadge value={Boolean(hit)} />
                            </div>
                          ))}
                        </div>
                      </details>
                    </article>
                  );
                })}
              </div>
            ) : null}

            {activeTab === "documents" ? (
              <div className="stack">
                {documents.map((document) => (
                  <article className="eval-document" key={asString(document.document_id)}>
                    <h3>{asString(document.document_id)}</h3>
                    {document.error ? <p className="error">{asString(document.error)}</p> : null}
                    <table>
                      <thead>
                        <tr><th>Strategy</th><th>Score</th><th>Candidates</th><th>Expected</th><th>Noise</th><th>Chunks</th><th>Max chars</th></tr>
                      </thead>
                      <tbody>
                        {getStrategies(document).map((strategy) => {
                          const metrics = getMetrics(strategy);
                          const score = strategy.score && typeof strategy.score === "object" ? strategy.score as Record<string, unknown> : {};
                          return (
                            <tr key={asString(strategy.name)}>
                              <td>{asString(strategy.name)} {strategy.name === document.winner ? <strong>(winner)</strong> : null}</td>
                              <td>{asNumber(score.score).toFixed(3)}</td>
                              <td>{asNumber(metrics.candidate_coverage?.rate).toFixed(3)}</td>
                              <td>{asNumber(metrics.expected_term_coverage?.rate).toFixed(3)}</td>
                              <td>{asNumber(metrics.noise_hit_count)}</td>
                              <td>{asNumber(metrics.chunk_count)}</td>
                              <td>{asNumber(metrics.max_chunk_chars)}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </article>
                ))}
              </div>
            ) : null}

            {activeTab === "chunks" ? (
              <div className="stack">
                <p className="placeholder">
                  Đây là text sau khi chunking. Mỗi document hiển thị strategy thắng trước; mở các strategy khác để so sánh.
                </p>
                {documents.map((document) => {
                  const winnerName = asString(document.winner);
                  const sortedStrategies = [...getStrategies(document)].sort((left, right) => {
                    if (left.name === winnerName) return -1;
                    if (right.name === winnerName) return 1;
                    return asString(left.name).localeCompare(asString(right.name));
                  });
                  return (
                    <article className="eval-document" key={asString(document.document_id)}>
                      <div className="section-header">
                        <div>
                          <h3>{asString(document.document_id)}</h3>
                          <p className="placeholder">Winner: <strong>{winnerName}</strong></p>
                        </div>
                      </div>
                      {sortedStrategies.map((strategy, strategyIndex) => {
                        const chunks = getChunks(strategy);
                        const strategyText = chunks
                          .map((chunk) => `[chunk ${asNumber(chunk.chunk_index)} | ${asNumber(chunk.char_count)} chars]\n${asString(chunk.text, "")}`)
                          .join("\n\n---\n\n");
                        return (
                          <details key={asString(strategy.name)} open={strategyIndex === 0}>
                            <summary>
                              {asString(strategy.name)} {strategy.name === document.winner ? "(winner)" : ""} - {chunks.length} chunks
                            </summary>
                            <div className="actions eval-chunk-actions">
                              <button className="secondary" type="button" onClick={() => void copyText(strategyText)}>Copy all chunks</button>
                            </div>
                            {chunks.length ? chunks.map((chunk) => (
                              <article className="eval-single-chunk" key={`${asString(strategy.name)}-${asNumber(chunk.chunk_index)}`}>
                                <div className="section-header">
                                  <strong>Chunk {asNumber(chunk.chunk_index)}</strong>
                                  <span className="placeholder">{asNumber(chunk.char_count)} chars</span>
                                </div>
                                <pre className="eval-chunk">{asString(chunk.text, "")}</pre>
                              </article>
                            )) : <p className="placeholder">Report cũ chỉ có sample chunks hoặc chưa lưu chunks đầy đủ. Hãy bấm Run evaluation lại để tạo report mới.</p>}
                          </details>
                        );
                      })}
                    </article>
                  );
                })}
              </div>
            ) : null}

            {activeTab === "evidence" ? (
              <div className="stack">
                {documents.map((document) => {
                  const evidence = getMetrics(getWinner(document) ?? {}).top_evidence ?? [];
                  return (
                    <article className="eval-document" key={asString(document.document_id)}>
                      <h3>{asString(document.document_id)}</h3>
                      {evidence.length ? evidence.map((item: Record<string, unknown>, index: number) => (
                        <pre className="eval-chunk" key={`${asString(document.document_id)}-${index}`}>{asString(item.text)}</pre>
                      )) : <p className="placeholder">No evidence chunks found.</p>}
                    </article>
                  );
                })}
              </div>
            ) : null}

            {activeTab === "noise" ? (
              <div className="stack">
                {documents.map((document) => {
                  const noise = getMetrics(getWinner(document) ?? {}).top_noise ?? [];
                  return (
                    <article className="eval-document" key={asString(document.document_id)}>
                      <h3>{asString(document.document_id)}</h3>
                      {noise.length ? noise.map((item: Record<string, unknown>, index: number) => (
                        <pre className="eval-chunk" key={`${asString(document.document_id)}-noise-${index}`}>{asString(item.text)}</pre>
                      )) : <p className="placeholder">No major noise chunks found.</p>}
                    </article>
                  );
                })}
              </div>
            ) : null}

            {activeTab === "raw" ? <pre className="diagnostics-log">{rawJson}</pre> : null}
          </div>
        ) : null}
      </section>
    </section>
  );
}
