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
| Map & Rendering | [map_rendering.md](learnings/map_rendering.md) | 25 | Map loading, rendering pipeline, depth, autotiles |
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
