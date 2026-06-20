---
name: create-steering-documents
description: Create comprehensive steering documents for development projects. Generates project-specific standards, git workflows, and technology guidelines in .kiro/steering/ directory.
version: 1.0.0
license: MIT
compatibility:
  - Kiro
  - Claude Code
  - Cursor
  - Windsurf
metadata:
  category: project-setup
  complexity: intermediate
triggers:
  - create steering documents
  - setup project standards
  - initialize kiro steering
  - project guidelines
---

# Create Steering Documents

Create comprehensive steering documents for a development project based on the project type and requirements.

## Usage

```
Create steering documents for [project description]
```

## Examples

- `Create steering documents for a React TypeScript e-commerce application`
- `Create steering documents for a Python FastAPI REST API with PostgreSQL`
- `Create steering documents for a Node.js microservices architecture`
- `Create steering documents for a Vue.js component library`

## What Are Steering Documents?

Steering documents are contextual guidelines that influence how AI assistants approach development tasks. They contain project-specific standards, conventions, and best practices that help provide more relevant and consistent assistance.

### How They Work

1. **Always Included (Default)**: Documents without front-matter are included in every interaction
2. **File Match Conditional**: Documents with `inclusion: fileMatch` are included when specific files are in context
3. **Manual Inclusion**: Documents with `inclusion: manual` are only included when explicitly referenced

## Process

### 1. Project Analysis

First, analyze the project requirements and determine which steering documents are needed:

**For Full-Stack Projects (like SecondBrain):**
- Include: project-context.md, backend-rules.md, frontend-rules.md
- Consider: nas-rules.md, git-workflow.md, test-rules.md

**For Backend/API Projects (Python/FastAPI):**
- Include: project-context.md, backend-rules.md, development-environment.md
- Consider: database-standards.md, security-guidelines.md

**For Frontend Projects (React, Vue):**
- Include: project-context.md, frontend-rules.md
- Consider: component-library.md, testing-strategy.md

### 2. Core Document Templates

#### project-context.md (always included)
```markdown
# [Project Name] — Project Context

## Stack
- [List services, ports, tech]

## Core data flow
[Describe main data flow]

## Key decisions (do not change without approval)
- [List important architectural decisions]

## File naming conventions
- [List key conventions]
```

#### backend-rules.md (always included for backend projects)
```markdown
# Backend Rules

## Folder structure rules
- schemas/ → [purpose]
- models/ → [purpose]
- services/ → [purpose]
- routers/ → [purpose]

## Import rules
[List what can import from where]

## Error handling
[Error handling conventions]
```

#### frontend-rules.md
```markdown
---
inclusion: fileMatch
fileMatchPattern: '*.tsx|*.jsx|*.ts|*.vue'
---

# Frontend Rules

## Data flow (MANDATORY)
[Component → Hook → api/ → Backend]

## Rules
- [List key conventions]

## Hook naming
[Naming conventions]
```

### 3. Front-matter Options

```yaml
---
inclusion: always|fileMatch|manual
fileMatchPattern: 'glob-pattern'  # for fileMatch only
---
```

### 4. Quality Checklist

Before finalizing steering documents, ensure:
- [ ] All documents have appropriate front-matter for inclusion logic
- [ ] Guidelines are specific and actionable, not generic
- [ ] Examples are provided for complex concepts
- [ ] No conflicting standards between documents
- [ ] Security and performance considerations are included
- [ ] File references are correctly formatted and valid

## Output Structure

Create steering documents in the `.kiro/steering/` directory:

```
.kiro/steering/
├── project-context.md          (always included)
├── backend-rules.md            (always included)
├── frontend-rules.md           (fileMatch: *.tsx,*.jsx)
├── nas-rules.md                (always included — project specific)
└── git-workflow.md             (always included)
```

## Best Practices

### Do:
- Keep documents focused and specific
- Use clear, actionable language
- Include concrete examples
- Reference external specifications with `#[[file:path]]`
- Update regularly as project evolves

### Don't:
- Create overly broad or generic guidelines
- Duplicate information across multiple documents
- Include sensitive information or secrets
- Create conflicting standards

---
*Source: [jasonkneen/kiro](https://github.com/jasonkneen/kiro/tree/main/skills/create-steering-documents) — MIT License*
