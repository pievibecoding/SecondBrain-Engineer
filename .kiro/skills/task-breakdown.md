---
name: task-breakdown
description: Convert technical designs into actionable, sequenced implementation tasks. Create clear coding tasks that enable incremental progress, respect dependencies, and provide a roadmap for systematic feature development.
license: MIT
compatibility: Kiro, Claude Code, Cursor, VS Code, Windsurf
metadata:
  category: methodology
  complexity: intermediate
  author: Kiro Team
  version: "1.0.0"
---

# Task Breakdown

Transform designs into actionable implementation plans. Use this skill to convert pa3-design.md sections into concrete, sequenced coding tasks.

## When to Use This Skill

Use task breakdown when:
- Design phase is complete and approved
- Ready to begin implementation of a module
- Need to coordinate work across team
- Want to track incremental progress
- Planning sprint work assignments

## Task Structure

### Two-Level Hierarchy

```markdown
- [ ] 1. [Epic/Major Component]
- [ ] 1.1 [Specific implementation task]
  - [Implementation details]
  - [Files/components to create]
  - _Requirements: [Requirement references]_
- [ ] 1.2 [Next specific task]
  - [Details]
  - _Requirements: [References]_

- [ ] 2. [Next Epic/Major Component]
- [ ] 2.1 [Specific task]
```

## Step-by-Step Process

### Step 1: Analyze Design Components

Identify all implementation needs from the design doc:
- Data models and validation (schemas/ + models/)
- Services and business logic (services/)
- External integrations (integrations/)
- API endpoints and handlers (routers/)
- UI components (frontend/components/)
- Tests for each layer (tests/)

### Step 2: Identify Dependencies

Map what needs to be built first:
- **Technical:** Code dependencies (models before services, services before routers)
- **Logical:** Feature dependencies (auth before any protected endpoint)
- **Data:** What data must exist first (DB schema before ORM models)

### Step 3: Sequence Tasks — Recommended: Hybrid Strategy

```
1. Minimal foundation (schemas, models, DB setup)
2. High-risk/high-value feature slice (e.g., auth, core ingestion)
3. Expand foundation as needed
4. Additional feature slices
5. Integration and polish
```

### Step 4: Write Task Descriptions

```markdown
- [ ] X.Y [Task Title]
  - [What to implement]
  - [Files to create/modify — be specific: backend/schemas/chat.py]
  - [Key functionality]
  - [Tests to write: tests/unit/backend/test_xxx.py]
  - _Requirements: [pa3-design section reference]_
```

## Task Scope Guidelines

**Appropriate:** 2-4 hours of focused work

**Too Large:**
```markdown
- [ ] 1.1 Implement complete NAS connector system
```

**Just Right:**
```markdown
- [ ] 1.1 Create NasFile SQLAlchemy model with state machine
  - Create backend/models/nas_file.py
  - Fields: nas_path, status, file_hash, lightrag_doc_id, approved_by
  - Status enum: DETECTED, PENDING_REVIEW, QUEUED, INDEXING, INDEXED, FAILED, REJECTED
  - Write tests/unit/backend/test_models.py::test_nas_file_states
  - _Requirements: pa3-design Section 4, NasFile state machine_
```

## Complete Example — SecondBrain Module

```markdown
# Implementation Plan: Backend Auth Module

- [ ] 1. Set up auth foundation
- [ ] 1.1 Create auth schemas (Pydantic)
  - Create backend/schemas/auth.py
  - LoginRequest, TokenResponse, UserResponse
  - Write tests/unit/backend/test_schemas.py::test_auth_schemas
  - _Requirements: pa3-design Section 8 API contracts_

- [ ] 1.2 Create User SQLAlchemy model
  - Create backend/models/user.py
  - Fields: id (UUID), email, role (user/admin), password_hash, created_at
  - Write tests/unit/backend/test_models.py::test_user_model
  - _Requirements: pa3-design Section 7 Data model_

- [ ] 2. Implement auth service
- [ ] 2.1 Create auth_service.py
  - Implement JWT create/verify (python-jose)
  - Implement bcrypt hash/verify
  - Write tests/unit/backend/test_auth_service.py
  - _Requirements: pa3-design Section 4 backend/services/_
```

## Quality Checklist

Before finalizing tasks:

**Completeness:**
- [ ] All design components have tasks
- [ ] All pa3-design sections addressed
- [ ] Testing tasks included throughout
- [ ] Integration tasks connect components

**Clarity:**
- [ ] Each task has specific file paths
- [ ] Requirements reference pa3-design section
- [ ] Completion criteria clear

**Sequencing:**
- [ ] Foundation (schemas, models) before features
- [ ] Services before routers
- [ ] Backend before frontend

---
*Source: [jasonkneen/kiro](https://github.com/jasonkneen/kiro/tree/main/skills/task-breakdown) — MIT License*
