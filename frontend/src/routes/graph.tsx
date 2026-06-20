const graphUrl = import.meta.env.VITE_LIGHTRAG_WEB_URL || "http://localhost:9621";

export function GraphPage() {
  return (
    <div className="stack">
      <section className="card">
        <h1>Knowledge Graph</h1>
        <p>Embedded LightRAG Web UI. If it is unavailable, start the LightRAG service on port 9621.</p>
      </section>
      <section className="card graph-frame-card">
        <iframe
          title="LightRAG Web UI"
          src={graphUrl}
          sandbox="allow-scripts allow-same-origin allow-forms"
          referrerPolicy="no-referrer"
        />
        <p className="placeholder">Graph UI placeholder: {graphUrl}</p>
      </section>
    </div>
  );
}
