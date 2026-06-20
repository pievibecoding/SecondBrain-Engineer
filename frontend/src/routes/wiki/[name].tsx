import { Link, useNavigate, useParams } from "react-router-dom";
import { RelationGraph } from "../../components/wiki/RelationGraph";
import { useWikiEntity } from "../../hooks/useWikiEntity";

export function WikiEntityPage() {
  const { name } = useParams();
  const navigate = useNavigate();
  const { data, loading, error } = useWikiEntity(name);
  if (loading && !data) {
    return <div className="card">Loading entity...</div>;
  }
  if (error) {
    return <div className="card error">{error.message}</div>;
  }
  if (!data) {
    return <div className="card">Entity not found.</div>;
  }
  return (
    <div className="stack">
      <section className="card entity-header">
        <div>
          <p className="eyebrow">{data.type}</p>
          <h1>{data.name}</h1>
          <p>{data.description || "No description available."}</p>
        </div>
        <Link className="button-link" to={`/chat?q=${encodeURIComponent(data.name)}`}>Hỏi AI về {data.name}</Link>
      </section>
      <section className="card">
        <h2>Relations</h2>
        <RelationGraph nodes={data.graph_nodes} edges={data.graph_edges} onNodeClick={(node) => navigate(`/wiki/${encodeURIComponent(node.id)}`)} />
        <div className="list">
          {data.relations.map((relation, index) => (
            <div className="list-row" key={`${relation.src}-${relation.tgt}-${index}`}>
              <strong>{relation.src}</strong>
              <span>{relation.rel_type}</span>
              <strong>{relation.tgt}</strong>
              <small>{relation.description}</small>
            </div>
          ))}
        </div>
      </section>
      <section className="card">
        <h2>Sources</h2>
        <div className="list">
          {data.sources.map((source) => (
            <a className="list-row" href={source.url || "#"} target="_blank" rel="noreferrer" key={`${source.file}-${source.page || ""}`}>
              <strong>{source.file}</strong>
              <span>{source.page ? `Page ${source.page}` : source.nas_path}</span>
              <small>{source.excerpt}</small>
            </a>
          ))}
        </div>
      </section>
    </div>
  );
}
