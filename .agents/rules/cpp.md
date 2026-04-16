# C++ — Documentation Constraints

> The spec for a C++ project MUST cover these points.

## Version (the spec MUST specify)

- Prefer **C++17/20/23** features over C constructs
- `auto` when the type is obvious from context
- `constexpr` for compile-time constants
- Structured bindings: `auto [key, value] = map_entry;`

## Formatting (non-negotiable)

- **clang-format**: `clang-format -i <file>` before every commit
- No style debate

## Resource Management (CRITICAL)

- **RAII everywhere** — zero manual `new`/`delete`
- `std::unique_ptr` for exclusive ownership
- `std::shared_ptr` only if shared ownership is truly needed
- `std::make_unique` / `std::make_shared` over `new`

The spec MUST document all managed resources and ownership.

## Mandatory Patterns in the Spec

| Pattern | When to document |
|---------|-----------------|
| **RAII** | All resource management (files, sockets, locks) |
| **Rule of Five/Zero** | Every class — prefer Zero (no custom destructor) |
| **Value semantics** | Small types by value, large by `const&`, return by value (RVO) |
| **Move semantics** | Sink parameters |

## Error Handling

- Exceptions for exceptional conditions
- `std::optional` for values that may not exist
- `std::expected` (C++23) or result types for expected failures

## Naming

| Element | Convention |
|---------|-----------|
| Types/Classes | `PascalCase` |
| Functions/Methods | `snake_case` or `camelCase` (follow project) |
| Constants | `kPascalCase` or `UPPER_SNAKE_CASE` |
| Namespaces | `lowercase` |
| Members | `snake_case_` (trailing underscore) or `m_` prefix |

## Testing

- Coverage: 80%+

## Review Checklist (`/code-review`)

### CRITICAL — Memory Safety

- Raw `new`/`delete` → `std::unique_ptr` / `std::shared_ptr`
- Buffer overflows: C-style arrays, `strcpy`, `sprintf` without bounds
- Use-after-free: dangling pointers, invalidated iterators
- Uninitialized variables
- Memory leaks: non-RAII resources
- Null dereference without check

### CRITICAL — Security

- Command injection: input in `system()` or `popen()`
- Format string attacks: user input in `printf` format
- Integer overflow: unchecked arithmetic on untrusted input
- `reinterpret_cast` without justification

### HIGH — Concurrency

- Data races: shared mutable state without synchronization
- Deadlocks: multiple mutexes locked in inconsistent order
- Manual locks → `std::lock_guard` / `std::scoped_lock`
- `std::thread` without `join()` or `detach()`

### HIGH — Code Quality

- No RAII: manual resource management
- Rule of Five violations
- C-style code: `malloc`, C arrays, `typedef` instead of `using`

### MEDIUM — Performance

- Unnecessary copies of large objects → `const&`
- Missing move semantics for sink parameters
- String concatenation in a loop → `std::ostringstream` or `reserve()`
- Missing `reserve()` on vector with known size

### MEDIUM — Best Practices

- Missing `const` correctness
- `using namespace std;` in headers
- Missing include guards or unnecessary includes

## Build & Lint Commands (`/build-fix`)

```bash
# Diagnostic
cmake --build build 2>&1 | head -100
cmake -B build -S . 2>&1 | tail -30
clang-tidy --checks='*,-llvmlibc-*' src/*.cpp -- -std=c++17
cppcheck --enable=all --suppress=missingIncludeSystem src/

# Full rebuild
cmake --build build --clean-first
cmake -B build -S . -DCMAKE_VERBOSE_MAKEFILE=ON

# Tests
ctest --test-dir build
```

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `undefined reference to X` | Missing implementation or library | Add source file or link library |
| `no matching function for call` | Incorrect argument types | Fix types or add overload |
| `use of undeclared identifier` | Missing include | Add `#include` |
| `multiple definition of` | Duplicate symbol | `inline`, move to .cpp, or include guard |
| `incomplete type` | Insufficient forward declaration | Add full `#include` |
| `template argument deduction failed` | Incorrect template args | Fix template parameters |
