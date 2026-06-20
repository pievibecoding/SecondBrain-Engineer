import { useDocuments } from "../../hooks/useDocuments";

export function AdminDocumentsPage() {
  const { documents, loading, error, compareReport, compare, reindex, remove, removeAll } = useDocuments();
  return (
    <section className="card">
      <div className="section-header">
        <h1>Documents</h1>
        <button className="secondary" type="button" disabled={!documents.length} onClick={() => void removeAll()}>
          Delete all
        </button>
      </div>
      {loading ? <p>Loading...</p> : null}
      {error ? <p className="error">{error.message}</p> : null}
      {compareReport ? (
        <div className="compare-panel">
          <div className="compare-grid">
            <article>
              <h2>Parsed</h2>
              <p><strong>Parser:</strong> {compareReport.parsed.parser_used || "-"}</p>
              <p><strong>Chars:</strong> {compareReport.parsed.char_count}</p>
              <p><strong>Lines:</strong> {compareReport.parsed.line_count}</p>
              <pre>{compareReport.parsed.text}</pre>
            </article>
            <article>
              <h2>Chunks</h2>
              <p><strong>Count:</strong> {compareReport.chunks.count}</p>
              <p><strong>Chars:</strong> {compareReport.chunks.char_count}</p>
              <p><strong>Lines:</strong> {compareReport.chunks.line_count}</p>
              {compareReport.chunks.error ? <p className="error">{compareReport.chunks.error}</p> : null}
              <pre>{compareReport.chunks.text}</pre>
            </article>
          </div>
          <article>
            <h2>Compare</h2>
            <p><strong>Similarity:</strong> {(compareReport.compare.similarity_ratio * 100).toFixed(2)}%</p>
            {compareReport.compare.first_diff_index !== null ? (
              <p><strong>First diff index:</strong> {compareReport.compare.first_diff_index}</p>
            ) : null}
            <details>
              <summary>Full diff</summary>
              <pre>{compareReport.compare.diff_preview || "(no diff)"}</pre>
            </details>
          </article>
        </div>
      ) : null}
      <table>
        <thead><tr><th>Path</th><th>Status</th><th>Chunks</th><th>Indexed</th><th>Actions</th></tr></thead>
        <tbody>
          {documents.map((document) => (
            <tr key={document.id}>
              <td>{document.nas_path}</td>
              <td>
                <div>{document.status}</div>
                {document.error_msg ? <div className="inline-error">{document.error_msg}</div> : null}
              </td>
              <td>{document.chunk_count || "-"}</td>
              <td>{document.indexed_at ? new Date(document.indexed_at).toLocaleString() : "-"}</td>
              <td className="actions">
                <button className="secondary" type="button" onClick={() => void compare(document.id)}>Compare</button>
                <button type="button" onClick={() => void reindex(document.id)}>Reindex</button>
                <button className="secondary" type="button" onClick={() => void remove(document.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
