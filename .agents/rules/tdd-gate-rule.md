---
trigger: always_on
---

## THE TDD GATE

**⛔ NEVER SKIP THIS GATE.** No implementation code without RED tests. This is non-negotiable.

> Spec Gate ensures docs are AI-ready before coding.
> TDD Gate ensures tests exist before implementation.
> Skip either one → you're vibe coding.

### Gate Checklist

Before writing ANY implementation code for a module:

```
- [ ] Test files exist for the module being implemented
- [ ] Tests are written from the spec's Test Case Specifications
- [ ] Tests are RED (failing) — they define what to build
- [ ] Edge cases from the spec's mandatory edge case table are covered
- [ ] Test framework and conventions match `.agents/rules/<language>.md`

If ANY item fails → STOP. Do NOT write implementation code.
```

### Gate Enforcement

The TDD Gate triggers at the boundary between `/tdd` (step 1) and implementation (step 2) in the Spec-Test-Implement Loop.

```
⚡ BUILD Loop:
  0. READ SPEC
  1. /tdd → Write tests from spec (RED)

  ⛔ TDD GATE — checkpoint here:
     → Test files exist?  NO → STOP, run /tdd
     → Tests are RED?     NO → Tests are wrong, fix them
     → Edge cases covered? NO → STOP, add edge case tests

  2. IMPLEMENT → Write code to pass tests (GREEN)
  3. VERIFY → verification-loop
```

### Self-Check Questions

Before writing implementation code, ask yourself:

1. **"Do test files exist for this module?"** — If no → run `/tdd` first.
2. **"Are tests currently RED?"** — If they pass already → tests are trivial or wrong.
3. **"Did I translate ALL the spec's Test Case Specifications?"** — If not → incomplete coverage.
4. **"Did I cover the mandatory edge cases?"** — Null, empty, invalid, boundaries, I/O errors.

### What Counts as "Implementation Code"

Any code that:
- Creates or modifies production source files (not test files)
- Implements business logic, API handlers, data models
- Adds routes, middleware, services, utilities

What does NOT require the TDD Gate:
- Configuration files (`.env`, `tsconfig.json`, `go.mod`)
- Build scripts, CI/CD files
- Documentation, specs, templates
- Type definitions without logic (pure interfaces/types)
- Scaffolding (project init, directory creation)

### Recovery Protocol

If you catch yourself writing implementation code without RED tests:

1. **STOP immediately** — do not finish the function
2. **State explicitly:** "⛔ TDD Gate violation — I wrote implementation code without RED tests"
3. **Run `/tdd`** — write tests for what you were about to implement
4. **Verify RED** — tests must fail
5. **Resume implementation** — now continue from the GREEN step

### Why This Gate Exists

Without the TDD Gate:
- AI skips to implementation because it's "faster"
- Tests get written AFTER code (confirmation bias — tests follow implementation, not spec)
- Edge cases are missed because they weren't tested first
- Divergence from spec goes undetected

With the TDD Gate:
- Tests come FROM the spec, not from the implementation
- Every spec requirement has a verifiable assertion
- Edge cases are caught before implementation, not after
- Implementation is constrained to what's specified
