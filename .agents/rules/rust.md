# Rust — Documentation Constraints

> The spec for a Rust project MUST cover these points.

## Formatting (non-negotiable)

- **rustfmt**: `cargo fmt` before every commit
- **clippy**: `cargo clippy -- -D warnings` (warnings = errors)

## Ownership and Borrowing

The spec MUST document ownership choices:
- Borrow (`&T`) by default — ownership only if storing/consuming
- `&str` > `String`, `&[T]` > `Vec<T>` in function parameters
- `impl Into<String>` for constructors that need to own
- **Never** `clone()` to satisfy the borrow checker without understanding the cause

```rust
// GOOD — borrows
fn word_count(text: &str) -> usize { text.split_whitespace().count() }

// GOOD — ownership via Into for constructor
fn new(name: impl Into<String>) -> Self { Self { name: name.into() } }
```

## Immutability

- `let` by default, `let mut` only when mutation is required
- `Cow<'_, T>` when a function may or may not allocate
- Prefer returning new values over mutating in-place

## Error Handling

- `Result<T, E>` + `?` for propagation — never `unwrap()` in production
- **Libraries**: typed errors with `thiserror`
- **Applications**: `anyhow` for flexible context
- `.with_context(|| format!("failed to ..."))?` to add context
- `unwrap()` / `expect()` reserved for tests and provably unreachable states

```rust
// Library
#[derive(Debug, thiserror::Error)]
pub enum ConfigError {
    #[error("failed to read config: {0}")]
    Io(#[from] std::io::Error),
}

// Application
fn load_config(path: &str) -> anyhow::Result<Config> {
    let content = std::fs::read_to_string(path)
        .with_context(|| format!("failed to read {path}"))?;
    toml::from_str(&content).with_context(|| format!("failed to parse {path}"))
}
```

## Mandatory Patterns in the Spec

| Pattern | When to document |
|---------|-----------------|
| **Newtype** | Prevent argument mix-ups (`UserId(u64)` vs `OrderId(u64)`) |
| **Enum state machines** | Model states — make illegal states unrepresentable |
| **Builder** | Structs with many optional parameters |
| **Sealed traits** | Control extensibility (prevent external implementations) |
| **Iterators > loops** | Declarative, composable transformations |

```rust
// Newtype
struct UserId(u64);
struct OrderId(u64);

// Enum state machine — exhaustive match, never wildcard `_` for business enums
enum ConnectionState {
    Disconnected,
    Connecting { attempt: u32 },
    Connected { session_id: String },
    Failed { reason: String, retries: u32 },
}
```

## Security

- Every `unsafe` block MUST have a `// SAFETY:` comment explaining the invariant
- Never `unsafe` to work around the borrow checker by convenience
- **cargo audit** for CVEs
- **cargo deny check** for licenses and advisories
- `cargo tree -d` to audit transitive dependencies
- SQL: parameterized queries (sqlx `$1` / diesel bind)
- Input validation: "Parse, don't validate" — convert unstructured data into types

## Testing

- Unit tests: `#[cfg(test)] mod tests` in the same file
- Integration tests: `tests/` (each file = separate binary)
- **rstest** for parameterized tests
- **proptest** for property-based tests
- **mockall** for trait mocking
- **`#[tokio::test]`** for async tests
- Coverage: `cargo llvm-cov --fail-under-lines 80`

## Visibility

- Private by default, `pub(crate)` for internal sharing
- `pub` only for the crate's public API
- Re-export public API from `lib.rs`

## Review Checklist (`/code-review`)

### CRITICAL — Safety

- `unwrap()`/`expect()` unjustified in production → `?` or explicit handle
- `unsafe` without `// SAFETY:` comment documenting invariants
- SQL injection: interpolation in queries
- Command injection: unvalidated input in `std::process::Command`
- Untrusted deserialization without size/depth limits
- Use-after-free via raw pointers

### CRITICAL — Error Handling

- `let _ = result;` on `#[must_use]` types
- `return Err(e)` without `.context()` / `.map_err()`
- `panic!()`, `todo!()`, `unreachable!()` in production
- `Box<dyn Error>` in libraries → `thiserror`

### HIGH — Ownership and Lifetimes

- `.clone()` to satisfy the borrow checker without understanding the cause
- `String` instead of `&str` as parameter
- `Vec<T>` instead of `&[T]` as parameter
- Missing `Cow` when allocation is conditional
- Over-annotated lifetimes (elision suffices)

### HIGH — Concurrency

- Blocking in async: `std::thread::sleep`, `std::fs` → tokio equivalents
- Unbounded channels without justification → bounded
- `PoisonError` from `.lock()` unhandled
- Types shared between threads without `Send`/`Sync`
- Deadlock: nested lock acquisition without consistent ordering

### MEDIUM — Performance

- `to_string()` / `to_owned()` in hot paths
- Repeated allocation in loops
- `Vec::new()` when size is known → `Vec::with_capacity(n)`
- `.cloned()` in iterators when borrowing suffices

### MEDIUM — Best Practices

- Clippy warnings suppressed with `#[allow]` without justification
- Missing `#[must_use]` on critical return types
- `pub` items without `///` documentation
- Wildcard match `_ =>` hiding business variants

## Build & Lint Commands (`/build-fix`)

```bash
# Diagnostic (in this order)
cargo check 2>&1
cargo clippy -- -D warnings 2>&1
cargo fmt --check 2>&1
cargo tree --duplicates 2>&1
cargo audit 2>/dev/null || echo "cargo-audit not installed"
cargo deny check 2>/dev/null || echo "cargo-deny not installed"

# Tests
cargo test
cargo llvm-cov --fail-under-lines 80
```

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `cannot borrow as mutable` | Active immutable borrow | Restructure to end immutable borrow first |
| `does not live long enough` | Value dropped during borrow | Extend scope, use owned type |
| `cannot move out of` | Move behind a reference | `.clone()`, `.to_owned()`, or restructure |
| `trait X is not implemented for Y` | Missing impl or derive | `#[derive(Trait)]` or manual impl |
| `async fn is not Send` | Non-Send type held across `.await` | Drop before the `.await` |

### Cargo troubleshooting

```bash
cargo tree -d                          # Duplicates
cargo tree -i some_crate               # Who depends on this?
cargo check --workspace                # All members
cargo update -p specific_crate         # Targeted update
```
