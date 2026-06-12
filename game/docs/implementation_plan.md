> **Status: IMPLEMENTED** — Wiki/Repo documentation split completed per ADR-009 (2026-05-27).

---

# Documentation Split & Global Readme Update

This plan details the partitioning of the existing documentation between the technical repository and the "human" wiki, as well as the redesign of the main README to reflect this new architecture.

## 1. Documentation Separation

### A. Human-Facing Documentation / Lore (To `game-wiki/`)
These documents are intended for Game Designers, Writers, and Players. They do not contain code implementation details.
- **[MOVE]** Move `game/docs/strategic/game_vision.md` to `game-wiki/Game_Vision.md`.
- **[NEW]** Create the base structure of the wiki (based on the current `Home.md`):
  - `game-wiki/GDD_Mechanics.md` (Game Design Document)
  - `game-wiki/Lore_Universe.md` (Lore, Characters)

### B. Technical Documentation (Remains in `game/docs/`)
These documents are intended for Developers and the AI.
- **[KEEP]** `game/docs/strategic/MASTER_ROADMAP.md` (Contains the code micro-versions and technical architecture).
- **[KEEP]** `game/docs/specs/` (All AI implementation specifications).
- **[KEEP]** `game/docs/ADRs/` (Architecture Decision Records).

## 2. Improving the Global README (`/README.md`)

The `README.md` file at the root will be refactored to become the showcase of the project and the entry point of the "Meta-Workspace".

**New README Structure:**
1. **Introduction & Global Vision:** Presentation of the RPG "The Heir's Awakening".
2. **Project Architecture (The Split):**
   - Clear link to the [GitHub Wiki](https://github.com/adrien-parasote/game/wiki) for Lore and Game Design.
   - Explanation of the technical structure (`game/`, `tools/`, `assets/`).
3. **Getting Started (Developers):** Instructions to run the game and procedural generation tools.
4. **Quality & AI (Stream Coding):** Mention of AI-assisted contribution rules and test coverage.

## User Review Required

> [!IMPORTANT]
> 1. Do you agree to keep the `MASTER_ROADMAP.md` in the technical side (since it contains the breakdown of code micro-versions), or do you want to extract a simplified version for the Wiki?
> 2. Is moving only the Vision (`game_vision.md`) to the Wiki suitable for you to start populating it?

Approve this plan and I will move the files, structure the Wiki, and rewrite the global README.
