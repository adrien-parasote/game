---
description: Create a detailed implementation plan from the validated spec. WAIT for confirmation before any code.
---

# /plan — Implementation Plan

> **Stream Coding reminder:** The plan is a **document**, not code. It translates the validated spec (Spec Gate = 10/10) into a verifiable sequence of actions. No code is written before explicit confirmation.

## Prerequisites

- [ ] The spec passed the Spec Gate (10/10)
- [ ] The spec passed Adversarial Review (0 CRITICAL)

If prerequisites are not met, **refuse to plan** and redirect to `/spec-gate` or `/adversarial-review`.

## Process

### 1. Read constraints

Before planning:
1. Read the validated implementation spec
2. Identify the project language(s)
3. Read language constraints: `.agents/rules/<language>.md`
4. Read universal coding standards: `.agents/templates/CODING_STANDARDS.md`
5. **Load codemaps:** If `docs/CODEMAPS/` exists, read all `.md` files in it. Use them to scope step 3 (Analyze architecture) — identify affected modules from the map, not by scanning the full codebase.

### 2. Restate requirements

Rewrite in clear language what the code must do. The developer must be able to read it and say "yes, that is exactly right". If it is not crystal clear → the spec is incomplete, return to 📋 SPEC.

### 3. Analyze architecture

List every affected component:
- Exact file path
- What changes (new, modified, deleted)
- Impacted dependencies

### 4. Break into steps

| Step | Content | Completion Criteria |
|------|---------|---------------------|
| Step 1 | Foundations + minimal MVP | Main test passes |
| Step 2 | Full happy path | All specified tests pass |
| Step 3 | Edge cases + error handling | Error tests pass |
| Step 4 | Optimization + polish | Performance validated |

For each step:

```markdown
### Step N: [Name]

**Files:**
| File | Action | Description |
|------|--------|-------------|
| `path/to/file.ext` | Create/Modify | What changes |

**Dependencies:** What must be done before this step
**Risks:** H(igh), M(edium), L(ow) + description
**Tests:** Which spec test cases cover this step
```

### 5. Test strategy

Map the Test Case Specifications from the spec to steps:
- Which unit tests per step
- Which integration tests per step
- Which E2E tests once all steps are completed

### 6. Request confirmation

Present the complete plan. **WAIT for "yes" or explicit confirmation.** Never start coding based on an unconfirmed plan.

## Red flags in a plan

Before submitting, verify:
- [ ] No function should exceed 50 lines
- [ ] No file should exceed 800 lines
- [ ] No planned nesting > 4 levels
- [ ] No duplicated code between steps
- [ ] Each step has a test strategy
- [ ] All file paths are exact and verified

## Golden Rule

> If the plan changes during execution → update the plan first, THEN regenerate the code. Never the reverse.
