---
description: Code-to-spec conformance audit. Verifies generated code matches the spec, security rules, and language standards. If divergence → flag the spec, not the code.
---

# /code-review — Conformance Audit

> **Stream Coding reminder:** This is not a classic code review. It is a **conformance audit**: does the code match the spec? If not, the spec is corrected first (Golden Rule).

## Process

### 1. Establish review scope

Before reviewing anything, determine what changed:

```bash
# PR review — detect actual base branch
gh pr view --json baseRefName,mergeStateStatus,statusCheckRollup 2>/dev/null

# Local review — prefer staged, then unstaged
git diff --staged --stat
git diff --stat

# Fallback if shallow history
git show --patch HEAD --stat
```

**If PR metadata available**, check merge readiness first:
- If required checks are **failing or pending** → STOP, report "review should wait for green CI"
- If PR shows **merge conflicts** → STOP, report "conflicts must be resolved first"
- If merge readiness cannot be verified → state this explicitly before continuing

### 2. Gather sources of truth

Before reviewing, read:
1. **The implementation spec** — code must match it exactly
2. **Security rules:** `.agents/rules/security.md`
3. **Language rules:** `.agents/rules/<language>.md` (includes the Review Checklist)

### 3. Run diagnostic commands

Run the project's canonical check commands before starting the review:

```bash
# Type checking (language-dependent)
# TypeScript: prefer project's typecheck script, use relevant tsconfig
npm run typecheck --if-present || tsc --noEmit -p <relevant-config>

# Linting
eslint . --ext .ts,.tsx,.js,.jsx  # or ruff check . / golangci-lint run / etc.
```

If typecheck or linting **fails** → STOP, report the errors. No point reviewing code that doesn't build.

### 4. Apply the language-specific review checklist

Load the Review Checklist from `.agents/rules/<language>.md` and apply it to the diff. The checklist is organized by severity (CRITICAL → HIGH → MEDIUM).

Additionally, check these universal items:

#### CRITICAL — Blocking, fix immediately

- [ ] Hardcoded secrets (API keys, passwords, tokens)
- [ ] SQL injection (string concatenation in queries)
- [ ] XSS (unescaped user input rendered in HTML)
- [ ] Path traversal (user-controlled file paths)
- [ ] CSRF (state-changing endpoints without protection)
- [ ] Auth bypass (protected routes without verification)
- [ ] Secrets in logs (tokens, PII)

#### HIGH — Fix before merge

- [ ] Functions > 50 lines
- [ ] Files > 800 lines
- [ ] Nesting > 4 levels
- [ ] Missing error handling (empty catches, unhandled rejections)
- [ ] Direct mutations (instead of immutable copies)
- [ ] `console.log` / print debug in production
- [ ] New code without tests
- [ ] Dead code (commented out, unused imports, unreachable branches)

#### MEDIUM — Note

- [ ] O(n^2) algorithms when O(n) or O(n log n) is possible
- [ ] Unnecessary re-renders (non-memoized components)
- [ ] Full library imports instead of specific modules
- [ ] Repeated computations without cache
- [ ] Synchronous I/O in an async context

#### LOW — Suggestion

- [ ] TODO/FIXME without ticket number
- [ ] Public APIs without documentation
- [ ] Unexplained magic numbers
- [ ] Variables named `x`, `tmp`, `data` in non-trivial code

#### Framework-Specific: React / Next.js (HIGH)

When the project uses React or Next.js, also check:

- [ ] Missing dependency arrays — `useEffect`/`useMemo`/`useCallback` with incomplete deps
- [ ] State updates in render — calling setState during render causes infinite loops
- [ ] Missing keys in lists — using array index as key when items can reorder
- [ ] Prop drilling — props passed through 3+ levels (use context or composition)
- [ ] Client/server boundary — using `useState`/`useEffect` in Server Components
- [ ] Missing loading/error states — data fetching without fallback UI
- [ ] Stale closures — event handlers capturing stale state values

```tsx
// BAD: Missing dependency, stale closure
useEffect(() => {
  fetchData(userId);
}, []); // userId missing from deps

// GOOD: Complete dependencies
useEffect(() => {
  fetchData(userId);
}, [userId]);
```

