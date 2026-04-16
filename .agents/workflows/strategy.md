---
description: Clarify the WHAT and WHY before the HOW.
---

# /strategy — 🎯 STRATEGY: Strategic Thinking

Use this to define the project foundations through the "7 Questions" framework.

## Pre-step: Load past learnings

Before answering the 7 Questions, check for existing learnings that could inform this spec:

1. If `.agents/learnings.md` exists, read it — look for universal patterns and anti-patterns relevant to this domain
2. If the project has an existing spec with an Anti-Patterns section, read that too
3. Note any relevant patterns to carry into the spec you're about to write

> **Why:** Learnings from `/learn-eval` are useless if they're never read back. This step closes the feedback loop.

## The 7 Questions

| # | Question | Required level of detail |
|---|----------|--------------------------|
| 1 | What exact problem are you solving? | Specific persona + measurable outcome. |
| 2 | What are your success metrics? | Numbers + timeline (e.g. 25% conversion). |
| 3 | Why will you win? | Architecture, data moat, or structural advantage. |
| 4 | What's the core architecture decision? | Human-made trade-off analysis. |
| 5 | What's the tech stack rationale? | Business-aligned (e.g. "team expertise"). |
| 6 | What are the MVP features? | 3-5 essentials, rest deferred. |
| 7 | What are you NOT building? | Explicit exclusions with rationale. |

## Actions
- Answer all 7 questions.
- Create `docs/strategic/blueprint.md`.
- Create Architecture Decision Records (ADRs) in `docs/ADRs/` for major choices.
