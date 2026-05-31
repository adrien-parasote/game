# 📚 Documentation Index

> **Quick orientation for AI agents and developers.**
> This file is the entry point for navigating the project documentation.

---

## Directory Structure

```
docs/
├── README.md              ← You are here
├── game/                  # Game engine & runtime documentation
│   ├── specs/             # Technical implementation specs (src/)
│   ├── strategic/         # Vision, roadmap, blueprints
│   ├── research/          # Discovery & research artifacts
│   └── ADRs/              # Architectural Decision Records
├── tooling/               # Developer tooling documentation (scripts/)
│   ├── specs/             # Specs for CLI utilities & asset pipelines
│   ├── strategic/         # Strategy docs for tooling features
│   └── research/          # Research for tooling decisions
├── codemaps/              # Auto-generated architecture maps (transversal)
├── traceability.md        # Spec↔Test traceability matrix (auto-generated)
└── traceability_report.md # Traceability coverage summary
```

---

## Game vs Tooling — How to Decide

| If the doc is about... | It goes in... |
|---|---|
| Runtime code in `src/` (engine, entities, UI, map, etc.) | `docs/game/` |
| Game vision, roadmap, feature blueprints | `docs/game/strategic/` |
| Architecture decisions affecting the game | `docs/game/ADRs/` |
| Scripts in `scripts/` (autotile converters, asset pipelines, release tools) | `docs/tooling/` |
| Cross-cutting concerns (codemaps, traceability) | `docs/` root |

---

## Key Entry Points

### Game Documentation
- **Master Spec Index:** [`game/specs/00_MASTER.md`](game/specs/00_MASTER.md) — Lists all 15+ game specs, global singletons, shared constants, and ADR links.
- **Game Vision:** [`game/strategic/game_vision.md`](game/strategic/game_vision.md) — Strategic vision for "The Heir's Awakening".
- **Master Roadmap:** [`game/strategic/MASTER_ROADMAP.md`](game/strategic/MASTER_ROADMAP.md) — Feature roadmap v0.5+.
- **ADRs:** [`game/ADRs/`](game/ADRs/) — 8 accepted architectural decisions (ADR-001 through ADR-008).

### Tooling Documentation
- **Asset Creator V1:** [`tooling/specs/asset_creator_spec.md`](tooling/specs/asset_creator_spec.md) — Procedural tileset generator (CLI, palette, texture, 47-tile blob).
- **Asset Creator V2:** [`tooling/specs/asset_creator_v2_texture_quality.md`](tooling/specs/asset_creator_v2_texture_quality.md) — OKLCh color ramps, smooth interpolation, dithering, detail overlays.
- **Asset Creator V3 GUI:** [`tooling/specs/asset_creator_v3_gui.md`](tooling/specs/asset_creator_v3_gui.md) — Dear PyGui interactive GUI with paint canvas.
- **Autotile Edge Pipeline:** [`tooling/specs/autotile-pipeline-spec.md`](tooling/specs/autotile-pipeline-spec.md) — RPG Maker XP → Tiled Wang Edge (16 tiles).
- **Autotile Blob Pipeline:** [`tooling/specs/blob_autotile_pipeline_spec.md`](tooling/specs/blob_autotile_pipeline_spec.md) — RPG Maker XP → Tiled Wang Blob (47 tiles).
- **Diagonal Wall Tool:** [`tooling/specs/diagonal_wall_spec.md`](tooling/specs/diagonal_wall_spec.md) — Flat wall → 45° diagonal tile transformation.

### Architecture Reference
- **Architecture Codemap:** [`codemaps/architecture.md`](codemaps/architecture.md)
- **Logic Codemap:** [`codemaps/logic.md`](codemaps/logic.md)
- **Data Codemap:** [`codemaps/data.md`](codemaps/data.md)

---

## Conventions

1. **Relative links only** — All cross-references between docs use relative paths (e.g., `../strategic/blueprint.md`), not absolute file:// URLs.
2. **Spec ↔ Blueprint pairing** — Each spec in `specs/` should link back to its strategic blueprint in `strategic/`, and vice versa.
3. **New docs** — When creating documentation for new features, place it in `game/` or `tooling/` based on the table above.
4. **Codemaps** — Auto-generated via `/update-codemaps`. Do not edit manually.
5. **Traceability** — Auto-generated via `scripts/dev/tc_report.py`. Do not edit manually.
