# Quality Gates and Standards [Reference]

> Document Type: Implementation


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
    - **Coverage**: >= 90% line coverage overall; 100% on `inventory_system.py`, `npc.py`, `audio.py`, `map/manager.py`, `spritesheet.py`, `emote_sprite.py`, `teleport.py`.
    - **Current status (2026-05-01):** 92% global, **436 tests passing** — domain-based layout: `tests/{engine,entities,map,ui,graphics}/`.

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
- [engine-core.md](engine-core.md)

## Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| [Fill me] | [Fill me] | [Fill me] |

## Test Case Specifications

### Unit Tests Required
| Test ID | Component | Input | Expected Output | Edge Cases |
|---------|-----------|-------|-----------------|------------|
| TC-001 | [Component] | [Input] | [Expected Output] | [Edge Cases] |

### Integration Tests Required
| Test ID | Flow | Setup | Verification | Teardown |
|---------|------|-------|--------------|----------|
| IT-001 | [Flow] | [Setup] | [Verification] | [Teardown] |

## Error Handling Matrix

| Error Type | Detection | Response | Fallback | Logging | Alert |
|------------|-----------|----------|----------|---------|-------|
| [Error] | [Detection] | [Response] | [Fallback] | [Logging] | [Alert] |

## Deep Links
- [Link description](file:///path/to/file#anchor)