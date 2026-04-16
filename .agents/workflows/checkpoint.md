---
description: Save points for rollback during development. create/verify/list.
---

# /checkpoint — Save Points

> If execution diverges from the spec, the checkpoint allows returning to a conformant state.

## Commands

### `create <name>`

Create a save point:

1. Verify the build passes
2. Verify tests pass
3. Capture state:
   ```bash
   git add -A
   git commit -m "checkpoint: <name>"
   ```
4. Generate a context snapshot at `.checkpoints/<name>.md` (see format below)
5. Log the checkpoint: modified files, tests passed, coverage

### `verify <name>`

Compare current state with a checkpoint:

1. List files modified since the checkpoint:
   ```bash
   git diff <checkpoint_commit> --stat
   ```
2. Verify that the checkpoint tests still pass
3. Compare coverage: same or better?
4. Report divergences

### `list`

List all checkpoints:

```bash
git log --oneline --grep="checkpoint:"
```

## Context Snapshot Format

When creating a checkpoint, generate `.checkpoints/<name>.md`:

```markdown
# Checkpoint: <name>
**Date:** YYYY-MM-DD HH:mm
**Branch:** <current branch>
**Spec:** <link to the implementation spec>

## What Worked (with evidence)
- **[component/feature]** — confirmed by: [test passed, build OK, manual verification]

## What Did NOT Work (and why)
- **[approach tried]** — failed because: [exact error or reason]

## What Has NOT Been Tried Yet
- [approach still to explore]
- [alternative solution worth considering]

## Current State of Files
| File | Status | Notes |
|------|--------|-------|
| `path/to/file` | ✅ Complete | [what it does] |
| `path/to/file` | 🔄 In Progress | [what's done, what's left] |
| `path/to/file` | 🗒️ Not Started | [planned but not touched] |

## Decisions Made
- **[decision]** — reason: [why this over alternatives]

## Exact Next Step
[The single most important thing to do when resuming.
Precise enough so resuming requires zero thinking about where to start.]
```

## Why the Context Snapshot Matters

The git commit captures **code state**. The context snapshot captures **cognitive state** — what the developer (or AI) knew, tried, and decided. Without it, a resumed session blindly retries failed approaches.

## When to Create a Checkpoint

- [ ] End of each implementation step
- [ ] Before a risky refactoring
- [ ] After a set of tests passes for the first time
- [ ] Before modifying code shared between multiple modules
- [ ] Before hitting context limits (save cognitive state before it's lost)
