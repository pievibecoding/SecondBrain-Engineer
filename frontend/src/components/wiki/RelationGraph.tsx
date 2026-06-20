import { useMemo, useState } from "react";
import type { GraphEdge, GraphNode } from "../../types";

interface RelationGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick?: (node: GraphNode) => void;
}

export function RelationGraph({ nodes, edges, onNodeClick }: RelationGraphProps) {
  const [scale, setScale] = useState(1);
  const layout = useMemo(() => {
    const center = { x: 300, y: 180 };
    const radius = 125;
    return nodes.map((node, index) => {
      if (index === 0) {
        return { ...node, ...center };
      }
      const angle = ((index - 1) / Math.max(nodes.length - 1, 1)) * Math.PI * 2;
      return { ...node, x: center.x + Math.cos(angle) * radius, y: center.y + Math.sin(angle) * radius };
    });
  }, [nodes]);
  const byId = new Map(layout.map((node) => [node.id, node]));

  if (nodes.length === 0) {
    return <div className="graph-empty">No graph relations available.</div>;
  }

  return (
    <div className="relation-graph">
      <div className="graph-toolbar">
        <button type="button" onClick={() => setScale((value) => Math.max(0.6, value - 0.2))}>-</button>
        <span>{Math.round(scale * 100)}%</span>
        <button type="button" onClick={() => setScale((value) => Math.min(1.8, value + 0.2))}>+</button>
      </div>
      <svg role="img" aria-label="Relation graph" viewBox="0 0 600 360">
        <g transform={`translate(${300 - 300 * scale} ${180 - 180 * scale}) scale(${scale})`}>
          {edges.map((edge, index) => {
            const source = byId.get(edge.source);
            const target = byId.get(edge.target);
            if (!source || !target) {
              return null;
            }
            const midX = (source.x + target.x) / 2;
            const midY = (source.y + target.y) / 2;
            return (
              <g key={`${edge.source}-${edge.target}-${index}`}>
                <line x1={source.x} y1={source.y} x2={target.x} y2={target.y} />
                <text x={midX} y={midY}>{edge.label}</text>
              </g>
            );
          })}
          {layout.map((node) => (
            <g key={node.id} className="graph-node" onClick={() => onNodeClick?.(node)} tabIndex={0} role="button">
              <title>{`${node.label}${node.type ? ` (${node.type})` : ""}`}</title>
              <circle cx={node.x} cy={node.y} r={node.id === nodes[0].id ? 34 : 26} />
              <text x={node.x} y={node.y}>{node.label}</text>
            </g>
          ))}
        </g>
      </svg>
    </div>
  );
}