```tsx
// BAD: Using index as key with reorderable list
{items.map((item, i) => <ListItem key={i} item={item} />)}

// GOOD: Stable unique key
{items.map(item => <ListItem key={item.id} item={item} />)}
```

#### Framework-Specific: Backend / API (HIGH)

When reviewing backend or API code, also check:

- [ ] Unvalidated input — request body/params used without schema validation
- [ ] Missing rate limiting — public endpoints without throttling
- [ ] Unbounded queries — `SELECT *` or queries without LIMIT on user-facing endpoints
- [ ] N+1 queries — fetching related data in a loop instead of a join/batch
- [ ] Missing timeouts — external HTTP calls without timeout configuration
- [ ] Error message leakage — sending internal error details to clients
- [ ] Missing CORS configuration — APIs accessible from unintended origins

```typescript
// BAD: N+1 query pattern
const users = await db.query('SELECT * FROM users');
for (const user of users) {
  user.posts = await db.query('SELECT * FROM posts WHERE user_id = $1', [user.id]);
}

// GOOD: Single query with JOIN or batch
const usersWithPosts = await db.query(`
  SELECT u.*, json_agg(p.*) as posts
  FROM users u
  LEFT JOIN posts p ON p.user_id = u.id
  GROUP BY u.id
`);
```

#### Silent Failure Hunting (HIGH)

Actively scan the diff for patterns that hide real failures:

- [ ] Empty catch blocks — `catch {}` or `except: pass`
- [ ] Dangerous fallbacks — `.catch(() => [])`, `?? []`, `|| {}` that return valid-looking data
- [ ] Log-and-forget — `console.error(e)` then continue as if nothing happened
- [ ] Lost stack traces — `throw new Error(e.message)` discards original cause
- [ ] Missing async handling — `async` without `try/catch` or `.catch()`
- [ ] Missing rollback — multi-step writes without transaction/rollback

```typescript
// BAD: Dangerous fallback hides real failure
const users = await fetchUsers().catch(() => []);
// Downstream code thinks "no users" instead of "fetch failed"

// GOOD: Propagate or handle explicitly
const users = await fetchUsers().catch((e) => {
  logger.error('Failed to fetch users', { error: e });
  throw new ServiceUnavailableError('User service down');
});
```

#### AI-Generated Code Addendum (MEDIUM)

When reviewing code generated by an AI agent (which in Stream Coding is always):

- [ ] Behavioral regressions — did the AI subtly change existing semantics?
- [ ] Trust boundary assumptions — did the AI skip auth/validation on internal callers?
- [ ] Architecture drift — did the AI introduce patterns inconsistent with the codebase?
- [ ] Over-engineering — unnecessary abstractions the spec didn't ask for?
- [ ] Hallucinated APIs — calls to functions, methods, or libraries that don't exist?

### 5. Confidence-based filtering

- **Report** only if > 80% confident it is a real problem
- **Ignore** stylistic preferences unless they violate project conventions
- **Consolidate** similar issues ("5 functions without error handling" not 5 separate findings)
- **Ignore** unmodified code except CRITICAL security issues

### 6. Verify spec-to-code conformance

For each generated function/module:
- Does the behavior exactly match what the spec describes?
- Does error handling match the Error Handling Matrix from the spec?
- Are documented edge cases implemented?

**If divergence detected → the question is not "how to patch the code" but "is the spec incomplete?"**

### 7. Produce the report

Use the following format:

```
[SEVERITY] Issue title
File: path/to/file.ext:42
Issue: Problem description
Fix: Concrete suggestion

## Review Summary
| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0     | pass   |
| HIGH     | 2     | warn   |
| MEDIUM   | 3     | info   |
| LOW      | 1     | note   |

Verdict: APPROVE / WARNING / BLOCK
```

## Verdict Criteria

| Verdict | Condition |
|---------|-----------|
| **APPROVE** | 0 CRITICAL, 0 HIGH |
| **WARNING** | 0 CRITICAL, HIGH > 0 (merge with caution) |
| **BLOCK** | CRITICAL > 0 (mandatory fix before merge) |

### Divergence Rule

If the review detects behavior that does not match the spec:

> ⚠️ **DIVERGENCE**: Code does [X] but spec specifies [Y].
> **Action**: First check if the spec is incomplete → update the spec → regenerate the code.
