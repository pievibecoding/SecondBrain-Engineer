import { FormEvent, useState } from "react";
import { useDiagnostics } from "../../hooks/useDiagnostics";

const tabs = ["diagnosis", "parse", "chunks", "retrieval", "context", "prompt", "llm", "raw"] as const;
type Tab = typeof tabs[number];

function linesToArray(value: string): string[] {
  return value.split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
}

function formatJson(value: unknown): string {
  return JSON.stringify(value ?? null, null, 2);
}

async function copyText(value: string): Promise<void> {
  await navigator.clipboard.writeText(value);
}

function stageText(stage: unknown): string {
  if (!stage || typeof stage !== "object") {
    return "";
  }
  const maybeText = stage as { text?: unknown; answer?: unknown; diff?: unknown };
  if (typeof maybeText.text === "string") {
    return maybeText.text;
  }
  if (typeof maybeText.answer === "string") {
    return maybeText.answer;
  }
  if (typeof maybeText.diff === "string") {
    return maybeText.diff;
  }
  return formatJson(stage);
}

export function AdminDiagnosticsPage() {
  const { result, loading, error, run } = useDiagnostics();
  const [query, setQuery] = useState("");
  const [fileId, setFileId] = useState("");
  const [folderPath, setFolderPath] = useState("");
  const [expectedTerms, setExpectedTerms] = useState("");
  const [expectedSourcePaths, setExpectedSourcePaths] = useState("");
  const [activeTab, setActiveTab] = useState<Tab>("diagnosis");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    await run({
      query,
      file_id: fileId.trim() || null,
      folder_path: folderPath.trim() || null,
      expected_terms: linesToArray(expectedTerms),
      expected_source_paths: linesToArray(expectedSourcePaths),
    });
    setActiveTab("diagnosis");
  };

  const activePayload = activeTab === "raw"
    ? result
    : activeTab === "diagnosis"
      ? result?.diagnosis
      : result?.stages?.[activeTab];
  const activeJson = formatJson(activePayload);
  const activeText = activeTab === "diagnosis"
    ? `${result?.diagnosis.code}\n${result?.diagnosis.reason}\n${result?.diagnosis.next_action}`
    : activeTab === "raw"
      ? activeJson
      : stageText(activePayload);

  return (
    <section className="card stack">
      <h1>Diagnostics</h1>
      <form className="diagnostics-form" onSubmit={submit}>
        <label>Question<textarea rows={3} value={query} onChange={(event) => setQuery(event.target.value)} required /></label>
        <label>Document ID<input value={fileId} onChange={(event) => setFileId(event.target.value)} placeholder="Optional NasFile id" /></label>
        <label>Folder path<input value={folderPath} onChange={(event) => setFolderPath(event.target.value)} placeholder="/local-nas/projects/Demo" /></label>
        <label>Expected terms<textarea rows={4} value={expectedTerms} onChange={(event) => setExpectedTerms(event.target.value)} placeholder="One term per line" /></label>
        <label>Expected source paths<textarea rows={4} value={expectedSourcePaths} onChange={(event) => setExpectedSourcePaths(event.target.value)} placeholder="One path per line" /></label>
        <button type="submit" disabled={loading}>{loading ? "Running..." : "Run diagnostic"}</button>
      </form>
      {error ? <p className="error">{error.message}</p> : null}
      {result ? (
        <div className="diagnostics-result">
          <div className={`diagnosis-pill diagnosis-${result.diagnosis.code}`}>{result.diagnosis.code}</div>
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
              <button className="secondary" type="button" onClick={() => void copyText(activeText)}>Copy Text</button>
              <button className="secondary" type="button" onClick={() => void copyText(activeJson)}>Copy JSON</button>
            </div>
          </div>
          <pre className="diagnostics-log">{activeTab === "raw" ? activeJson : activeText}</pre>
        </div>
      ) : null}
    </section>
  );
}
