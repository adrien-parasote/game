# Kotlin — Documentation Constraints

> The spec for a Kotlin project MUST cover these points.

## Formatting (non-negotiable)

- **ktlint** or **Detekt** for enforcement
- `kotlin.code.style=official` in `gradle.properties`

## Immutability

- `val` > `var` — everything is `val` by default, `var` only if mutation required
- `data class` for value types, immutable collections (`List`, `Map`, `Set`) in public APIs
- Copy-on-write: `state.copy(field = newValue)`

## Null Safety (CRITICAL)

- **Never `!!`** — prefer `?.`, `?:`, `requireNotNull()`, `checkNotNull()`
- `?.let {}` for scoped null-safe operations
- Return nullable types for functions legitimately without result

```kotlin
// BAD — the spec must forbid !!
val name = user!!.name

// GOOD
val name = user?.name ?: "Unknown"
val name = requireNotNull(user) { "User must be set" }.name
```

## Sealed Types

- Use sealed classes/interfaces for closed state hierarchies
- Exhaustive `when` on sealed types — **never an `else` branch**

```kotlin
sealed interface UiState<out T> {
    data object Loading : UiState<Nothing>
    data class Success<T>(val data: T) : UiState<T>
    data class Error(val message: String) : UiState<Nothing>
}
```

## Scope Functions

| Function | Usage |
|----------|-------|
| `let` | null check + transform |
| `run` | compute result with receiver |
| `apply` | configure an object |
| `also` | side effects |

Max 2 nesting levels.

## Error Handling

- `Result<T>` or custom sealed types
- `runCatching {}` to wrap throwable code
- **Never catch `CancellationException`** — always rethrow
- No `try-catch` for control flow

## Testing

- Coverage: 80%+

## Review Checklist (`/code-review`)

### CRITICAL — Architecture

- Domain module imports Android/framework → domain must be pure Kotlin
- Entities/DTOs exposed to presentation layer → map to domain models
- Business logic in ViewModels → extract into UseCases
- Circular dependencies between modules

### CRITICAL — Security (Android)

- Exported components (Activities, Services) without guards
- Insecure crypto or storage (plaintext secrets, weak keystore)
- Unsafe WebView (JavaScript bridges, cleartext traffic)
- Tokens/credentials/PII in logs

### HIGH — Coroutines & Flows

- `GlobalScope` → use structured scopes (`viewModelScope`, `coroutineScope`)
- Catching `CancellationException` → always rethrow
- Missing `withContext(Dispatchers.IO)` for DB/network calls
- Mutable collections in `StateFlow` → copy (`state.copy(items = items + newItem)`)
- `stateIn(scope, SharingStarted.Eagerly)` → often `WhileSubscribed` is preferable

### HIGH — Compose

- Unstable parameters → unnecessary recompositions
- Side effects outside `LaunchedEffect`
- `NavController` passed deeply → pass lambdas instead
- Missing `key()` in `LazyColumn`
- Objects allocated inline in params → `remember`

### MEDIUM — Kotlin Idioms

- `!!` → `?.`, `?:`, `requireNotNull`
- `var` where `val` suffices
- Java-style patterns (static utility classes → top-level functions)
- Mutable collections exposed → return `List` not `MutableList`
- Non-exhaustive `when` on sealed types

### MEDIUM — Android Specific

- Context leaks: `Activity`/`Fragment` stored in singletons/ViewModels
- Hardcoded strings → `strings.xml` or Compose resources
- Flow collected in Activity without `repeatOnLifecycle`

## Build & Lint Commands (`/build-fix`)

```bash
# Diagnostic
./gradlew build 2>&1
./gradlew detekt 2>&1 || echo "detekt not configured"
./gradlew ktlintCheck 2>&1 || echo "ktlint not configured"
./gradlew dependencies --configuration runtimeClasspath 2>&1 | head -100

# Tests
./gradlew test

# Troubleshooting
./gradlew build --refresh-dependencies
./gradlew clean && rm -rf .gradle/build-cache/
./gradlew dependencyInsight --dependency <name> --configuration runtimeClasspath
```

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Unresolved reference: X` | Missing import/dependency | Add import or dependency |
| `Type mismatch: Required X, Found Y` | Wrong type | Conversion or fix |
| `Smart cast impossible` | Mutable property / concurrent access | Local `val` or `let` |
| `'when' expression must be exhaustive` | Missing branch | Add missing branches |
| `Suspend function can only be called from coroutine` | Missing `suspend` | Add modifier or launch coroutine |
