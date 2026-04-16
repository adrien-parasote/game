---
name: verification-loop
description: Activate after completing a feature, before creating a PR, or after refactoring. Runs build, typecheck, lint, tests, security scans, spec-conformance checks, and silent-failure hunting to verify quality gates.
---

# Verification Loop Skill

The **Verify** step in Stream Coding's "Generate → Verify → Integrate" loop. This is not a passive checklist — it is an active audit that reasons about spec conformance, hunts silent failures, and flags AI-generated code patterns.

> If verification reveals spec non-conformance → fix the spec first, then regenerate.

## When to Activate

- After completing a feature or significant code change
- Before creating a PR or merging
- After refactoring
- On every `/orchestrate` cycle between TDD and code-review

## Automated Scripts

> **This skill includes executable scripts** following the [agentskills.io](https://agentskills.io) standard.
> Scripts auto-detect the project's build system and produce structured output.

### Quick Run (replaces manual Phases 1-5)

```bash
# Run all verification checks (auto-detects build system)
python .agents/skills/verification-loop/scripts/verify.py .

# JSON output for programmatic consumption
python .agents/skills/verification-loop/scripts/verify.py . --json

# Security + Build only (P0 + P1, stop on first CRITICAL)
python .agents/skills/verification-loop/scripts/verify.py . --priority P0,P1 --stop-on-fail

# Spec conformance check (Phase 6)
python .agents/skills/verification-loop/scripts/spec_conformance.py .
python .agents/skills/verification-loop/scripts/spec_conformance.py . --spec docs/api-spec.md
```

### Script Reference

| Script | Covers | Priority |
|--------|--------|----------|
| `scripts/verify.py` | P0 Security → P1 Build → P2 Types → P3 Lint → P4 Tests → P5 Debug artifacts | CRITICAL→MEDIUM |
| `scripts/spec_conformance.py` | Exports, API routes, file references vs spec | Spec drift |

> Use `--help` on any script for full usage. All produce exit code 0 (pass) or 1 (fail).

---

## Verification Phases

> **Prefer scripts:** Run `verify.py` to execute Phases 1-5 automatically.
> Fall back to manual commands only when scripts are unavailable or you need granular control.

### Phase 1: Build Verification

```bash
# Automated (preferred)
python .agents/skills/verification-loop/scripts/verify.py . --priority P1

# Manual fallback — detect build system and run
npm run build 2>&1 | tail -20
# OR: cargo build, go build ./..., ./gradlew build, terraform validate, etc.
```

If build fails → **STOP**. Fix before continuing. Use `/build-fix` if needed.

### Phase 2: Type Check

```bash
# Automated (preferred)
python .agents/skills/verification-loop/scripts/verify.py . --priority P2

# Manual fallback
npx tsc --noEmit 2>&1 | head -30      # TypeScript
pyright . 2>&1 | head -30              # Python
go vet ./...                            # Go
cargo check                             # Rust
```

Report all type errors. Fix critical ones before continuing.

### Phase 3: Lint Check

```bash
# Automated (preferred)
python .agents/skills/verification-loop/scripts/verify.py . --priority P3

# Manual fallback
npm run lint 2>&1 | head -30           # JavaScript/TypeScript
ruff check . 2>&1 | head -30           # Python
golangci-lint run                       # Go
cargo clippy                            # Rust
tflint --recursive                      # Terraform
```

### Phase 4: Test Suite

```bash
# Automated (preferred)
python .agents/skills/verification-loop/scripts/verify.py . --priority P4

# Manual fallback
npm run test -- --coverage 2>&1 | tail -50
# OR: go test ./... -coverprofile=cover.out
# OR: pytest --cov
# Target: 80% minimum
```

Report: Total tests, Passed, Failed, Coverage %.

### Phase 5: Security Scan

```bash
# Automated (preferred — uses the security-review skill's scanner)
python .agents/skills/security-review/scripts/security_scan.py .
# OR via verify.py:
python .agents/skills/verification-loop/scripts/verify.py . --priority P0

# Manual fallback
rg -n "sk-|api_key|password|secret" --type-add 'code:*.{ts,js,py,go,tf}' -t code . | head -10
rg -n "console\.log|print\(|fmt\.Print" --type-add 'code:*.{ts,js,py,go}' src/ | head -10
rg -n "TODO|FIXME|HACK|XXX" --type-add 'code:*.{ts,js,py,go,tf}' -t code . | head -10
```

### Phase 6: Spec Conformance Audit

**This is the phase that separates this skill from a generic CI pipeline.**

For each changed file/module, actively verify against the source spec:

1. **Behavioral match** — Does the code do exactly what the spec describes? Not more, not less.
2. **Error handling match** — Does error handling match the Error Handling Matrix from the spec?
3. **Edge case coverage** — Are all documented edge cases implemented?
4. **Anti-pattern avoidance** — Did the code violate any anti-pattern listed in the spec?
5. **Interface conformance** — Do function signatures, types, and API contracts match the spec?

**If divergence detected:**

```
⚠️ DIVERGENCE: [file:line] does [X] but spec specifies [Y].
Action: Check if spec is incomplete → update spec → regenerate code.
```

> Do NOT silently fix the code. Divergence means either the spec or the code is wrong. Determine which, and fix the source of truth first.

### Phase 7: Silent Failure Hunting

Actively scan the changed code for patterns that hide real failures:

| Hunt Target | What to Look For | Why It's Dangerous |
|---|---|---|
| **Empty catch blocks** | `catch {}`, `catch (e) {}`, `except: pass` | Errors vanish — impossible to debug |
| **Dangerous fallbacks** | `.catch(() => [])`, `?? []`, `|| {}` | Returns look valid but data is missing |
| **Log-and-forget** | `console.error(e)` then continue | Error is noted but never acted on |
| **Lost stack traces** | `throw new Error(e.message)` | Original cause vanishes |
| **Missing async handling** | `async` without `try/catch` or `.catch()` | Unhandled rejection crashes at runtime |
| **Missing timeouts** | HTTP/DB calls without timeout config | Hangs indefinitely under failure |
| **Missing rollback** | Multi-step writes without transaction/rollback | Partial writes corrupt state |

For each finding, report:
- **Location**: file:line
- **Severity**: CRITICAL / HIGH / MEDIUM
- **Issue**: What fails silently
- **Impact**: What downstream effect this causes
- **Fix**: Concrete recommendation

### Phase 8: AI-Generated Code Audit

When reviewing code that was generated by an AI agent (which in Stream Coding is always), additionally check:

| Check | What to Look For |
|---|---|
| **Behavioral regressions** | Did the AI preserve existing behavior, or did it subtly change semantics? |
| **Trust boundary assumptions** | Did the AI assume internal callers are always trusted? |
| **Architecture drift** | Did the AI introduce coupling or patterns inconsistent with the codebase? |
| **Over-engineering** | Did the AI add unnecessary abstractions, unused generics, or defensive code that the spec didn't ask for? |
| **Under-engineering** | Did the AI implement the happy path but skip error paths listed in the spec? |
| **Hallucinated APIs** | Did the AI call functions, methods, or libraries that don't exist? |

## Output Format

```
VERIFICATION REPORT
==================

Build:     [PASS/FAIL]
Types:     [PASS/FAIL] (X errors)
Lint:      [PASS/FAIL] (X warnings)
Tests:     [PASS/FAIL] (X/Y passed, Z% coverage)
Security:  [PASS/FAIL] (X issues)
Spec:      [CONFORMS/DIVERGES] (X divergences)
Silent:    [CLEAN/X findings] (X silent failure patterns)
AI-Audit:  [CLEAN/X findings]

Overall:   [READY/NOT READY] for PR

Issues to Fix:
1. [CRITICAL] ...
2. [HIGH] ...

Divergences (fix spec first):
1. ...
```

## Continuous Mode

For long sessions, run verification at natural checkpoints:
- After completing each function or module
- After finishing a component
- Before moving to the next task in `/orchestrate`
- Before hitting context limits (save state before it's lost)

---

**Remember**: Verification is not optional. It's the feedback loop that makes Stream Coding work. Phases 1-5 catch mechanical issues. Phases 6-8 catch semantic issues that CI pipelines miss.
