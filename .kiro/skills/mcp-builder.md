---
name: mcp-builder
description: Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. Use when building MCP servers to integrate external APIs or services, whether in Python (FastMCP) or Node/TypeScript (MCP SDK).
license: Complete terms in LICENSE.txt
---

# MCP Server Development Guide

## Overview

Create MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. The quality of an MCP server is measured by how well it enables LLMs to accomplish real-world tasks.

---

# Process

## High-Level Workflow

Creating a high-quality MCP server involves four main phases:

### Phase 1: Deep Research and Planning

**API Coverage vs. Workflow Tools:**
Balance comprehensive API endpoint coverage with specialized workflow tools. Workflow tools can be more convenient for specific tasks, while comprehensive coverage gives agents flexibility to compose operations. When uncertain, prioritize comprehensive API coverage.

**Tool Naming and Discoverability:**
Clear, descriptive tool names help agents find the right tools quickly. Use consistent prefixes (e.g., `secondbrain_search`, `secondbrain_get_entity`) and action-oriented naming.

**Context Management:**
Agents benefit from concise tool descriptions and the ability to filter/paginate results. Design tools that return focused, relevant data.

**Actionable Error Messages:**
Error messages should guide agents toward solutions with specific suggestions and next steps.

#### Study MCP Protocol Documentation

Navigate the MCP specification:
- Start with: `https://modelcontextprotocol.io/sitemap.xml`
- Key pages: Specification overview, transport mechanisms, tool/resource/prompt definitions

#### Recommended Stack
- **Language**: TypeScript (high-quality SDK support) or Python (FastMCP)
- **Transport**: Streamable HTTP for remote servers (stateless JSON). stdio for local servers.

**Load framework docs during Phase 1/2:**
- Python SDK: `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md`
- TypeScript SDK: `https://raw.githubusercontent.com/modelcontextprotocol/typescript-sdk/main/README.md`

---

### Phase 2: Implementation

#### Project Structure

**Python (FastMCP) — recommended for SecondBrain:**
```python
# backend/mcp/server.py
from fastmcp import FastMCP

mcp = FastMCP("SecondBrain — Robolinks Knowledge Hub")

@mcp.tool()
async def search_knowledge(query: str, mode: str = "mix") -> str:
    """Search Robolinks knowledge base. mode: mix/local/global/naive"""
    ...

@mcp.tool()
async def get_entity(entity_name: str) -> dict:
    """Get entity info: description, relations, source documents."""
    ...
```

#### Core Implementation Principles

For each tool:

**Input Schema:**
- Use Pydantic (Python) for validation
- Include constraints and clear descriptions

**Tool Description:**
- Concise summary of functionality
- Parameter descriptions
- Return type info

**Implementation:**
- Async/await for all I/O operations
- Proper error handling with actionable messages
- Support pagination where applicable

**Tool Annotations:**
- `readOnlyHint`: true/false
- `destructiveHint`: true/false

---

### Phase 3: Review and Test

**Code Quality:**
- No duplicated code (DRY principle)
- Consistent error handling
- Full type coverage
- Clear tool descriptions

**Test with MCP Inspector:**
```bash
npx @modelcontextprotocol/inspector
```

---

### Phase 4: Create Evaluations

After implementing, create 10 evaluation questions to test effectiveness:
- **Independent**: Not dependent on other questions
- **Read-only**: Only non-destructive operations
- **Complex**: Requiring multiple tool calls
- **Realistic**: Based on real Robolinks use cases
- **Verifiable**: Single, clear answer

---

## Reference Files

### Core MCP Documentation
- **MCP Protocol**: `https://modelcontextprotocol.io/sitemap.xml`
- **Python SDK**: `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md`
- **TypeScript SDK**: `https://raw.githubusercontent.com/modelcontextprotocol/typescript-sdk/main/README.md`

---
*Source: [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills/mcp-builder) — Anthropic Official*
