---
name: profile-game
description: Correction autonome d'un problème de performance identifié par le skill perf-audit. Reçoit un identifiant P-NNN et le rapport d'audit en entrée. Applique la correction minimale ciblée, re-profile pour valider l'amélioration, et rend un rapport de résultat. Ce skill NE FAIT PAS DE DIAGNOSTIC — il exécute uniquement. Activer quand l'utilisateur dit "corrige P-001", "applique la correction P-NNN", "execute le fix pour [problème]", ou après avoir lu un rapport perf-audit et choisi quoi corriger.
---

# Skill — Correction de Performance Autonome

> Ce skill **exécute une correction ciblée** à partir d'un problème P-NNN
> identifié par le skill `perf-audit`. Il ne fait aucun diagnostic.
>
> ⛔ **Entrée requise :** chemin du rapport `perf_audit_*.md` + identifiant P-NNN à traiter.

---

## Étape 0 — Résoudre le workspace root

```bash
WORKSPACE=$(git rev-parse --show-toplevel)
```

---

## Étape 1 — Lire le rapport d'audit et extraire le P-NNN

```bash
cat "$WORKSPACE/scripts/dev/perf_audit_[DATE].md"
```

Extraire pour le P-NNN demandé :
- **Localisation** : `game/src/[fichier.py]:[ligne]`
- **Description** : ce que fait le problème
- **Correction attendue** : telle que décrite dans la section 3 du rapport

Si le P-NNN n'existe pas dans le rapport → STOP, demander à l'utilisateur de relancer `perf-audit`.

---

## Étape 2 — Baseline avant correction

```bash
cd "$WORKSPACE"
python scripts/dev/profile_game.py --output scripts/dev/profile_before.txt
```

Relever les métriques de référence pour le P-NNN traité :

```bash
grep -E "avg|p95|p99|Delta|gen[0-9]|Growth" "$WORKSPACE/scripts/dev/profile_before.txt"
```

---

## Étape 3 — Pre-Edit Investigation Gate (OBLIGATOIRE)

Avant de modifier quoi que ce soit :

```bash
# Quels fichiers importent le module ciblé ?
rg "import.*<module>" "$WORKSPACE/game/src/"

# Quels tests couvrent ce fichier ?
rg -l "<module>" "$WORKSPACE/game/tests/"

# Lire le fichier source cible en entier
cat "$WORKSPACE/game/src/<path/to/file.py>"
```

Confirmer que la ligne identifiée dans le rapport correspond au code lu.
Si la ligne ne correspond pas → STOP, signaler la divergence à l'utilisateur.

---

## Étape 4 — Appliquer la correction minimale

**Règles de scope :**
- Toucher **un seul fichier** par P-NNN
- Ne corriger QUE la ligne/fonction identifiée dans le rapport
- Aucun refactoring adjacent
- Aucune "amélioration" non demandée

**Corrections connues par pattern (référence rapide) :**

| Pattern (CPU) | Correction |
|---|---|
| `sorted()` dans la boucle de rendu | Y-sort cache avec dirty flag |
| `pygame.Rect()` dans les loops | Pré-allouer et réutiliser |
| `font.render()` dans draw() | Pre-render en surface composite |
| `rotozoom()` / `smoothscale()` dans draw() | Cache bucketed de surfaces |
| `distance_to()` dans triggers | `distance_squared_to()` |

| Pattern (Mémoire) | Correction |
|---|---|
| Grosse allocation répétée par frame | Pré-allouer hors boucle |
| Cache sans limite | Ajouter `maxsize` ou LRU |
| Sprites non libérés | Vérifier `kill()` / `empty()` |

| Pattern (GC) | Correction |
|---|---|
| gen0 très élevé | Pré-allouer les objets temporaires de la boucle |
| uncollectable > 0 | Casser le cycle avec `weakref` |

Vérifier le scope après la correction :

```bash
git diff --stat
```

Seul le fichier cible doit apparaître. Tout fichier supplémentaire = annuler et reprendre.

---

## Étape 5 — Re-profiling post-correction

```bash
cd "$WORKSPACE"
python scripts/dev/profile_game.py --output scripts/dev/profile_after.txt
```

Comparer avec la baseline :

```bash
grep -E "avg|p95|p99|Delta|gen[0-9]|Growth" "$WORKSPACE/scripts/dev/profile_before.txt"
echo "---après---"
grep -E "avg|p95|p99|Delta|gen[0-9]|Growth" "$WORKSPACE/scripts/dev/profile_after.txt"
```

---

## Étape 6 — Valider ou annuler

**Critère de validation :**
- ✅ Au moins une métrique s'améliore ET aucune ne régresse → correction validée
- ❌ Toute régression → `git checkout -- <fichier>`, signaler à l'utilisateur

---

## Étape 7 — Rapport de résultat

```
CORRECTION P-[NNN] — [nom du problème]
=======================================
Fichier modifié    : [path relatif]
Ligne(s) modifiée(s): [N]
Correction         : [description en 1 phrase]

MÉTRIQUES
---------
avg frame  : X ms → Y ms  (Δ Z %)
p95        : X ms → Y ms  (Δ Z %)
p99        : X ms → Y ms  (Δ Z %)
Mémoire/fr : X KB → Y KB  (Δ Z %)
GC gen0    : X   → Y   collections

STATUT : ✅ Validé / ❌ Annulé (raison)

Prochain P-NNN recommandé : [selon ordre section 4 du rapport perf-audit]
```

---

## Règles d'or

- **Entrée = P-NNN du rapport perf-audit.** Jamais de diagnostic autonome.
- **Jamais de chemin absolu.** Toujours `$WORKSPACE` via `git rev-parse --show-toplevel`.
- **Un P-NNN par exécution.** Ne jamais grouper deux corrections.
- **Baseline avant, re-profiling après.** Sans les deux, la correction n'est pas validée.
- **Régression = annulation immédiate.** `git checkout -- <fichier>`, pas de workaround.
