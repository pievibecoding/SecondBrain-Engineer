import { useNavigate } from "react-router-dom";
import type { CitationItem } from "../../types";

export function CitationCard({ citation }: { citation: CitationItem }) {
  const navigate = useNavigate();
  const label = citation.file || citation.entity || citation.target || "Source";
  const detail = citation.excerpt || citation.relation || (citation.page ? `Page ${citation.page}` : citation.type);

  const open = () => {
    if (citation.type === "graph_entity" && citation.entity) {
      navigate(`/wiki/${encodeURIComponent(citation.entity)}`);
      return;
    }
    if (citation.url) {
      window.open(citation.url, "_blank", "noopener,noreferrer");
    }
  };

  return (
    <button
      className="citation-card"
      type="button"
      onClick={open}
      aria-label={`Citation: ${label}${detail ? ` — ${detail}` : ""}`}
    >
      <span>{label}</span>
      <small>{detail}</small>
    </button>
  );
}
