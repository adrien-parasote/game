---
name: self-debug
description: Activate when the agent is failing repeatedly, looping on the same tool, burning tokens without progress, or drifting from the intended task. Guides structured self-recovery before escalating to the user.
---

# Agent Self-Debug Skill

Structured self-debugging workflow for agent-level failures. This skill teaches the agent to diagnose and recover from its own execution problems — loops, token burn, context drift, environment mismatches — before burning further context or escalating.

> This skill handles **agent failures**, not code failures.
> Code failures → Golden Rule: fix spec, regenerate.
> Agent failures → this skill: capture, diagnose, recover, report.

## When to Activate

- Maximum tool call / loop-limit reached
- Same tool or command retried 3+ times without progress
- Context growth or prompt drift degrading output quality
- File-system or environment state mismatch (expected file missing, wrong branch, service down)
- Token burn without forward progress (agent "spinning")
- Agent optimizing the wrong subtask (lost the real objective)

## Scope Boundaries

**Use this skill for:**
- Capturing failure state before retrying blindly
- Diagnosing common agent-specific failure patterns
- Applying contained recovery actions
- Producing a structured debug report

**Do NOT use this skill for:**
- Code verification after changes → use `verification-loop`
- Build errors → use `/build-fix`
- Spec-code divergence → use Golden Rule (fix spec, regenerate)
- Framework-specific debugging → use language-specific rules

## Four-Stage Recovery Loop

### Capture — Record the failure precisely

Before attempting recovery, freeze the failure state:

```markdown
## Failure Capture
- Task in progress:
- Goal at time of failure:
- Error (if any):
- Last successful step:
- Last failed tool/command:
- Repeated pattern observed:
- Environment assumptions to verify: (cwd, branch, service state, expected files)
- Context pressure: (repeated prompts, oversized logs, duplicated plans)
```

> **Mantra:** "Document the failure. Don't retry blindly."

### Diagnose — Match the failure to a known pattern

| Pattern | Likely Cause | Check |
|---------|-------------|-------|
| Same command retried 3+ times | Loop or no-exit path | Inspect last N tool calls for repetition |
| Context overflow / degraded reasoning | Unbounded notes, repeated plans, oversized logs | Inspect recent context for duplication and low-signal bulk |
| Service unavailable / timeout | Wrong port, service down, URL stale | Verify service health, URL, port assumptions |
| Rate limit / quota exhaustion | Retry storm or missing backoff | Count repeated calls, inspect retry spacing |
| File missing after write / stale diff | Race, wrong cwd, or branch drift | Re-check path, cwd, `git status`, actual file existence |
| Tests still failing after "fix" | Wrong hypothesis | Isolate the exact failing test and re-derive the bug |
| Agent solving wrong problem | Objective drift | Re-read the original task/spec — is this still the goal? |

**Diagnosis questions (ask yourself):**
1. Is this a logic failure, state failure, environment failure, or **spec failure**?
2. Did I lose the real objective and start optimizing the wrong subtask?
3. Is the failure deterministic or transient?
4. What is the smallest reversible action that would validate the diagnosis?

> **Stream Coding principle:** If the diagnosis reveals a **spec gap**, stop recovery and fix the spec first. The agent failure was a symptom — the spec ambiguity was the cause.

### Recover — Smallest action that changes the diagnosis surface

**Recovery heuristics (apply in order):**

1. **Restate the real objective** in one sentence
2. **Verify the world state** instead of trusting memory (check files, branch, service)
3. **Shrink the failing scope** to one file, one test, one command
4. **Run one discriminating check** that confirms or refutes the diagnosis
5. **Only then retry** — with a changed approach based on evidence

**Safe recovery actions:**
- Stop repeated retries and restate the hypothesis
- Trim low-signal context (keep active goal, blockers, evidence only)
- Re-check actual filesystem / branch / process state
- Narrow the task to one failing command, one file, or one test
- Switch from speculative reasoning to direct observation
- Escalate to the user when failure is high-risk or externally blocked

```markdown
## Recovery Action
- Diagnosis chosen:
- Smallest action taken:
- Why this is safe:
- Evidence that would prove the fix worked:
```

**Anti-pattern:** Retrying the same action 3 times with slightly different wording. That's not recovery — that's praying.

### Report — Structured output for the next action

End with a report that makes the recovery legible:

```markdown
## Agent Self-Debug Report
- Task:
- Failure:
- Root cause:
- Recovery action:
- Result: success | partial | blocked
- Token/time burn estimate:
- Follow-up needed:
- Spec change required: [yes — describe / no]
```

## Integration with Stream Coding

| After recovery... | Then... |
|-------------------|---------|
| Code was changed during recovery | Run `verification-loop` |
| Spec gap was discovered | Fix the spec first (Golden Rule), then regenerate |
| Pattern is worth encoding | Run `/learn-eval` to extract the anti-pattern |
| Build is broken | Run `/build-fix` |
| Agent is still stuck after recovery | **Escalate to user** — do not loop |

## Output Standard

When this skill is active, **never** end with "I fixed it" alone.

Always provide:
- The failure pattern identified
- The root-cause hypothesis
- The recovery action taken
- The evidence that the situation is now better or still blocked

---

**Remember**: The agent looping without recovery is the #1 token burn pattern. This skill exists to break that loop with structure, not hope.
