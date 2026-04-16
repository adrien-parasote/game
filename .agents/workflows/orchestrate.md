---
description: Multi-step pipeline for complex tasks. Chains plan, tdd, review, security in sequence with structured handoffs.
---

# /orchestrate — Multi-Step Pipeline

## When to Use

This workflow orchestrates multiple steps in sequence for complex tasks requiring planning, implementation, review, and verification.

## Stream Coding Integration

- **Stage:** ⚡ BUILD — structures the Generate-Verify-Integrate loop
- **Golden rule:** If code diverges from spec → fix the spec, not the code
- **Each handoff** MUST reference the source spec

## Workflow Types

| Type | Pipeline | Use Case |
|------|----------|----------|
| `feature` | plan → tdd → review → security | New feature |
| `bugfix` | diagnose → tdd → fix → review | Bug fix |
| `refactor` | analyze → plan → refactor → review | Refactoring |
| `security` | audit → plan → fix → verify | Security fix |

## Process

### 1. Select the type

```
/orchestrate feature "Feature description"
/orchestrate bugfix "Bug description"
```

### 2. Run each step

**Step: Plan**
- If `docs/CODEMAPS/` exists, read all `.md` files in it to scope the affected modules
- Run `/plan` or `/strategy` depending on complexity
- **Output:** Implementation plan conforming to the spec
- **Gate:** Plan validated before continuing

**Step: TDD (if applicable)**
- Run `/tdd` to write tests first
- **Output:** RED tests defining expected behavior
- **Gate:** Tests written and runnable (they fail — that is expected)

**Step: Review**
- Run `/code-review` to verify spec-to-code conformance
- **Output:** Conformance report
- **Gate:** Zero CRITICAL, all HIGH addressed

**Step: Security (if applicable)**
- Run `/security-review` for security audit
- **Output:** Security report
- **Gate:** Zero CRITICAL security issues

### 3. Handoff Document Format

Between each step, produce a handoff document:

```markdown
## Handoff: [Step N] → [Step N+1]

**Spec source:** [link to the spec]
**Step completed:** [step name]
**Status:** [PASS / PASS WITH NOTES / BLOCKED]

### Result
- [summary of actions performed]

### Open Issues
- [unresolved issues for the next step]

### Context for Next Step
- [information needed to continue]
```

### 4. Final Report

```
ORCHESTRATION REPORT
====================

Type:        [feature/bugfix/refactor/security]
Spec:        [reference to source spec]
Steps:       [N/N completed]

Plan:        [PASS/FAIL]
TDD:         [PASS/FAIL] (X tests, Y% coverage)
Review:      [PASS/FAIL] (X findings)
Security:    [PASS/FAIL] (X issues)

Recommendation: [SHIP / NEEDS WORK / BLOCKED]

Spec Conformance: [✅ Code matches spec / ⚠️ Divergence detected]
```

## Parallel Execution

- Review and Security can run in parallel (no dependency)
- Plan and TDD are sequential (TDD depends on the plan)
- NEVER skip the Plan step

### 5. Synthesis Obligation

When a research step completes, you MUST synthesize before delegating follow-up work.

**Anti-pattern (lazy delegation):**
> "Based on your findings, fix the auth bug"
> "The research found an issue. Please fix it."

**Required pattern (synthesized spec):**
> "Fix the null pointer in src/auth/validate.ts:42. The user field on Session is
> undefined when sessions expire but the token remains cached. Add a null check
> before user.id access — if null, return 401 with 'Session expired'."

A well-synthesized handoff gives ALL specifics: file paths, line numbers, exact behavior expected. If you write "based on your findings" or "based on the research", you have failed to synthesize.

### 6. Subagent Context Reuse

When using `browser_subagent`, decide whether to reuse a previous subagent's context (`ReusedSubagentId`) or start fresh:

| Situation | Decision | Why |
|-----------|----------|-----|
| Previous subagent navigated to the exact page needed | **Reuse** | Page state already loaded |
| Previous subagent was exploring broadly | **Fresh** | Avoid noise from unrelated pages |
| Correcting a failed browser interaction | **Reuse** | Error context helps debug |
| Verifying a different page or flow | **Fresh** | Clean state avoids interference |

### 7. Parallel Tool Calls

In Antigravity, parallelism means issuing multiple tool calls in a single turn (not multi-agent workers).

| Task Type | Execution | How |
|-----------|-----------|-----|
| Reading multiple files | **Parallel** | Multiple `view_file` / `grep_search` in one turn |
| Running independent commands | **Parallel** | Multiple `run_command` in one turn |
| File edits | **Sequential** | One edit tool per file at a time |
| Research + file reading | **Parallel** | `search_web` + `view_file` in one turn |

**Maximize parallelism on research.** Issue all independent reads and searches in a single turn.

When using `browser_subagent`, always include a purpose statement in the Task:
- "This research will inform a PR description — focus on user-facing changes."
- "I need this to plan an implementation — report file paths, line numbers, and type signatures."
- "This is a quick check before we merge — just verify the happy path."

