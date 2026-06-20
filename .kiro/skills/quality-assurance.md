---
name: quality-assurance
description: Comprehensive testing and validation strategies for spec-driven development. Learn phase-specific validation techniques, quality gates, and testing approaches to ensure high-quality implementation.
license: MIT
compatibility: Kiro, Claude Code, Cursor, VS Code, Windsurf
metadata:
  category: methodology
  complexity: intermediate
  author: Kiro Team
  version: "1.0.0"
---

# Quality Assurance

Ensure quality throughout the spec-driven development process with validation techniques, quality gates, and testing strategies.

## When to Use This Skill

Use quality assurance practices when:
- Completing any spec phase (requirements, design, tasks)
- Reviewing completed implementation
- Establishing team quality standards
- Setting up CI/CD quality gates

## Core Principles

1. **Requirements-Driven Testing:** Every test traces to a requirement
2. **Phase-Appropriate Validation:** Different techniques for each phase
3. **Continuous Quality:** Checks throughout development
4. **Fast Feedback:** Catch issues early

## Test Pyramid for SecondBrain

```
       /\
      /  \     E2E / QA Manual (qa/questions.md checklist)
     /____\    Integration Tests (need PostgreSQL + Redis)
    /      \
   /________\   Unit Tests (no Docker needed — run first)
```

## Phase-Specific Validation

### Requirements Phase
- [ ] All user stories have acceptance criteria
- [ ] Requirements are unambiguous and specific
- [ ] Each requirement can be validated/tested
- [ ] No conflicting requirements

### Design Phase
- [ ] Design addresses all requirements
- [ ] Scalability considerations documented
- [ ] Security addressed
- [ ] External integrations defined

### Tasks Phase
- [ ] Each task has clear deliverables
- [ ] Task sequence is logical
- [ ] All design elements covered
- [ ] Tasks appropriately sized (2-4 hours)
- [ ] Dependencies clearly defined

## Quality Gates

### Task-Level Quality Gates

**Before Starting:**
- [ ] Task requirements understood
- [ ] Test strategy defined
- [ ] Dependencies available

**During Implementation:**
- [ ] Code follows backend-rules / frontend-rules conventions
- [ ] schemas/ = Pydantic only, models/ = SQLAlchemy only
- [ ] Component → Hook → api/ chain respected in frontend
- [ ] Tests written alongside code

**Before Marking Complete:**
- [ ] All unit tests pass: `pytest tests/unit/ -v`
- [ ] Code review completed
- [ ] Documentation updated

## Testing Strategies

### Unit Testing (No Docker)
- Fast execution (< 1 second per test)
- Mock external dependencies (LightRAG, Graphiti, PostgreSQL)
- Target 80%+ coverage for services/ and schemas/
- Run: `pytest tests/unit/ -v`

### Integration Testing (PostgreSQL + Redis)
- Test with real DB — use `docker-compose.test.yml`
- Validate DB migrations: `alembic upgrade head`
- Test CRUD operations with real data
- Run: `docker compose -f tests/docker-compose.test.yml up -d && pytest tests/integration/`

### E2E / QA Manual
- Full stack running: `docker compose up -d`
- Follow checklist in `tests/qa/questions.md`
- 20 domain-specific questions covering Chat, Wiki, NAS Sync, MCP
- Rate answers 1-5, track quality over time

## Validation Checklists

### Implementation Validation
```markdown
## Implementation Review

**Code Quality:**
- [ ] Follows backend-rules / frontend-rules conventions
- [ ] Well-documented
- [ ] Tests included in tests/unit/
- [ ] No hardcoded secrets or config

**Requirements:**
- [ ] All pa3-design requirements met
- [ ] Edge cases handled
- [ ] Error handling complete

**Integration:**
- [ ] Works with existing code
- [ ] APIs functioning per schemas/
- [ ] Performance acceptable
```

## Best Practices

1. Write unit tests first when possible
2. Each test verifies one thing
3. Use descriptive test names: `test_nas_file_transitions_to_indexed_after_approval`
4. Maintain test independence — no shared state between tests
5. Keep `tests/qa/questions.md` updated as new tài liệu Robolinks is indexed

---
*Source: [jasonkneen/kiro](https://github.com/jasonkneen/kiro/tree/main/skills/quality-assurance) — MIT License*
