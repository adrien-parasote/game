# Project Learnings Registry

> **Usage:** Lire avant toute session BUILD. Chaque entrée = un pattern ou anti-pattern confirmé avec evidence.
> **Format:** `ID · Date · Scope [P=project-specific | U=universal] · Outcome`

> **⛔ RÈGLE PERMANENTE — LEARNINGS HUB : LECTURE SEULE :**
> `pull_learnings`, `search_learnings`, `auth_status`, `auth_login` sont **autorisés** (lecture depuis le Hub).
> `submit_learning` est **interdit** sur ce projet — ne jamais soumettre de learnings au Hub.
> Les learnings projet sont maintenus **uniquement** dans `.agents/learnings/`. Step 4b de `/learn-eval` est systématiquement skippé.


## Domains

| Domaine | Fichier | Entrées | Quand lire |
|---------|---------|---------|-----------|
| Audio & Engine Setup | [audio_engine.md](learnings/audio_engine.md) | 6 | Session audio, SFX, BGM, init pygame mixer |
| Testing & Traceability | [testing.md](learnings/testing.md) | 51 | Tout BUILD — le plus riche, lire en priorité |
| Game Engine & Architecture | [game_engine.md](learnings/game_engine.md) | 30 | Architecture, refactoring, performance engine |
| Map & Rendering | [map_rendering.md](learnings/map_rendering.md) | 26 | Map loading, rendering pipeline, depth, autotiles |
| UI & UX | [ui.md](learnings/ui.md) | 25 | Tout travail UI (ChestUI, PauseScreen, dialogue, halos) |
| Tooling & Utilities | [tooling.md](learnings/tooling.md) | 7 | Développement d'outils, scripts de conversion, Asset Convertor |
| Methodology, Agent & Docs | [methodology_and_docs.md](learnings/methodology_and_docs.md) | 36 | Workflow agents, spec writing, doc urbanization |

## Convention de nommage des IDs

```
L-DOMAINE-NNN  → Learning (pattern confirmé)
A-DOMAINE-NNN  → Anti-pattern (piège à éviter)

Domaines : GAME, ARCH, REND, PERF, MAP, SPRITE,
           UI, UX, STATIC, TEST, TRACE, INFRA,
           SPEC, AGENT, DOC, AUDIO
```

**Règle L-DOC-005 :** Un learning = un seul fichier domaine. Avant d'ajouter, vérifier avec :
```bash
grep -rn "L-NOM-ID" .agents/learnings/
# Si présent dans 2 fichiers → supprimer le duplicata
```

## Note historique

`rendering_depth_regression.md` — fichier tombstone supprimé le 2026-05-15 (contenu migré en `L-REND-004` dans `map_rendering.md`).

### A-SPEC-007 · 2026-06-12 · U · Major Rework — Sanitization Bias & Adversarial Review False Positives
> ⚠️ Migrate to `methodology_and_docs.md` per L-DOC-005 (one learning = one domain file).
- **Source:** game — stair-movement.md
- **Evidence:** Bypassed Spec Gate and committed code directly to fix 8 broken unit tests caused by a false positive from an earlier Adversarial Review.
- **Anti-pattern:** Accepting an Adversarial Review "CRITICAL" finding as absolute truth without verifying unit tests first. Removed an intentional fallback mechanism for dynamic grid geometry, breaking the test suite. Subsequently skipped Spec Gate and TDD gates to quickly revert.
- **Fix:** Adversarial Review findings are hypotheses, not facts. Verify findings against existing tests before altering specs. Never skip Spec Gate after a regression — fix spec first, then code.

### L018: Dynamic entities require dynamic cache keys
- **Date:** 2026-06-13
- **Source:** game — render_occlusion
- **Evidence:** Player animation froze visually while moving because `OcclusionRenderer` cache key only used static `camera_offset` and `len(rects)`.
- **Anti-pattern:** Caching composite visual surfaces of dynamic entities using only environment/static state keys (like camera position).
- **Fix:** Include the dynamic entity's state (e.g., `is_moving` or `frame_index`) in the cache invalidation logic, or bypass the cache entirely for moving entities.

### L019: Swapped stair direction mappings cause collision blockages
- **Date:** 2026-06-19
- **Source:** game — stair-movement (STAIR_BEHAVIOR in config.py)
- **Evidence:** Player got blocked trying to move right in basement staircase, triggering descending step-off and solid wall collision.
- **Anti-pattern:** Mismatch between visual stair tileset properties and engine behavioral mapping keys (`up,left` vs `up,right`).
- **Fix:** Ensure the second parameter (`left`/`right`) of compound stair directions consistently maps to the entry side (lowest step visually) for both `up` and `down` assets. In this case, swap `up,left` and `up,right` in the engine's STAIR_BEHAVIOR move_map.

### L020: Overlapping layer collision property leakage
- **Date:** 2026-06-19
- **Source:** game — manager.py (get_vertical_move_props layer scan)
- **Evidence:** Player got stuck at basement stairs bottom coordinates `(29, 35)` and `(30, 35)` because visual overlays (banisters) on `02-layer` had been misconfigured with `movement_type="ladder"` in `01-stairs.tsx`. Since layer scanning is top-down, the engine resolved the cell as a ladder instead of stairs, blocking horizontal movement.
- **Anti-pattern:** Placing movement-restricting properties (like ladders or stairs) on foreground/decorative overlay tiles (which are on higher layers) when those coordinates already have a physical movement tile (like stairs or walkable floors) on a lower layer. Top-down layer resolution will incorrectly resolve the decoration's class behavior instead of the physical floor behavior.
- **Fix:** Ensure decorative/foreground overlays on higher layers (like handrails or wall borders) never contain movement class properties (like `movement_type` or `stair_direction`). Keep overlays as pure visual decorations (`depth >= 1`), letting the parser fall back to the underlying physical tiles on lower layers (`01-layer` or `00-layer`) to determine movement physics.

