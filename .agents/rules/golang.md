# Go — Documentation Constraints

> The spec for a Go project MUST cover these points. If an item is not documented, the Spec Gate does not pass.

## Formatting (non-negotiable)

- **gofmt** and **goimports** mandatory — no style debate
- Verify in spec: "CI runs `gofmt -d` and `goimports`"

## Design

- **Accept interfaces, return structs** — functions consume interfaces, produce concrete types
- Small interfaces: 1-3 methods max
- Define interfaces **where they are used**, not where they are implemented

## Error Handling

- Always wrap errors with context:
  ```go
  return fmt.Errorf("failed to create user: %w", err)
  ```
- The spec MUST list possible errors and their messages

## Mandatory Patterns in the Spec

| Pattern | When to document |
|---------|-----------------|
| **Functional options** | Constructors with > 2 optional params |
| **Dependency injection** | Any service with external dependencies |
| **Context with timeout** | Any network, DB, or external I/O call |
| **Table-driven tests** | All unit tests |

```go
// Functional options — the spec must indicate this pattern
type Option func(*Server)
func WithPort(port int) Option { return func(s *Server) { s.port = port } }
func NewServer(opts ...Option) *Server { ... }

// DI — the spec must document injected dependencies
func NewUserService(repo UserRepository, logger Logger) *UserService { ... }
```

## Security

- **gosec** for static analysis: `gosec ./...`
- **context.WithTimeout** on every external call:
  ```go
  ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
  defer cancel()
  ```
- The spec MUST specify timeouts per external service

## Testing

- Framework: `go test` standard
- **Always** `-race` flag: `go test -race ./...`
- Coverage: `go test -cover ./...`

### Coverage Targets

| Code Type | Target |
|-----------|--------|
| Critical business logic | 100% |
| Public APIs | 90%+ |
| General code | 80%+ |
| Generated code | Exclude |

### Mandatory Test Patterns

```go
// Table-driven tests (ALWAYS use this pattern)
tests := []struct {
    name    string
    input   InputType
    want    OutputType
    wantErr bool
}{
    {"case 1", input1, want1, false},
    {"edge case", input2, want2, true},
}
for _, tt := range tests {
    t.Run(tt.name, func(t *testing.T) {
        got, err := Function(tt.input)
        // assertions
    })
}

// Parallel tests — capture loop variable
for _, tt := range tests {
    tt := tt // capture
    t.Run(tt.name, func(t *testing.T) {
        t.Parallel()
        // test body
    })
}

// Test helpers — use t.Helper() + t.Cleanup()
func setupTestDB(t *testing.T) *sql.DB {
    t.Helper()
    db := createDB()
    t.Cleanup(func() { db.Close() })
    return db
}
```

## Review Checklist (`/code-review`)

> What `/code-review` must check specifically for Go, in addition to the universal checklist.

### CRITICAL — Security

- SQL injection: string concatenation in `database/sql`
- Command injection: unvalidated input in `os/exec`
- Path traversal: user file paths without `filepath.Clean` + prefix check
- Race conditions: shared state without synchronization
- `unsafe` package without justification
- `InsecureSkipVerify: true` in TLS config

### CRITICAL — Error Handling

- Errors ignored with `_` (unless documented as intentional)
- `return err` without wrapping (`fmt.Errorf("context: %w", err)`)
- `panic()` for recoverable errors
- `err == target` instead of `errors.Is(err, target)`

### HIGH — Concurrency

- Goroutine leaks: no cancellation mechanism (`context.Context`)
- Deadlock on unbuffered channel
- Missing `sync.WaitGroup` for coordination
- Mutex without `defer mu.Unlock()`

### HIGH — Code Quality

- `if/else` instead of early return
- Mutable package-level variables (global state)
- Interface pollution (unused abstractions)

### MEDIUM — Performance

- String concatenation in a loop → `strings.Builder`
- Slice without pre-allocation → `make([]T, 0, cap)`
- N+1 queries in loops

### MEDIUM — Idioms

- `ctx context.Context` must be the first parameter
- Error messages: lowercase, no punctuation
- Package naming: short, lowercase, no underscores
- `defer` in a loop → risk of resource accumulation

## Build & Lint Commands (`/build-fix`)

```bash
# Diagnostic (in this order)
go build ./...
go vet ./...
staticcheck ./... 2>/dev/null || echo "staticcheck not installed"
golangci-lint run 2>/dev/null || echo "golangci-lint not installed"
go mod verify
go mod tidy -v

# Tests
go test -race ./...
go test -cover ./...
govulncheck ./...
```

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `undefined: X` | Missing import, typo, unexported | Add import or fix casing |
| `cannot use X as type Y` | Type mismatch | Type conversion or dereference |
| `X does not implement Y` | Missing method | Implement with correct receiver |
| `import cycle not allowed` | Circular dep | Extract shared types into new package |
| `declared but not used` | Unused var/import | Remove or blank identifier |

### Module troubleshooting

```bash
grep "replace" go.mod              # Check local replaces
go mod why -m package              # Why this version
go get package@v1.2.3              # Pin a version
go clean -modcache && go mod download  # Fix checksum
```
