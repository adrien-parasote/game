---
description: Structured agent failure recovery. Capture failure state, diagnose pattern, apply minimal recovery, report. Use when looping, burning tokens, or drifting from the task.
---

# /self-debug — Agent Failure Recovery

## When to Use

- Agent is looping (same tool/command retried 3+ times)
- Token burn without forward progress
- Context drift (agent optimizing wrong subtask)
- Environment state mismatch (files missing, wrong branch, service down)
- `/orchestrate` step fails 2+ times consecutively

## Stream Coding Integration

- **Stage:** ⚡ BUILD — escalation path when the Spec-Test-Implement loop is blocked by agent-level failure
- **Skill:** `self-debug` (loaded on activation)
- **Not for:** Code bugs (→ fix spec), Build errors (→ `/build-fix`), Spec gaps (→ Spec Gate)

## Process

### 1. Detect (automatic or manual)

Triggers:
- Same tool call repeated 3+ times → automatic escalation
- User invokes `/self-debug` → manual escalation
- `/orchestrate` detects step failure 2+ times → suggests `/self-debug`

### 2. Capture

Freeze the failure state before attempting recovery:

```markdown
## Failure Capture
- Task in progress:
- Goal at time of failure:
- Error:
- Last successful step:
- Last failed tool/command:
- Repeated pattern observed:
- Environment assumptions to verify:
```

### 3. Diagnose

Match to known patterns:

| Pattern | Likely Cause | First Check |
|---------|-------------|-------------|
| Tool loop | No-exit path | List last 5 tool calls |
| Context overflow | Unbounded context growth | Check for duplicated plans/logs |
| File state mismatch | Wrong cwd or branch | `git status`, `ls` the expected path |
| Service down | Process not running | Health check the expected URL/port |
| Wrong hypothesis | Spec misread or assumption | Re-read the spec section for this task |

**Key question:** Is this an **agent** failure or a **spec** failure?
- If spec failure → stop `/self-debug`, fix the spec (Golden Rule)
- If agent failure → continue to recovery

### 4. Recover

Apply the smallest action that changes the diagnosis surface:

1. Restate the objective in one sentence
2. Verify the world state (don't trust memory)
3. Shrink scope to one file/test/command
4. Run one discriminating check
5. Only then retry

### 5. Report

```markdown
## Self-Debug Report
- Failure: [pattern name]
- Root cause: [diagnosis]
- Recovery action: [what was done]
- Result: success | partial | blocked
- Spec change needed: [yes/no — if yes, describe]
- Follow-up: [next action]
```

## Escalation

If recovery does not resolve the issue after **one cycle** (Capture → Diagnose → Recover):
- **Do NOT loop.** Repeating recovery is the same anti-pattern as repeating the original failure.
- **Escalate to the user** with the Self-Debug Report
- Let the user decide: change approach, change scope, or abandon the task

## Checklist

- [ ] Failure state captured (not just "it failed")
- [ ] Pattern matched from diagnosis table
- [ ] Spec-vs-agent failure classification made
- [ ] Recovery action is the **smallest** possible (not "try everything")
- [ ] Report produced with evidence
- [ ] If blocked: escalated to user (not looped)
