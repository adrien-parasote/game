---
description: Verify specification completeness before coding.
---

# /spec-gate — 📋 SPEC: Spec Gate

Run this checklist on every Implementation Document before ⚡ BUILD.

## 13-Item Checklist

### Foundation (7)
- [ ] **Actionable**: Every section has implementation value.
- [ ] **Current**: No outdated decisions.
- [ ] **Single Source**: No duplicates.
- [ ] **Decision**: Statements are decisions, not wishes.
- [ ] **Prompt-Ready**: Ready for an AI prompt.
- [ ] **No Future State**: "Will eventually" language removed.
- [ ] **No Fluff**: Motivational content removed.

### Architecture (6)
- [ ] **Type Identified**: Strategic vs Implementation.
- [ ] **Anti-patterns**: 5+ entries in Implementation docs.
- [ ] **Test Cases**: 5+ Unit, 3+ Integration in Implementation docs.
- [ ] **Error Handling**: Matrix present in Implementation docs.
- [ ] **Deep Links**: Absolute paths/anchors present in ALL docs.
- [ ] **No Duplicates**: Strategic docs use pointers.

### Learnings Cross-Check
- [ ] **Learnings loaded**: If `.agents/learnings.md` exists, verify the spec doesn't repeat known anti-patterns.
- [ ] **No known ambiguities**: Spec addresses ambiguity classes previously flagged by `/learn-eval`.

## Scoring
Use the **AI Coder Understandability Rubric** from `GEMINI.md` to self-score:
- Actionability (25%), Specificity (20%), Consistency (15%), Structure (15%), Disambiguation (15%), Reference Clarity (10%)
- Target: **10/10** before proceeding to ⚡ BUILD.
- If < 10/10 → fix the spec, do NOT proceed.