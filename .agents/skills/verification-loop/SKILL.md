---
name: verification-loop
description: |
  [LOCAL OVERRIDE — game workspace]
  Post-implementation quality gate avec détection automatique du sous-projet.
  Exécute verify.py sur game/ OU tools/ selon les fichiers modifiés.
  Fallback vers les deux si aucun sous-projet détecté.
---

# /verification-loop — Quality Verification (game workspace)

> **Override local** : Ce skill remplace le plugin global pour ce projet.
> La logique de détection du sous-projet est appliquée **avant** toute vérification.

## Différence avec le plugin global

Le plugin global lance `verify.py .` sur l'ensemble du workspace.
Ce skill local détecte automatiquement le sous-projet cible (`game/` ou `tools/`)
et lance `verify.py` **uniquement dans ce répertoire**.

---

## Étape 0 : Détection du sous-projet (OBLIGATOIRE)

Avant tout, détecter quel sous-projet est concerné :

```bash
# Détection automatique (basée sur les fichiers git modifiés)
python3 .agents/skills/verification-loop/scripts/detect_subproject.py --verbose
```

**Résultat possible :**

| Résultat | Signification | Action |
|----------|---------------|--------|
| `game`   | Fichiers dans `game/` modifiés | Vérifier uniquement `game/` |
| `tools`  | Fichiers dans `tools/` modifiés | Vérifier uniquement `tools/` |
| `all`    | Aucun sous-projet détecté ou les deux | Vérifier `game/` puis `tools/` |

**Override explicite possible :**

```bash
# Forcer un sous-projet spécifique
python3 .agents/skills/verification-loop/scripts/detect_subproject.py --subproject game
python3 .agents/skills/verification-loop/scripts/detect_subproject.py --subproject tools
python3 .agents/skills/verification-loop/scripts/detect_subproject.py --subproject all
```

---

## Étape 1 : Vérification du sous-projet détecté

### Si `game` détecté :

```bash
cd /Users/adrien.parasote/Documents/perso/game/game && \
  python ../.agents/skills/verification-loop/scripts/verify.py . \
  || python /Users/adrien.parasote/.gemini/config/plugins/stream-coding/skills/verification-loop/scripts/verify.py .
```

**Chemin de résolution du script `verify.py` :**
1. `.agents/skills/verification-loop/scripts/verify.py` (local, depuis workspace root)
2. Plugin global : `/Users/adrien.parasote/.gemini/config/plugins/stream-coding/skills/verification-loop/scripts/verify.py`

> ⚠️ `verify.py` doit être appelé depuis le répertoire du sous-projet (`game/` ou `tools/`).

### Si `tools` détecté :

```bash
cd /Users/adrien.parasote/Documents/perso/game/tools && \
  python ../.agents/skills/verification-loop/scripts/verify.py . \
  || python /Users/adrien.parasote/.gemini/config/plugins/stream-coding/skills/verification-loop/scripts/verify.py .
```

### Si `all` (fallback) :

Exécuter **séquentiellement** `game` puis `tools`.
Arrêter si l'un échoue (sauf si `--continue-on-fail` est demandé).

```bash
# game d'abord
cd /Users/adrien.parasote/Documents/perso/game/game && \
  python ../.agents/skills/verification-loop/scripts/verify.py .

# puis tools
cd /Users/adrien.parasote/Documents/perso/game/tools && \
  python ../.agents/skills/verification-loop/scripts/verify.py .
```

---

## Étapes 2-8 : Identiques au plugin global

Une fois le sous-projet ciblé, suivre le même protocole que le plugin global :

- **Phase 1** : Build verification
- **Phase 2** : Type check
- **Phase 3** : Lint
- **Phase 4** : Test suite (`pytest` dans le sous-projet)
- **Phase 5** : Security scan
- **Phase 6** : Spec conformance (depuis les specs du sous-projet : `game/docs/` ou `tools/docs/`)
- **Phase 7** : Silent failure hunting
- **Phase 8** : AI-generated code audit

Pour le détail de chaque phase, charger le step file du plugin global :
`.gemini/config/plugins/stream-coding/skills/verification-loop/steps/01-running-verification.md`

---

## Règles de chemin pour les specs

| Sous-projet | Specs | Tests |
|-------------|-------|-------|
| `game/` | `game/docs/` | `game/tests/` |
| `tools/` | `tools/docs/` | `tools/tests/` |

```bash
# Spec conformance — cibler les specs du bon sous-projet
python .agents/skills/verification-loop/scripts/spec_conformance.py . \
  --spec game/docs/   # ou tools/docs/
```

---

## Script de résolution (ordre de priorité)

| Priorité | Chemin |
|----------|--------|
| 1 — Local | `.agents/skills/verification-loop/scripts/verify.py` |
| 2 — Plugin global | `/Users/adrien.parasote/.gemini/config/plugins/stream-coding/skills/verification-loop/scripts/verify.py` |
| 3 — SCRIPT_NOT_FOUND | Arrêter et signaler |

> ⛔ Ne jamais substituer l'auto-évaluation au script. Si le script est introuvable, signaler `SCRIPT_NOT_FOUND`.

---

## Exit criteria

```
- [ ] detect_subproject.py exécuté et résultat affiché
- [ ] verify.py lancé depuis le bon sous-projet (game/ ou tools/)
- [ ] Zero silent failures détectés
- [ ] Spec conformance vérifiée (specs du bon sous-projet)
- [ ] TDD Gate passé si nouveau code écrit
- [ ] VERIFICATION REPORT produit avec evidence
```
