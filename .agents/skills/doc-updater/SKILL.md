---
name: doc-updater
description: Activate after adding new features, changing APIs, modifying architecture, or after refactoring. Ensures documentation stays synchronized with code through drift detection and spec updates.
---

# Doc Updater Skill

Ensures documentation stays in sync with code changes. The most critical skill for Stream Coding methodology.

## When to Activate

- After implementing a new feature
- After modifying API endpoints or types
- After architectural changes
- After refactoring or cleanup
- When a code review flags spec/code divergence

## Stream Coding Principle

> *"Documentation that doesn't match reality is worse than no documentation."*
> The spec is the source of truth. Code is generated FROM the spec.
> Every undocumented code change creates divergence debt.

## Drift Detection

Check for these signals:

1. **Recent code changes** — `git diff --name-only HEAD~5`
2. **New/modified exports** — have public APIs changed?
3. **New dependencies** — added but not documented?
4. **New/modified routes** — API surface changed?
5. **Architecture changes** — new modules, reorganization?

## Update Process

For each drift detected:

1. **Identify the spec** — which specification document is affected?
2. **Update the spec** — the spec is the source of truth, not the code
3. **Verify consistency** — is the updated spec self-consistent?
4. **Timestamp** — add a last-updated marker

## Quality Checklist

- [ ] All file paths referenced in docs exist
- [ ] Code examples compile/execute
- [ ] Internal links point to existing sections
- [ ] No orphaned sections
- [ ] Anti-patterns list still relevant
- [ ] Test cases match current behavior
- [ ] If `docs/CODEMAPS/` exists, codemaps are still accurate (run `/update-codemaps` if modules, routes, or dependencies changed)

## Codemap Generation (Large Projects)

For projects with 10+ modules, maintain a codemap:

```markdown
## Codemap — [Project Name]

**Last Updated:** [date]

| Module | Path | Responsibility | Dependencies |
|--------|------|----------------|-------------|
| [name] | [path] | [description] | [dependent modules] |
```

---

**Remember**: Every time you change code without updating the spec, you create divergence. Divergence is technical debt.
