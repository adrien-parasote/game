---
description: Stress-test specs with a hostile critic before execution.
---

# /adversarial-review — 📋 SPEC: Adversarial Review

Before any code generation, submit your spec to a different AI model (Gemini, GPT-4o, etc.) or a senior developer with the prompt below.

## Adversarial Prompt Template

Copy and paste the following into a NEW chat with a DIFFERENT AI model:

```markdown
You are a skeptical senior developer reviewing this specification
before it goes to an AI agent for execution.

## Your Mission
Find REAL flaws that would cause incorrect code generation.
Do NOT invent theoretical issues or stylistic preferences.

## What to Look For
1. LOGICAL CONTRADICTIONS: Conflicts within the spec.
2. IMPLICIT DEGREES OF FREEDOM: Where the AI agent must CHOOSE interpretation.
3. MISSING ERROR STATES: Unhandled failure modes with concrete impact.
4. AMBIGUOUS REQUIREMENTS: Statements that two developers would interpret differently.

## What NOT to Flag (Hard Exclusions)
- Stylistic preferences (naming, formatting, prose quality)
- "Could be more detailed" without specifying WHAT is missing
- Best practices the spec didn't claim to follow
- Theoretical edge cases without concrete exploitation scenario
- Performance concerns without measurable thresholds
- "Consider adding" suggestions — this is a review, not a feature request
- Redundancy that aids clarity (intentional repetition for readability)
- Missing features that are explicitly out of scope
- Security concerns already covered by the security review workflow

## Confidence Requirement
Only report findings where you are ≥ 80% confident that an AI coder
would generate INCORRECT code because of this issue. If the AI would
probably get it right despite the ambiguity — do not report it.

## Output Format
[SEVERITY] — Issue title
Location: Section/Line
Problem: What SPECIFIC incorrect code would result
Fix: Specific rewrite needed (exact text, not vague direction)

Severity: CRITICAL / HIGH / MEDIUM / LOW
```

## Hard Exclusions — Do NOT Accept These as Findings

| # | Exclusion | Why |
|---|-----------|-----|
| 1 | "Could be more detailed" without specifics | Not actionable |
| 2 | Stylistic or formatting suggestions | Not a spec failure |
| 3 | Feature requests disguised as findings | Review ≠ ideation |
| 4 | Theoretical concerns without concrete code impact | Speculation |
| 5 | "Industry best practice" the spec never claimed to follow | Scope creep |
| 6 | Security concerns (handled by `/security-review`) | Wrong workflow |
| 7 | Performance concerns without measurable criteria | Not actionable |
| 8 | Redundancy that aids clarity | Intentional |

## Convergence Protocol

The adversarial review MUST converge. Follow this protocol:

1. **Run 1:** Apply the adversarial prompt. Collect findings.
2. **Fix:** Address all CRITICAL and HIGH findings in the spec.
3. **Run 2 (if CRITICALs were fixed):** Re-run the review on the UPDATED spec.
4. **Convergence check:** If Run 2 produces NEW findings that were NOT present in Run 1:
   - Apply Hard Exclusions — exclude any finding matching the table above
   - Apply Confidence filter — exclude findings < 80% confidence
   - If remaining new findings = 0 → **CONVERGED**
   - If remaining new findings > 0 → fix and do ONE more run (max)
5. **Maximum 5 runs.** Stop early if a run produces zero new findings after filtering. After 5 runs, accept the spec as reviewed. Document any remaining MEDIUM/LOW issues as known limitations.

> **Why limit runs?** An unconstrained hostile critic will ALWAYS find new issues.
> The goal is not perfection — it's eliminating issues that would cause incorrect code generation.

## Exit Criteria

- [ ] ZERO **CRITICAL** issues remaining.
- [ ] All **HIGH** issues have a documented decision (fix/accept/defer).
- [ ] Review has **converged** (no new findings after filtering, or 3 runs reached).
- [ ] Re-score with Spec Gate if criticals were fixed.
