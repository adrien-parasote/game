# TypeScript / JavaScript — Documentation Constraints

> The spec for a TS/JS project MUST cover these points.

## Types and Interfaces

- Explicit types on all public APIs (exported functions, component props)
- Let TypeScript infer obvious local variables
- `interface` for extensible object shapes, `type` for unions/intersections/mapped types
- **Never `any`** — use `unknown` + narrowing for external data
- String literal unions > `enum` unless interop needed

```typescript
// The spec must clearly define types
interface User { id: string; email: string }
type UserRole = 'admin' | 'member'

// unknown, not any
function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  return 'Unexpected error'
}
```

## React/Svelte Patterns

The spec MUST cover:
- Props with named `interface` (no inline types)
- No `React.FC` unless specifically justified
- Complete dependency arrays in `useEffect`/`useMemo`/`useCallback`
- Stable keys (no array index if reordering possible)
- Explicit client/server boundary (Server Components vs Client Components)
- Loading/error states for all data fetching

## Immutability

- Spread operator for updates:
  ```typescript
  function updateUser(user: Readonly<User>, name: string): User {
    return { ...user, name }
  }
  ```
- The spec MUST forbid direct mutations

## Validation

- **Zod** for schema-based validation:
  ```typescript
  const userSchema = z.object({
    email: z.string().email(),
    age: z.number().int().min(0).max(150)
  })
  type UserInput = z.infer<typeof userSchema>
  ```
- The spec MUST define validation schemas for all inputs

## Mandatory Anti-Patterns

The spec MUST list as forbidden:
- `console.log` in production code (use a logger)
- `any` in application code
- `React.FC` without justification
- Array-index-based keys
- Direct object/array mutations

## Security

- Secrets via `process.env`, never hardcoded
- Fail fast if secret missing at startup

## Testing

- E2E: **Playwright** for critical flows
- Selectors: `data-testid`, never CSS classes
- Wait for API responses, not arbitrary timeouts

## Review Checklist (`/code-review`)

### CRITICAL — Security

- `eval()` / `new Function()` with user input
- XSS: unsanitized input in `innerHTML`, `dangerouslySetInnerHTML`
- SQL/NoSQL injection: concatenation in queries
- Path traversal: user input in `fs.readFile`, `path.join`
- Prototype pollution: merging untrusted objects without validation
- `child_process` with user input without allowlist

### HIGH — Type Safety

- `any` without justification → `unknown` + narrowing
- Non-null assertion `value!` without guard
- `as` casts that bypass checks
- `tsconfig.json` modified to reduce strictness

### HIGH — Async Correctness

- Unhandled promises / missing `.catch()`
- Sequential `await` for independent operations → `Promise.all`
- Floating promises without error handling
- `array.forEach(async fn)` → `for...of` or `Promise.all`

### HIGH — Node.js

- `fs.readFileSync` in request handlers (blocking event loop)
- `process.env` access without fallback or startup validation
- `require()` in an ESM context

### MEDIUM — React / Next.js

- Incomplete dependency arrays in `useEffect`/`useCallback`/`useMemo`
- Direct state mutation
- `key={index}` in dynamic lists → stable IDs
- `useEffect` for derived state
- Client/server leaks (server-only modules in client components)

### MEDIUM — Performance

- Objects/arrays created inline in props (unnecessary re-renders)
- N+1 queries in loops
- `import _ from 'lodash'` → named imports

## Build & Lint Commands (`/build-fix`)

```bash
# Type checking
npm run typecheck --if-present
tsc --noEmit -p <tsconfig>

# Linting
eslint . --ext .ts,.tsx,.js,.jsx
prettier --check .

# Vulnerabilities
npm audit

# Tests
vitest run    # or jest --ci
```

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `TS2305: Module has no exported member` | Missing export | Add the export or check the path |
| `TS2322: Type X is not assignable to Y` | Type mismatch | Fix the type or add assertion |
| `TS7006: Parameter implicitly has 'any'` | Missing type | Add type annotation |
| `TS2345: Argument not assignable` | Incompatible args | Check overloads or fix |
| `Cannot find module` | Missing package | `npm install` or check paths |
