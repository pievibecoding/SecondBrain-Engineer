from collections import defaultdict
from typing import Iterable

from backend.schemas.wiki import WikiPageResponse, RelationItem, SourceDocument, GraphNode, GraphEdge


def _dedupe_relations(relations: Iterable[dict]) -> list[RelationItem]:
    seen = set()
    out = []
    for r in relations or []:
        key = (r.get("src"), r.get("rel_type"), r.get("tgt"))
        if key in seen:
            continue
        seen.add(key)
        out.append(RelationItem(src=r.get("src"), rel_type=r.get("rel_type"), tgt=r.get("tgt"), description=r.get("description"), source=r.get("source")))
    return out


def _dedupe_sources(sources: Iterable[dict]) -> list[SourceDocument]:
    seen = set()
    out = []
    for s in sources or []:
        key = (s.get("file"), s.get("nas_path"), s.get("page"))
        if key in seen:
            continue
        seen.add(key)
        out.append(SourceDocument(file=s.get("file"), nas_path=s.get("nas_path"), url=s.get("url"), page=s.get("page"), excerpt=s.get("excerpt")))
    return out


def _build_graph(relations: list[RelationItem], center_name: str) -> tuple[list[GraphNode], list[GraphEdge]]:
    nodes = {center_name: GraphNode(id=center_name, label=center_name, type=None)}
    edges = []
    for r in relations:
        for n in (r.src, r.tgt):
            if n not in nodes:
                nodes[n] = GraphNode(id=n, label=n, type=None)
        edges.append(GraphEdge(source=r.src, target=r.tgt, label=r.rel_type))
    return list(nodes.values()), edges


def build_entity_page(entity: dict, edges: list[dict]) -> WikiPageResponse:
    # normalize entity
    name = entity.get("name") or entity.get("id") or ""
    etype = entity.get("type") or entity.get("entity_type") or ""
    description = entity.get("description")

    # collect relations from both entity and edges
    rels = []
    rels.extend(entity.get("relations") or [])
    # edges list expected as dicts: {src, rel_type, tgt, description}
    rels.extend(edges or [])

    relations = _dedupe_relations(rels)
    sources = _dedupe_sources(entity.get("sources") or [])

    graph_nodes, graph_edges = _build_graph(relations, name)

    return WikiPageResponse(
        name=name,
        type=etype,
        description=description,
        relations=relations,
        sources=sources,
        graph_nodes=graph_nodes,
        graph_edges=graph_edges,
    )
