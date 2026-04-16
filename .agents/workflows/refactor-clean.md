---
description: Dead code detection and removal. Incremental approach by risk (SAFE/CAREFUL/RISKY). Updates spec after cleanup.
---

# /refactor-clean — Dead Code Cleanup

## When to Use

- After a major development effort
- When the codebase grows and accumulates unused code
- Regular maintenance (recommended: 1x per sprint)

## Stream Coding Integration

- **Stage:** ✅ HARDEN
- **Rule:** After cleanup → update the spec if the code surface changes (Rule of Divergence)
- **Golden Rule:** If a refactor reveals a gap in the spec → fix the spec first

## When NOT to Use

- During active feature development
- On code you do not fully understand yet
- Without a functioning test suite (no safety net)

## Process

### 1. Detection

**JavaScript/TypeScript:**
```bash
npx knip                         # Full detection (exports, deps, files)
npx depcheck                     # Unused dependencies
npx ts-prune                     # Unused TypeScript exports
npx eslint --report-unused-disable-directives .
```

**Python:**
```bash
vulture .                        # Dead code detection
pip-audit                        # Dependencies
ruff check . --select F401,F811  # Unused imports
```

**Go:**
```bash
go vet ./...
staticcheck ./...
```

**Rust:**
```bash
cargo clippy -- -W dead_code
cargo udeps                      # Unused dependencies
```

**Java/Kotlin:**
```bash
# Via IDE inspections or:
./gradlew lint                   # Android/Kotlin
```

### 2. Categorize risk

| Level | Criteria | Action |
|-------|----------|--------|
| **SAFE** | Never referenced, no public export, no tests | Delete directly |
| **CAREFUL** | Exported but never imported, or imported in one place only | Check indirect usage (reflection, dynamic imports) |
| **RISKY** | Used via indirection, part of public API | Mark deprecated, remove in next cycle |

### 3. Deletion order

1. **Unused dependencies** (package.json, requirements.txt, Cargo.toml)
2. **Unused exports** (functions, classes, constants exported but never imported)
3. **Entire files** (modules no longer imported anywhere)
4. **Duplicated code** (after extracting the common function)

### 4. Safety checklist before deletion

- [ ] Tests pass before starting
- [ ] Each deletion is followed by `build` + `test`
- [ ] No batch deletions — one type at a time
- [ ] CAREFUL deletions verified with `grep -rn`
- [ ] RISKY deletions documented and reviewed
- [ ] Spec updated if API surface changes

### 5. Post-cleanup

- Update documentation if modules/functions were removed
- Atomic commit: `refactor: remove unused [component]`
- If the spec references deleted code → update the spec (Rule of Divergence)
