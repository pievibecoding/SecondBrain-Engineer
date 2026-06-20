import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RelationGraph } from "./RelationGraph";

describe("RelationGraph", () => {
  it("renders graph nodes and edges", () => {
    render(<RelationGraph nodes={[{ id: "Alpha", label: "Alpha" }, { id: "PLC", label: "PLC" }]} edges={[{ source: "Alpha", target: "PLC", label: "USES" }]} />);
    expect(screen.getByRole("img", { name: "Relation graph" })).toBeInTheDocument();
    expect(screen.getByText("USES")).toBeInTheDocument();
  });
});
