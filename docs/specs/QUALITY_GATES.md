# Quality Gates and Standards [Reference]

This document defines the technical standards and verification criteria for the RPG Tile Engine.

## 1. The Quality Gates

To maintain a 10-20x velocity multiplier, all contributions must pass through the following automated and manual gates.

### I. Spec Gate (Documentation Quality)
- **Criterion**: Documents must be "AI-ready" (Actionable, Current, Single Source, Decision-based).
- **Mandatory Sections**: All implementation specs MUST include Anti-patterns, Test Case Specs, Error Handling Matrix, and Deep Links.
- **Score**: Must achieve a 10/10 Understandability Score before any code is written.

### II. TDD Gate (Verification-First)
- **Criterion**: No implementation code without RED tests.
- **Requirement**: Test files must exist and fail (RED) before any business logic is added.

### III. Verify Gate (Pre-Commit)
- **Criterion**: Full system verification.
- **Checks**:
    - **Linting**: Zero errors in logic or formatting.
    - **Static Analysis**: Zero high-risk findings (`bandit`).
    - **Tests**: 100% pass rate in the full test suite.
    - **Coverage**: >= 90% line coverage for core engine modules.

## 2. Technical Standards

### Logging Strategy
| Level | Description | Example Event |
|-------|-------------|---------------|
| **DEBUG** | Mathematical trace | Camera offset calculation, raw input bits |
| **INFO** | Core lifecycle | Engine init, map load, settings load |
| **WARNING** | Performance dip | FPS < 30, fallback to defaults used |
| **ERROR** | Recoverable failure | Missing entity texture, single asset load fail |
| **CRITICAL** | System failure | Pygame init fail, corrupted core map file |

### Development Principles
- **Portability**: Use `Settings` for all keys/constants; never access raw JSON in logic.
- **Stability**: Always apply `MAX_DT_CLAMP` (default: 10.0) in `update()` to prevent physics explosion after long pauses or debugging.
- **Cross-Platform**: Use `os.path` for all file path operations.
- **Cleanliness**: Files < 800 lines, methods < 50 lines. No nesting > 4 levels.

## 3. Deep Links
- [STRATEGIC_BLUEPRINT.md](../STRATEGIC_BLUEPRINT.md)
- [ENGINE_CORE.md](ENGINE_CORE.md)
