---
description: Incremental build error resolution. Detects build system, parses errors, applies minimal fix one at a time. Stop if it gets worse.
---

# /build-fix — Build Error Resolution

> A build fix is a minimal fix. If the fix requires an architectural change → return to plan/spec.

## Process

### 1. Detect the build system

| Indicator | Command |
|-----------|---------|
| `package.json` + `build` script | `npm run build` or `pnpm build` |
| `tsconfig.json` (TS without build script) | `npx tsc --noEmit` |
| `Cargo.toml` | `cargo build 2>&1` |
| `go.mod` | `go build ./...` |
| `pom.xml` | `mvn compile` |
| `build.gradle` / `build.gradle.kts` | `./gradlew compileJava` / `./gradlew compileKotlin` |
| `pyproject.toml` | `mypy .` or `python -m py_compile <file>` |

### 2. Run the build and parse errors

1. Run the build command
2. Isolate the first error
3. Read the relevant source file + surrounding context

### 3. Minimal fix

- Fix **one error** at a time
- The fix must be the smallest possible change
- Re-run the build after each fix
- Move to the next error

### 3b. Structured Debugging (when simple fixes stall)

> **Trigger:** If the same error returns after 1 fix attempt, or a fix introduces new errors, switch to structured debugging before attempting more fixes.

#### Phase A: OBSERVE — Gather evidence, don't guess

```
1. Read the FULL error message, not just the first line
2. Check the error file AND its imports/dependents
3. Check recent changes: git diff HEAD~1 --stat
4. Note: What changed? What was the last working state?
```

#### Phase B: HYPOTHESIZE — Form exactly ONE hypothesis

```
Write down: "I believe the error is caused by [X] because [evidence]"

Rules:
- The hypothesis MUST be supported by evidence from Phase A
- If you can't form one → gather more evidence (back to Phase A)
- NEVER apply a fix based on a hunch
```

#### Phase C: TEST — Verify the hypothesis BEFORE fixing

```
How to test without changing code:
- Read the relevant source to confirm the hypothesis
- Trace the call chain from error back to root cause
- Check if the hypothesis explains ALL symptoms, not just one
```

#### Phase D: FIX — Apply the minimal targeted fix

```
1. Fix ONLY what the hypothesis identified
2. Re-run the build
3. If fixed → continue to next error
4. If NOT fixed → back to Phase A with new evidence
```

#### 5 Whys (for persistent errors)

If an error survives 2+ fix attempts, apply 5 Whys before trying again:

```
Error: "Cannot find module './utils'"
Why 1: The import path is wrong → Why?
Why 2: The file was moved → Why?
Why 3: A refactor changed the directory structure → Why?
Why 4: The spec reorganized modules by domain → Why?
Why 5: ROOT CAUSE: The refactor updated the file but not all its importers
→ Fix: Update all import paths referencing the old location
```

> **Key insight:** The first "why" is almost never the root cause. Keep digging.

### 4. Guardrails

Stop immediately and report if:
- [ ] A fix introduces **more** errors than it resolves
- [ ] The same error returns **3 times** despite fixes → deeper problem (use 5 Whys)
- [ ] The fix requires an **architectural** change → return `/plan`
- [ ] The fix contradicts the **spec** → return to spec (Golden Rule)

### 5. Final verification

```bash
# Full rebuild
<build command>

# Tests
<test command>
```

Both must pass before considering the build fix complete.
