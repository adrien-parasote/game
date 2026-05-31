# Strategic Blueprint: Domain-Driven Monorepo Migration

## 1. Problem Statement
The current repository structure mixes `docs`, `src`, `test`, `tools`, and `scripts` at the root level. This makes the project architecture unreadable and fluid navigation impossible. Most importantly, game code and tooling code are fundamentally distinct domains that require their own separate documentation, source code, and tests, but they are currently entangled.

## 2. Success Metrics
- **Clear Delimitation:** Strict, zero-ambiguity boundaries between game code, tools, and assets.
- **Domain-Specific Documentation:** Both `/game` and `/tools` have their own isolated `docs/` and `src/` folders.
- **Onboarding Speed:** A new developer can understand the project architecture in under 5 minutes without needing a guide.

## 3. Why This Approach Wins
By adopting a **Domain-Driven Monorepo**, we get the best of both worlds:
- **Evolution Simplified:** Tools and game code can evolve independently while still sharing the same Git history, allowing atomic commits (updating a tool and the game it affects simultaneously).
- **Onboarding Facilitated:** The cognitive load is drastically reduced because a developer working on the game doesn't see tooling code, and vice versa.

## 4. Core Architecture Decision
We are keeping a **Monorepo** but transforming the root hierarchy into "Domains".

**Proposed Root Structure:**
```text
/game
  /src
  /test
  /docs
/tools
  /src
  /test
  /docs
/assets
  /images
  /sounds
  /tiled
/scripts
  (global repository automation)
```
*See ADR 0001 for details.*

## 5. Technical Rationale (Git LFS)
The user explicitly stated "no need for Git LFS", and after verifying the repository, the `/assets` directory is only 8.5MB. Git is perfectly capable of handling this natively without performance degradation. We will not introduce Git LFS or any submodule complexity at this stage, as it would add unnecessary overhead. We will strictly use standard Git tracking for the Monorepo.

## 6. Migration Features (Execution Order)
1. **Prepare the Root:** Create the new `/game`, `/tools`, and `/assets` directories.
2. **Migrate Game:** Move the game-specific `src`, `test`, and `docs` into `/game/`.
3. **Migrate Tools:** Move tool-specific code and docs into `/tools/`.
4. **Migrate Assets:** Move all visual, audio, and tiled assets into `/assets/`.
5. **Update Paths:** Fix all broken paths in build scripts, imports, and documentation.

## 7. What We Are NOT Building
- We are **not** splitting the project into multiple GitHub repositories (no polyrepo).
- We are **not** using Git LFS, Submodules, or DVC.
- We are **not** refactoring the actual source code of the game or tools; this is purely a structural file migration.
- We are **not** changing the build systems (e.g., Make, CMake, npm) beyond fixing their internal file paths.
