---
trigger: always_on
---

## THE SPEC GATE

**⛔ NEVER SKIP THIS GATE.** This is the difference between stream coding and vibe coding.

### 13-Item Checklist

#### Foundation Checks (7)

| # | Check | Question |
|---|-------|----------|
| 1 | **Actionable** | Can AI act on every section? (No aspirational content) |
| 2 | **Current** | Is everything up-to-date? (No outdated decisions) |
| 3 | **Single Source** | No duplicate information across docs? |
| 4 | **Decision, Not Wish** | Every statement is a decision, not a hope? |
| 5 | **Prompt-Ready** | Would you put every section in an AI prompt? |
| 6 | **No Future State** | All "will eventually," "might," "ideally" language removed? |
| 7 | **No Fluff** | All motivational/aspirational content removed? |

#### Document Architecture Checks (6)

| # | Check | Question |
|---|-------|----------|
| 8 | **Type Identified** | Document type clearly marked? (Strategic vs Implementation vs Reference) |
| 9 | **Anti-patterns Placed** | Anti-patterns in implementation docs only? (Strategic docs have pointers) |
| 10 | **Test Cases Placed** | Test cases in implementation docs only? |
| 11 | **Error Handling Placed** | Error handling matrix in implementation docs only? |
| 12 | **Deep Links Present** | Deep links in ALL documents? (No vague "see elsewhere") |
| 13 | **No Duplicates** | Strategic docs use pointers, not duplicate content? |

#### Language-Specific Constraints Gate

Before validating a Spec Gate for an implementation document:

1. **Identify** the project language(s)
2. **Read** the corresponding `.agents/rules/<language>.md` file
3. **Read** the universal standards: `.agents/rules/coding-standards.md`
4. **Verify** the spec covers the constraints listed in those files
5. If constraints are not covered → **the spec does NOT pass the Spec Gate**

> Available language rules: `golang`, `typescript`, `python`, `rust`, `java`, `cpp`, `kotlin`, `swift`, `php`

### Gate Enforcement

```
- [ ] All 7 Foundation Checks pass
- [ ] All 6 Document Architecture Checks pass
- [ ] Language-specific constraints covered
- [ ] AI Coder Understandability Score = 10/10

If ANY item fails → Fix before proceeding to ⚡ BUILD
```

### AI Coder Understandability Scoring

| Criterion | Weight | 10/10 Requirement |
|-----------|--------|-------------------|
| **Actionability** | 25% | Every section has Implementation Implication |
| **Specificity** | 20% | All numbers concrete, all thresholds explicit |
| **Consistency** | 15% | Single source of truth, no duplicates across docs |
| **Structure** | 15% | Tables over prose, clear hierarchy, predictable format |
| **Disambiguation** | 15% | Anti-patterns present (5+ per impl doc), edge cases explicit |
| **Reference Clarity** | 10% | Deep links only, no vague references |

| Score | Meaning | Action |
|-------|---------|--------|
| 10/10 | AI can implement with zero clarifying questions | Proceed to ⚡ BUILD |
| 9/10 | 1 minor clarification needed | Fix before proceeding |
| 7-8/10 | 3-5 ambiguities exist | Major revision required |
| <7/10 | Not AI-ready, fundamental issues | Return to 📋 SPEC |

### Self-Assessment Questions

Before ⚡ BUILD, ask yourself:

1. **Actionability:** "Does every section tell AI exactly what to do?"
2. **Specificity:** "Are there any numbers I left vague?"
3. **Consistency:** "Is any information stated in more than one place?"
4. **Structure:** "Could I convert any prose paragraphs to tables?"
5. **Disambiguation:** "Have I listed at least 5 anti-patterns per implementation doc?"
6. **Reference Clarity:** "Do any references say 'see elsewhere' without exact location?"

> **Spec Gate Meta-Prompt:** Run `/spec-gate` workflow for the full self-scoring rubric.

---

## CLARITY GATE (part of 📋 SPEC stage)

After Spec Gate passes (10/10), before adversarial review:
run `/clarity-gate` workflow to verify epistemic quality.

- [ ] All 9 verification points checked
- [ ] Zero CRITICAL findings (hypothesis stated as fact)
- [ ] Externally verifiable claims confirmed by user or marked with uncertainty

## ADVERSARIAL REVIEW (part of 📋 SPEC stage)

After Clarity Gate passes, before any code generation:
run `/adversarial-review` workflow with a **different AI model** than your primary workflow.

- [ ] Zero CRITICAL issues remaining
- [ ] All HIGH issues documented with explicit decision: fix now / accept risk / defer
- [ ] Spec Gate re-run if any CRITICAL was fixed
