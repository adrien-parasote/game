# ADR 0001: Domain-Driven Monorepo Architecture

## Status
Proposed

## Context
The project is growing and currently has a flat structure at the root (`docs`, `src`, `test`, `tools`, `scripts`), mixing game code, tooling code, and assets. 
This lack of delimitation makes onboarding difficult and the repository hard to read. Furthermore, `src` (the game) and `tools` are distinct elements—one feeds the other—and require their own separate documentation, testing, and source directories. 

The decision is whether to split into multiple repositories (polyrepo) or reorganize the current repository (monorepo).

## Decision
We will adopt a **Domain-Driven Monorepo Structure**.

Instead of splitting into multiple repositories, we will restructure the current repository into three isolated top-level domains:
1. `/game` (contains its own `src/`, `tests/`, `docs/`)
2. `/tools` (contains its own `src/`, `tests/`, `docs/`)
3. `/assets` (contains all binary and visual assets: tiled, images, sound)
4. `/scripts` (global repository automation, CI/CD)

### Git LFS Requirement
**Decision:** We are NOT implementing Git LFS at this stage. The current `assets/` directory is 8.5MB, which is well within Git's native handling capabilities. Implementing LFS now would add unnecessary overhead. We will monitor the repository size and only consider LFS if the asset footprint grows significantly (e.g., > 500MB).

## Consequences

### Positive
- **Clear Delimitation:** Game code, tools, and assets are physically separated at the root.
- **Isolated Documentation:** `tools` and `game` have their own `docs/` folders, preventing confusion.
- **Atomic Commits:** A developer can still update a tool and the game code that relies on it in a single pull request.
- **Onboarding:** A new game developer only needs to look inside `/game`; a tools developer only inside `/tools`.

### Negative
- Requires a one-time migration to move files into their respective domains.
- Path references in existing scripts and tools will break and must be updated.
