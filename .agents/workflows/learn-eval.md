---
description: Extract spec patterns after BUILD→HARDEN. Captures what worked, what caused rework, and feeds learnings back into future specs. The missing workflow for HARDEN's Continuous Learning.
---

# /learn-eval — Spec Pattern Extraction

> **Stream Coding principle:** "What improves is the quality of specs, not the quality of code. Code follows automatically."
> This workflow IS the mechanism for that improvement.

## When to Use

- After completing a BUILD→HARDEN cycle
- After a spec caused unexpected rework
- After a spec produced perfect code on first pass (capture the pattern)
- Periodically to consolidate learnings across multiple features

## Stream Coding Integration

- **Stage:** ✅ HARDEN — Continuous Learning (execution.md, lines 79-99)
- **Input:** The spec, the generated code, and the review/verification results
- **Output:** Documented spec pattern or anti-pattern, optionally strengthened Spec Gate

## Process

### 1. Classify the outcome

Evaluate how the spec performed during BUILD:

| Outcome | Signal | Action |
|---------|--------|--------|
| **Perfect first pass** | Code matches spec, zero rework, all tests pass | Extract the PATTERN to reproduce |
| **Minor rework** | 1-2 clarifications needed, small fixes | Extract the AMBIGUITY that caused it |
| **Major rework** | Significant divergence, code rewritten | Extract the GAP and strengthen Spec Gate |
| **Spec was wrong** | Spec needed fundamental correction | Extract the ASSUMPTION that failed |

### 2. Extract the learning

For each outcome, capture a structured learning:

```markdown
## Learning: [short title]

**Date:** YYYY-MM-DD
**Spec:** [link to the spec that produced this learning]
**Outcome:** [Perfect / Minor Rework / Major Rework / Spec Wrong]
**Project:** [project name or path]

### What happened
[1-2 sentences: what the spec asked for, what the code did]

### Root cause
[The specific spec pattern or gap that caused the outcome]

### Pattern (what to reproduce)
[If outcome was Perfect: the exact spec structure/language that worked]

### Anti-pattern (what to avoid)
[If outcome was Rework/Wrong: the exact ambiguity or assumption]

### Evidence
- [Test result, review finding, or code diff that proves this]

### Scope
- [ ] Project-specific (applies only to this codebase)
- [ ] Universal (applies across projects)
```

### 3. Quality gate

Before saving, apply this checklist:

| Check | Question | If NO → |
|-------|----------|---------|
| **Actionable** | Can this learning change a future spec? | Drop — it's an observation, not a pattern |
| **Specific** | Does it name the exact spec structure that worked/failed? | Improve — vague learnings are useless |
| **Evidence-backed** | Is there a concrete test/review/diff proving it? | Improve — anecdotal = unreliable |
| **Non-duplicate** | Is this genuinely new, not already in an existing anti-pattern? | Absorb — merge into existing |
| **Scoped** | Is the project vs universal scope correctly identified? | Fix scope before saving |

**Verdict:**

| Verdict | Action |
|---------|--------|
| **SAVE** | All checks pass → save to the project's anti-patterns or patterns doc |
| **IMPROVE** | 1-2 checks fail → refine the learning, re-evaluate |
| **ABSORB** | Duplicate → merge into existing pattern/anti-pattern |
| **DROP** | Not actionable or not evidence-backed → discard |

### 4. Integrate the learning

Based on the verdict:

**If SAVE (Pattern to reproduce):**
- **Project-specific:** Add to the relevant implementation spec's Anti-Patterns section as a "✅ Pattern to reproduce"
- **Universal:** Add to `.agents/learnings.md` (the cross-project learning registry)
- If it's a coding standard: also add to `.agents/rules/coding-standards.md`

**If SAVE (Anti-pattern to avoid):**
- **Project-specific:** Add to the relevant implementation spec's Anti-Patterns section as a "❌ Don't"
- **Universal:** Add to `.agents/learnings.md`
- If it's a recurring pattern (seen 2+ times): strengthen the Spec Gate
  - Add a new check to `.agents/rules/spec-gate-rule.md`
  - Or add a question to the Spec Gate's self-assessment

**If ABSORB:**
- Find the existing pattern/anti-pattern in `.agents/learnings.md` or the project spec and merge the new evidence into it
- Increase confidence if the same pattern is confirmed again

### 5. Gate strengthening (if recurring)

When the same type of rework appears 2+ times:

1. Identify the common ambiguity class (e.g., "error handling not specified", "API response format assumed")
2. Add a new Foundation Check or Document Architecture Check to the Spec Gate
3. Add a new self-assessment question to the adversarial review

```markdown
## Spec Gate Addition

**New check:** [description]
**Trigger:** This ambiguity caused rework in [spec1], [spec2]
**Question:** [the question to add to the Spec Gate checklist]
```

## Output

```
LEARN-EVAL REPORT
=================

Spec evaluated:     [reference]
Outcome:            [Perfect / Minor Rework / Major Rework / Spec Wrong]

Learnings extracted: N
  - Patterns:        N (to reproduce)
  - Anti-patterns:   N (to avoid)

Quality gate:
  - SAVE:     N
  - IMPROVE:  N
  - ABSORB:   N
  - DROP:     N

Gate strengthened:   [Yes — added check X / No]

Integrated into:
  - [doc1.md] — added pattern: [title]
  - [doc2.md] — added anti-pattern: [title]
```

## Anti-Patterns for This Workflow

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Save every observation as a learning | Apply the quality gate first | Knowledge bloat makes patterns unfindable |
| Write vague learnings ("be more specific") | Name the exact spec structure | Vague = not reproducible |
| Skip evidence | Always link to the test/review/diff | Anecdotal learnings decay |
| Save project patterns as universal | Check scope carefully | React patterns don't apply to Terraform |
| Only extract from failures | Also extract from perfect first passes | You need the positive patterns too |
