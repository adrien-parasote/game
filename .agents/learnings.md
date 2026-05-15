# Project Learnings Registry

> **Usage:** Lire avant toute session BUILD. Chaque entrée = un pattern ou anti-pattern confirmé avec evidence.
> **Format:** `ID · Date · Scope [P=project-specific | U=universal] · Outcome`

## Domains

| Domaine | Fichier | Entrées | Quand lire |
|---------|---------|---------|-----------|
| Audio & Engine Setup | [audio_engine.md](learnings/audio_engine.md) | 6 | Session audio, SFX, BGM, init pygame mixer |
| Testing & Traceability | [testing.md](learnings/testing.md) | ~26 | Tout BUILD — le plus riche, lire en priorité |
| Game Engine & Architecture | [game_engine.md](learnings/game_engine.md) | ~15 | Architecture, refactoring, performance engine |
| Map & Rendering | [map_rendering.md](learnings/map_rendering.md) | ~11 | Map loading, rendering pipeline, depth, autotiles |
| UI & UX | [ui.md](learnings/ui.md) | ~18 | Tout travail UI (ChestUI, PauseScreen, dialogue, halos) |
| Methodology, Agent & Docs | [methodology_and_docs.md](learnings/methodology_and_docs.md) | ~12 | Workflow agents, spec writing, doc urbanization |

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
