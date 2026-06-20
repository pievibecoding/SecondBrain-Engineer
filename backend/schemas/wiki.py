from datetime import datetime
from pydantic import BaseModel, ConfigDict


class EntitySummaryResponse(BaseModel):
    name: str
    type: str
    description: str | None = None
    score: float | None = None


class RelationItem(BaseModel):
    src: str
    rel_type: str
    tgt: str
    description: str | None = None
    source: str | None = None


class SourceDocument(BaseModel):
    file: str
    nas_path: str | None = None
    url: str | None = None
    page: int | None = None
    excerpt: str | None = None


class GraphNode(BaseModel):
    id: str
    label: str
    type: str | None = None


class GraphEdge(BaseModel):
    source: str
    target: str
    label: str | None = None


class WikiPageResponse(BaseModel):
    name: str
    type: str
    description: str | None = None
    relations: list[RelationItem] = []
    sources: list[SourceDocument] = []
    graph_nodes: list[GraphNode] = []
    graph_edges: list[GraphEdge] = []
