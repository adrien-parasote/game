---
name: architect
description: Activate when making architectural decisions, designing system components, evaluating trade-offs between technologies, or when an ADR needs to be created. Guides structured analysis and ADR documentation.
---

# System Architect Skill

Guides architectural decisions with structured analysis, trade-off evaluation, and ADR documentation.

## When to Activate

- Architectural decisions (database choice, framework selection, service boundaries)
- System design (new modules, API design, data flow)
- Trade-off evaluation (performance vs maintainability, consistency vs availability)
- Technology selection with business rationale

## Stream Coding Principle

> Phase 1 Strategic Thinking, Question 4: "What's the core architecture decision?"
> Architecture decisions must be HUMAN decisions based on explicit trade-off analysis.
> Never let the AI choose architecture — the AI documents the options, the human decides.

## Architecture Principles

| Principle | Meaning |
|-----------|---------|
| **Modularity** | Components can be understood, changed, and tested independently |
| **Scalability** | Design for 10x current load without rewrite |
| **Maintainability** | New team members can understand in < 1 day |
| **Security** | Zero trust at every boundary |
| **Performance** | Set explicit latency/throughput targets, measure |

## Decision Process

### 1. Identify the Decision

What specific architectural choice needs to be made? Frame as a question:
- "Should we use a relational or document database?"
- "Should this be a monolith or microservices?"
- "Should auth be custom or delegated?"

### 2. Evaluate Options

For each option:

| Criteria | Option A | Option B | Option C |
|----------|----------|----------|----------|
| Team expertise | | | |
| Time to implement | | | |
| Scalability | | | |
| Maintenance cost | | | |
| Risk | | | |

### 3. Document as ADR

Use the ADR template (`.agents/templates/ADR_TEMPLATE.md`):
- Status, Context, Decision, Consequences
- Trade-offs explicitly stated
- Reversibility assessed

## Common Patterns

| Domain | Pattern | When |
|--------|---------|------|
| **API** | REST with OpenAPI spec | CRUD-heavy, public API |
| **API** | GraphQL | Complex relations, mobile clients |
| **Data** | PostgreSQL | Structured data, transactions |
| **Data** | Redis | Cache, sessions, real-time |
| **Auth** | OAuth2 / OIDC | Delegated auth, SSO |
| **Messaging** | Event-driven | Async processing, decoupling |

## Red Flags (Anti-Patterns)

- ❌ Choosing technology because it's trendy
- ❌ Premature microservices (start monolith, extract later)
- ❌ No defined API contract before implementation
- ❌ Shared mutable state between services
- ❌ Architecture decision without ADR

---

**Remember**: Architecture is about trade-offs, not perfection. Document WHY you chose each trade-off in an ADR.
