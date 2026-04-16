---
name: planner
description: Activate for complex features requiring multi-file changes, dependency analysis, or multi-phase implementations. Breaks down work into actionable, ordered steps with risks and dependencies.
---

# Implementation Planner Skill

Breaks down complex features into actionable, ordered implementation steps with risks and dependencies identified.

## When to Activate

- Complex features spanning multiple files/modules
- Features with unclear implementation path
- Work requiring dependency analysis
- Multi-phase implementations

## Stream Coding Principle

> Phase 1 Strategic Thinking: answering the 7 Questions with specificity.
> The planner outputs a PLAN that feeds the SPEC. The spec feeds the code.
> A good plan makes the spec obvious. A bad plan makes the spec ambiguous.

## Planning Process

### 1. Understand Scope

- If `docs/CODEMAPS/` exists, read all `.md` files in it — use them to identify affected modules and file paths instead of scanning the full codebase
- Read the requirements or user request fully
- Identify what exists vs what needs to be created
- Map the affected files and modules (scoped by codemaps when available)

### 2. Break Down

Decompose into phases ordered by dependency:

```markdown
## Plan: [Feature Name]

### Phase 1: [Foundation]
**Files:** [list of files]
**Dependencies:** None
**Risk:** [LOW/MEDIUM/HIGH]
**Tests:** [what needs testing]
- [ ] Step 1.1: [specific action]
- [ ] Step 1.2: [specific action]

### Phase 2: [Core Logic]
**Files:** [list of files]
**Dependencies:** Phase 1
**Risk:** [LOW/MEDIUM/HIGH]
**Tests:** [what needs testing]
- [ ] Step 2.1: [specific action]
- [ ] Step 2.2: [specific action]
```

### 3. Risk Assessment

| Risk Level | Criteria | Mitigation |
|------------|----------|------------|
| **LOW** | Well-understood, isolated change | Standard review |
| **MEDIUM** | Multiple modules affected, some unknowns | Extra testing, staged rollout |
| **HIGH** | Core architecture change, external dependencies | Spike/prototype first, extensive testing |

### 4. Spec Readiness Check

Before the plan is "done":
- [ ] Each phase has clear acceptance criteria
- [ ] Edge cases identified per phase
- [ ] Dependencies are explicit and ordered
- [ ] Risk mitigations are actionable
- [ ] The plan can be translated into spec sections

## Output Rules

- Be specific: file names, function signatures, data structures
- Be minimal: smallest change that achieves the goal
- Be phased: each phase should be independently testable
- Document decisions: why THIS approach over alternatives

## EXIT GATE (MANDATORY)

> ⛔ **A plan CANNOT leave this skill until ALL items pass.** An incomplete plan produces an ambiguous spec, which produces wrong code — the exact failure cascade Stream Coding exists to prevent.

Before handing off to 📋 SPEC:

| # | Gate Item | Test |
|---|-----------|------|
| 1 | **Every phase has acceptance criteria** | If you removed the code and re-read the plan, could you tell if each phase succeeded? |
| 2 | **Dependencies are explicit** | Can AI determine the build order without asking? |
| 3 | **Risks have mitigations, not just labels** | "HIGH risk" alone is useless — what's the mitigation? |
| 4 | **No phase has > 5 steps** | If it does, split it. Large phases hide complexity and cause missed work. |
| 5 | **File paths are concrete** | `src/handlers/auth.go`, not "the auth handler file" |
| 6 | **Scope is bounded** | Can you list what is explicitly NOT included? If not, scope will creep during SPEC. |

```
- [ ] All 6 gate items pass
- [ ] Plan reviewed with user (if scope > 3 phases)

If ANY item fails → Fix the plan. Do NOT proceed to spec.
```

---

**Remember**: A plan is not a spec. A plan decides WHAT to do. The spec decides HOW to do it in enough detail for code generation.
