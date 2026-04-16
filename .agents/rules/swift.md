# Swift — Documentation Constraints

> The spec for a Swift project MUST cover these points.

## Formatting (non-negotiable)

- **SwiftFormat** for auto-formatting, **SwiftLint** for enforcement
- `swift-format` bundled with Xcode 16+ as alternative

## Immutability

- `let` > `var` — everything is `let`, change to `var` only if the compiler requires it
- `struct` with value semantics by default — `class` only if identity/reference semantics required

## Naming

- Follow the [Apple API Design Guidelines](https://www.swift.org/documentation/api-design-guidelines/)
- Clarity at the point of use — omit needless words
- Name by role, not by type
- `static let` for constants over global constants

## Error Handling

- Typed throws (Swift 6+) and pattern matching:
  ```swift
  func load(id: String) throws(LoadError) -> Item {
      guard let data = try? read(from: path) else {
          throw .fileNotFound(id)
      }
      return try decode(data)
  }
  ```
- The spec MUST document error types and recovery paths

## Concurrency

- Swift 6 strict concurrency checking enabled
- `Sendable` value types for data crossing isolation boundaries
- **Actors** for shared mutable state
- Structured concurrency (`async let`, `TaskGroup`) > unstructured `Task {}`

## Testing

- Coverage: 80%+

## Review Checklist (`/code-review`)

### CRITICAL — Security

- Hardcoded secrets in source
- Keychain not used for credentials → not `UserDefaults`
- ATS (App Transport Security) disabled without justification
- Unvalidated user input in URL schemes / deep links

### HIGH — Concurrency

- Data races: shared state without `actor` or synchronization
- Unstructured tasks (`Task {}`) → prefer `async let` / `TaskGroup`
- Missing `@MainActor` for UI updates
- Non-`Sendable` types crossing isolation boundaries

### HIGH — Memory

- Retain cycles: closures strongly capturing `self` → `[weak self]`
- Non-`weak` delegate
- Missing `deinit` cleanup

### MEDIUM — SwiftUI

- `@ObservedObject` where `@StateObject` should be used (creation in body)
- Views too large → extract into sub-components
- `onAppear` for derived state → use computed properties

### MEDIUM — Swift Idioms

- Force unwrap `!` on non-guaranteed optionals → `guard let` / `if let`
- `Any` / `AnyObject` instead of typed protocols
- API Design Guidelines violation (naming)

## Build & Lint Commands (`/build-fix`)

```bash
# Build
xcodebuild -scheme <Scheme> -destination 'platform=iOS Simulator,name=iPhone 16' build 2>&1 | tail -30
swift build 2>&1  # For SPM projects

# Lint
swiftlint lint --strict
swift-format lint -r Sources/

# Tests
swift test
xcodebuild test -scheme <Scheme> -destination 'platform=iOS Simulator,name=iPhone 16'
```
