import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { CitationCard } from "./CitationCard";

describe("CitationCard", () => {
  it("renders document citation", () => {
    render(<CitationCard citation={{ type: "document", file: "BOM.xlsx", page: 2, excerpt: "Motor Siemens" }} />, { wrapper: MemoryRouter });
    expect(screen.getByText("BOM.xlsx")).toBeInTheDocument();
    expect(screen.getByText("Motor Siemens")).toBeInTheDocument();
  });
});
