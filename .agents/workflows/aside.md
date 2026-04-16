---
description: Answer a quick side question without interrupting or losing context from the current task. Resume work automatically after answering.
---

# /aside — Side Question Without Context Loss

Ask a question mid-task and get an immediate, focused answer — then continue right where you left off. The current task, files, and context are never modified.

## When to Use

- You need a quick explanation while the AI is working on a task
- You want a second opinion or clarification without derailing the task
- You need to understand an error, concept, or pattern before proceeding
- You want to ask something unrelated without starting a new conversation

## Process

### 1. Freeze the current task state

Before answering, mentally note:
- What is the active task?
- What step was in progress when `/aside` was invoked?
- What was about to happen next?

**Do NOT touch, edit, create, or delete any files during the aside.**

### 2. Answer the question directly

- Lead with the answer, not the reasoning
- Keep it short — offer to go deeper after the task if needed
- If about the current file, reference file path and line number
- If answering requires reading a file, read it — but read only, never write

Format:

```
ASIDE: [restate the question briefly]

[Your answer here]

— Back to task: [one-line description of what was being done]
```

### 3. Resume the main task

After delivering the answer, immediately continue the active task from the exact point it was paused. Do not ask for permission to resume unless the aside revealed a blocker.

## Edge Cases

**Aside reveals a problem with the current task:**
```
ASIDE: [answer]

⚠️ Note: This suggests [issue] with the current approach.
Want to address this before continuing, or proceed as planned?
```
Wait for the user's decision before resuming.

**Question is actually a task redirect:**
```
ASIDE: That sounds like a direction change, not a side question.
Do you want to:
  (a) Answer this as information only and keep the current plan
  (b) Pause the current task and change approach
```

**No active task:**
```
ASIDE: [answer]

— Back to task: no active task to resume
```

**Question requires a long answer:**
Give the essential answer concisely, then offer:
```
That's the short version. Want a deeper explanation after we finish [current task]?
```
