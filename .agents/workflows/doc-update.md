---
description: Documentation-to-code synchronization. Detects spec/code drift, updates docs, verifies links. Enforces the Rule of Divergence.
---

# /doc-update — Documentation Synchronization

## When to Use

- After any code change that alters the API surface or architecture
- After a refactoring
- During ✅ HARDEN — regular maintenance
- When a `/code-review` flags a spec-to-code divergence

## Stream Coding Integration

- **Stage:** ✅ HARDEN — This is THE most critical workflow in Stream Coding
- **Core principle:** *"Documentation that doesn't match reality is worse than no documentation"*
- **Rule of Divergence:** Every time code is modified without updating the spec, you create debt. This workflow eliminates it.

## Process

### 1. Detect drift

```markdown
## Drift Detection Checklist

- [ ] Do recently modified files (`git diff --name-only HEAD~5`) have associated docs?
- [ ] Have public exports changed? (new functions, removed functions)
- [ ] Have types/interfaces evolved?
- [ ] Were new dependencies added?
- [ ] Were API routes added/modified/removed?
- [ ] Has the architecture changed? (new modules, reorganization)
```

### 2. Update

For each detected drift:

1. **Identify the source doc** — which spec document is affected?
2. **Update the spec** — not the code. The spec is the source of truth.
3. **Verify consistency** — is the updated spec still self-consistent?
4. **Timestamp** — add a last-updated timestamp

### 3. Validation

```markdown
## Documentation Quality Checklist

- [ ] All referenced file paths exist
- [ ] Code examples compile/run
- [ ] Internal links point to existing sections
- [ ] No orphaned sections (referenced nowhere)
- [ ] Version numbers are correct
- [ ] Listed anti-patterns are still relevant
- [ ] Test cases match current behavior
```

### 4. Codemap (for large projects)

Generate a module index for the project:

```markdown
## Codemap — [Project Name]

**Last updated:** [date]

### Structure
| Module | Path | Responsibility | Dependencies |
|--------|------|----------------|--------------|
| [name] | [path] | [description] | [dependent modules] |

### Entry Points
| Endpoint/Route | File | Description |
|----------------|------|-------------|
| [route] | [path] | [description] |
```

## Output

```
DOC-UPDATE REPORT
=================

Files changed since last update: X
Docs affected: X
Drifts detected: X
Drifts fixed: X

Updated Documents:
- [doc1.md] — [change description]
- [doc2.md] — [change description]

Remaining Drifts: [0 / list]
```

## Recommended Frequency

| Context | Frequency |
|---------|-----------|
| After each feature | Immediate |
| Maintenance | 1x per week |
| Post-refactoring | Immediate |
| Before release | Mandatory |
