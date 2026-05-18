# Technical Specification: Documentation Language Urbanization

> **Document Type:** Implementation
> **Status:** APPROVED — 2026-05-18
> **Methodology Stage:** SPEC Gate Validation

This specification details the translation dictionary, terminology mapping, link integrity constraints, and quality gates for the language urbanization of the RPG game's documentation.

---

## 1. RPG & Engine Translation Dictionary

To maintain absolute consistency across all translated documents, the following technical terms and in-game names must be mapped uniformly:

| French Original | English Urbanized | Technical Context / Rationale |
|-----------------|-------------------|--------------------------------|
| `Castel` | `Castel` | Named in-game castle/hub (keep capitalized as `Castel`). |
| `Majordome` | `Butler` | Represents the player's mechanical guardian companion (`02-butler.png`). |
| `Sauvegarde` | `Save` / `Save System` | Relates to `SaveManager` and slot persistence. |
| `Miniature` | `Thumbnail` | Squared 120x120px player screenshot crop stored in `saves/slot_N_thumb.png`. |
| `Menu de pause` | `Pause Screen` / `Pause Menu` | Corresponds to the `PauseScreen` UI class. |
| `Menu principal` | `Title Screen` / `Main Menu` | Corresponds to the `TitleScreen` UI class. |
| `Bouton retour` | `Back Button` | Renders with I18n `menu.back`. |
| `Walkability` | `Walkability` | Movement permission model mapped to `walkable` tile property. |
| `Autotiles directionnels` | `Directional Autotiles` | Allowed direction flags check on tile departure. |
| `Pont-levis` / `Pont` | `Drawbridge` / `Bridge` | Mapped to the `bridge` interactive entity subtype. |
| `Éther` / `Éthéré` | `Ether` / `Ethereal` | Magical energy currency used in the progression system. |
| `Sphérier` | `Sphere Grid` | Node-based character progression system. |
| `Festin` | `Feast` / `Banquet` | In-game cozy cooking items triggering seasonal festivals. |
| `Familiers` | `Familiars` | Tamable wild creatures/monsters supporting the player. |
| `Amitié PNJ` | `NPC Friendship` | Dialogue and routing unlocking mechanic. |
| `Météo` | `Weather` / `Weather System` | Environmental status effects affecting stats. |

---

## 2. Link Integrity Constraints

When translating files, every Markdown link must be carefully checked. 

### 2.1 Deep Links to Source Files
Deep links pointing to specific source files or line numbers must remain fully functional. The relative path depth must not change.
*Example:* `[inventory.py L21](../../src/engine/inventory_system.py#L21)` -> `[inventory.py L21](../../src/engine/inventory_system.py#L21)`.

### 2.2 Links between Specifications
All internal links between specification documents under `docs/specs/` must remain `./filename.md` relative links.
*Example:* `[engine-core.md](./engine-core.md#L1)` -> `[engine-core.md](./engine-core.md#L1)`.

---

## 3. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Translate code variables, methods, or class names (e.g. `is_on` as `est_allume`) | Keep all code symbols in backticks exactly as they are in Python | Translation of variables breaks code-conformance check tools and AI comprehension |
| Change or translate Test Case IDs (e.g. `SAVE-U-001` to `SAUV-U-001`) | Retain exact Test Case IDs in all test specification tables | Test Case IDs are mapped to python test functions and are tracked by verification gating |
| Use machine-specific absolute paths (e.g. `file:///Users/adrien/...`) | Use relative paths from the document's directory | Ensures portability across different developer machines and CI pipelines (L-DOC-001) |
| Leave comments, subtitles, or page notes in French | Translate every single word outside of strict code identifiers to English | Ensures 100% urbanization completeness and matches user requirement |
| Add new features or structural modifications during translation | Perform a pure semantic translation | Prevents scope creep and avoids introducing regressions into validated specifications |

---

## 4. Test Case Specifications (Translation Audit)

We will perform a complete file-by-file post-translation audit to verify:
- **UT-TR-001**: 100% absence of French characters/phrases in the final documents.
- **UT-TR-002**: Verification that all deep links resolved to valid, existing paths.
- **UT-TR-003**: 100% validation of all Test Case ID matches in specifications.
