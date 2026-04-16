# Coding Standards — Universal Rules

> These rules apply to **every** language. For language-specific constraints, see `.agents/rules/<language>.md`.

## Immutability (CRITICAL)

- Create new objects/structures, never mutate existing ones
- No reassignment unless proven necessary
- Collections returned by public APIs are copies, not references

```
// Pseudocode
WRONG:  modify(original, field, value) → changes original in-place
CORRECT: update(original, field, value) → returns new copy with change
```

Rationale: Immutability eliminates hidden side-effects, simplifies debugging, and ensures safe concurrency.

## Code Organization

| Criterion | Limit |
|-----------|-------|
| File size | 200-400 lines (800 absolute max) |
| Function size | < 50 lines |
| Nesting | < 4 levels (use early returns) |
| Duplication | If you write the same 3 lines twice → extract a function |
| Organization | By feature/domain, not by type |

## Error Handling

- **Never** silently swallow errors (empty catch, `_ = err`)
- User-friendly messages on the UI side
- Detailed server-side logging with context (file, function, input)
- Typed errors if the language supports them
- Never expose stack traces to users

## Validation

- Validate at **system boundaries** (API input, user input, external data)
- Fail fast — reject invalid data immediately
- Never trust external data (API responses, user input, file content)
- Explicit validation schema (Zod, JSON Schema, struct tags)

## Security (basics)

- Zero hardcoded secrets — env vars + secrets manager
- Parameterized queries — never SQL concatenation
- Sanitize HTML — never `innerHTML` with user data
- Rate limiting on public endpoints
- Error messages must not leak internal data
- See `.agents/rules/security.md` for the full checklist and response protocol

## Git

Conventional commit format:

```
<type>: <description>

Types: feat, fix, refactor, docs, test, chore, perf, ci
```

## Test Coverage

- **80% minimum** (branches, functions, lines)
- Unit tests + integration tests + E2E tests (critical flows)
- See `.agents/workflows/tdd.md` for the TDD cycle

## Pre-Edit Dependency Check (MANDATORY)

> ⛔ **Before modifying ANY file**, answer these 4 questions. Do NOT skip this.

| # | Question | Why |
|---|----------|-----|
| 1 | **What imports this file?** | Dependents might break if you change exports/signatures |
| 2 | **What does this file import?** | Interface changes in dependencies affect this file |
| 3 | **What tests cover this file?** | You need to run them after editing — if none exist, write them first (TDD Gate) |
| 4 | **Is this a shared module?** | Shared code affects multiple consumers — changes need broader verification |

**How to check quickly:**

```bash
# Find dependents (what imports this file)
rg "import.*<module_name>" --type-add 'code:*.{ts,js,go,py}' -t code .
# OR
grep -r "from.*<module>" --include="*.py" .

# Find test files
rg -l "test|spec" --glob "*<module_name>*" .
```

If any answer reveals a shared component or missing tests → **proceed with extra caution** or write tests first.

## Code Quality Checklist

Before marking work as complete:

- [ ] Readable code with explicit naming
- [ ] Functions < 50 lines
- [ ] Files < 800 lines
- [ ] No nesting > 4 levels
- [ ] Explicit error handling
- [ ] No hardcoded values (use constants or config)
- [ ] Immutable patterns used
- [ ] No state mutation

## Post-Task Self-Verification (MANDATORY)

> ⛔ **After completing ANY implementation work**, run these checks before declaring "done".

### Quick Automated Check

```bash
# Run the full verification suite (preferred — auto-detects build system)
python .agents/skills/verification-loop/scripts/verify.py .

# If security-sensitive changes were made
python .agents/skills/security-review/scripts/security_scan.py . --output summary
```

### Manual Checklist (if scripts unavailable)

| # | Check | How | Fail Action |
|---|-------|-----|-------------|
| 1 | **Build passes** | `npm run build` / `go build ./...` / etc. | Fix before anything else |
| 2 | **Type check passes** | `npx tsc --noEmit` / `go vet ./...` / etc. | Fix type errors |
| 3 | **Lint passes** | `npm run lint` / `golangci-lint run` / etc. | Fix or justify |
| 4 | **Tests pass** | `npm test` / `go test ./...` / etc. | Fix. If spec unclear → fix spec first |
| 5 | **No debug artifacts** | No `console.log`, `print()`, `fmt.Print` in prod code | Remove |
| 6 | **No new secrets** | No hardcoded keys, tokens, passwords | Use env vars |
| 7 | **Spec still matches** | Code implements what spec says, nothing more, nothing less | Update spec or code |

> **Rule:** If any check fails, fix it BEFORE moving on. Do NOT defer. Do NOT "fix later".

## Language Rules

| Language | File |
|----------|------|
| Go | `.agents/rules/golang.md` |
| TypeScript/JavaScript | `.agents/rules/typescript.md` |
| Python | `.agents/rules/python.md` |
| Rust | `.agents/rules/rust.md` |
| Java | `.agents/rules/java.md` |
| C++ | `.agents/rules/cpp.md` |
| Kotlin | `.agents/rules/kotlin.md` |
| Swift | `.agents/rules/swift.md` |
| PHP | `.agents/rules/php.md` |
