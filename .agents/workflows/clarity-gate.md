---
description: Epistemic quality verification for specs and docs. Ensures claims are properly qualified before AI execution. Run after /spec-gate, before or alongside /adversarial-review.
---

# /clarity-gate — 📋 SPEC: Epistemic Quality Verification

> "Detection finds what is; enforcement ensures what should be."

## Purpose

Spec Gate verifies **structural** quality (can AI execute this?).
Adversarial Review verifies **logical** quality (will an attacker find flaws?).
Clarity Gate verifies **epistemic** quality (are claims properly qualified?).

**Core Question:** "If an AI agent reads this spec, will it mistake assumptions for facts?"

## When to Run

- After `/spec-gate` passes (10/10)
- Before or alongside `/adversarial-review`
- On any spec containing: projections, estimates, benchmarks, performance targets, pricing, or competitor claims

## The 9 Verification Points

### Epistemic Checks (Points 1–4) — CRITICAL

| # | Check | Fails | Passes |
|---|-------|-------|--------|
| 1 | **Hypothesis vs Fact** | "Our architecture outperforms competitors" | "Our architecture outperforms competitors [benchmark in Table 3]" |
| 2 | **Uncertainty Markers** | "Revenue will be $50M by Q4" | "Revenue is **projected** to be $50M by Q4" |
| 3 | **Assumption Visibility** | "The system scales linearly" | "The system scales linearly [assuming <1000 concurrent users]" |
| 4 | **Authoritative Unvalidated Data** | Tables with 89%, 95% without sources | Add "(est.)", "(projected)", or source citations |

### Data Quality Checks (Points 5–7) — WARNING

| # | Check | Red Flag | Fix |
|---|-------|----------|-----|
| 5 | **Data Consistency** | "500 users" in one section, "750" in another | Reconcile or explicitly note discrepancy |
| 6 | **Implicit Causation** | "Shorter prompts improve quality" | Reframe: "MAY improve (hypothesis, not validated)" |
| 7 | **Future State as Present** | "Processes 10K rps" (not built yet) | "DESIGNED TO process 10K rps" or "TARGET: 10K rps" |

### Verification Routing (Points 8–9) — FLAG

| # | Check | Red Flag | Fix |
|---|-------|----------|-----|
| 8 | **Temporal Coherence** | Dates inconsistent or stale | Update dates, add "as of [date]" qualifiers |
| 9 | **Externally Verifiable Claims** | Specific pricing, stats, competitor claims | Add source+date, uncertainty marker, or generalize |

## Quick Scan Patterns

| Pattern | Action |
|---------|--------|
| Specific percentages (89%, 73%) | Add source or mark as estimate |
| Comparison tables | Add "PROJECTED" header if not measured |
| "Achieves", "delivers", "provides" | Use "designed to", "intended to" if not validated |
| "100%" anything | Almost always needs qualification |
| "$X.XX" or "~$X" (pricing) | Flag for external verification |
| "averages", "typically" | Flag for source/citation |
| Competitor capability claims | Flag for external verification |
| Unqualified performance numbers | Add "[measured]", "[target]", or "[estimated]" |

## Execution Protocol

### Step 1: Scan the Spec

Read the full spec. For each claim, apply the 9 verification points. Track findings.

### Step 2: Classify Findings

| Level | Definition | Action |
|-------|------------|--------|
| **CRITICAL** | AI will treat hypothesis as fact | Must fix before BUILD |
| **WARNING** | AI might misinterpret | Should fix |
| **TEMPORAL** | Date/time inconsistency | Verify and update |
| **VERIFIABLE** | Claim that could be fact-checked | Route to user for confirmation |

### Step 3: Report

```
## Clarity Gate Results

**Document:** [filename]
**Issues Found:** [number]
**Points Passed:** [e.g., 1-4,6-9]

### Critical (will cause hallucination)
- [issue + location + fix]

### Warning (could cause equivocation)
- [issue + location + fix]

### Externally Verifiable Claims
| # | Claim | Type | Suggested Action |
|---|-------|------|------------------|
| 1 | [claim] | Pricing | [verify at source] |
```

### Step 4: User Confirmation

Present any VERIFIABLE claims to the user for confirmation before proceeding.

## Exit Criteria

- [ ] All 9 points checked
- [ ] Zero CRITICAL findings remaining
- [ ] All WARNING findings documented with decision (fix/accept)
- [ ] Externally verifiable claims confirmed by user or marked with uncertainty

## What This Workflow Does NOT Do

- Does not restructure documents (that's Spec Gate)
- Does not attack logic or find contradictions (that's Adversarial Review)
- Does not check factual accuracy (requires human verification)
- Does not produce CGD format files (adapted for Stream Coding pipeline)

## Credits

Adapted from [Clarity Gate](https://github.com/frmoretto/clarity-gate) v2.1 by Francesco Marinoni Moretto (CC BY 4.0).
