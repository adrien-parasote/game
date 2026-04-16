---
name: refactor-cleaner
description: Activate during codebase maintenance, after removing a feature or module, or when dependencies are suspected unused. Guides dead code detection and removal with SAFE/CAREFUL/RISKY categorization.
---

# Refactor & Cleanup Skill

Auto-activated when dead code or maintenance context is detected. Guides the developer through systematic cleanup using the `/refactor-clean` workflow.

## When to Activate

- Codebase maintenance tasks
- After removing a feature or module
- When dependencies are suspected unused
- During Phase 4 Quality & Iteration

## What This Skill Does

1. **Detect** dead code patterns in the current context (unused imports, unreferenced exports, orphaned files)
2. **Suggest** running `/refactor-clean` workflow for systematic cleanup
3. **Enforce** the Rule of Divergence: after cleanup → update the spec if the code surface changed
4. **Categorize** removals by risk level (SAFE/CAREFUL/RISKY) before any deletion

## Stream Coding Principle

> After cleanup → update the spec if the code surface changed (Rule of Divergence).
> If a refactor reveals a gap in the spec → fix the spec first.

## Quick Reference

| Need | Where |
|------|-------|
| Full cleanup procedure | `/refactor-clean` workflow |
| Risk categorization (SAFE/CAREFUL/RISKY) | `/refactor-clean` → "Catégoriser le risque" |
| Detection tools by language | `/refactor-clean` → "Détection" |
| Safety checklist before deletion | `/refactor-clean` → "Checklist de sécurité" |

## Refactoring Principles

### Chesterton's Fence — Understand before removing

> If you find code that seems useless, assume someone put it there for a reason. **Understand WHY before deleting.**

Before removing any code, answer:

| # | Question | If you can't answer → |
|---|----------|-----------------------|
| 1 | **Why does this code exist?** | Read git blame, commit messages, PR descriptions |
| 2 | **What breaks if I remove it?** | Check dependents, search for usage across the codebase |
| 3 | **Is this a workaround?** | Look for comments like `// HACK`, `// workaround for`, linked issues |
| 4 | **Is this tested?** | If tests exist for it, it was important enough to test |

```
⛔ NEVER delete code you don't understand.

If you can't answer all 4 questions:
→ Mark as CAREFUL or RISKY (not SAFE)
→ Ask the user before removing
```

### Strangler Fig — Incremental replacement, not big-bang

> Replace old code incrementally: build new alongside old, migrate callers one by one, remove old only when unused.

**Why:** Big-bang refactors are the #1 cause of regressions. They're especially dangerous with AI — the AI regenerates everything from scratch and loses edge cases the original handled.

```
WRONG (Big-bang):
  1. Delete old module
  2. Write new module
  3. Fix everything that breaks (usually many things)

RIGHT (Strangler Fig):
  1. Build new module alongside old
  2. Migrate ONE caller at a time
  3. Verify each migration with tests
  4. Remove old module only when zero callers remain
```

**When to use Strangler Fig:**
- Replacing a module with > 3 callers
- Changing a shared interface or data model
- Migrating to a new library or pattern

**When big-bang is OK:**
- Module has 0-1 callers (isolated)
- You have strong test coverage on ALL callers
- The change is purely internal (no API surface change)

---

**Remember**: Clean code serves the spec. If the spec doesn't mention it, ask whether it should be there.
