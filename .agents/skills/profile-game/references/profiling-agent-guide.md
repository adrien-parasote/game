# Spec — Outil de Profiling Autonome [Reference]

> **Document Type :** Reference
> **Script :** `scripts/dev/profile_game.py`
> **Rapport généré :** `scripts/dev/profile_report.txt`

---

## Objectif

Ce document explique à un **agent IA autonome** comment utiliser `profile_game.py`,
interpréter chaque section du rapport, et décider des corrections à apporter
sans intervention humaine.

---

## 1. Quand lancer le profiling

Lance le profiler **avant toute optimisation de performance**. Ne jamais optimiser
à l'aveugle. Le rapport est la source de vérité.

| Symptôme rapporté | Action |
|---|---|
| "Le jeu rame" / "lag" / "freeze" | Lancer le profiler, analyser AXE 1 + AXE 2 |
| "Fuite mémoire" / "ça grossit" | Lancer le profiler, analyser AXE 3 + AXE 4 |
| "Des spikes ponctuels" | Lancer le profiler, analyser AXE 1 p99 + AXE 4 |
| Avant tout refactoring de hot-path | Lancer le profiler → baseline → refactorer → re-profiler |

---

## 2. Lancer le script

```bash
# Depuis la racine du workspace (/game)
python scripts/dev/profile_game.py
```

Durée : ~30 secondes (1800 frames à 60 fps).
Sortie : `scripts/dev/profile_report.txt`

Options :
```bash
# Durée personnalisée
python scripts/dev/profile_game.py --frames 3600   # 60 s

# Chemin de sortie custom
python scripts/dev/profile_game.py --output /tmp/profile_before.txt
```

---

## 3. Structure du rapport

Le rapport contient 4 sections. Lire dans cet ordre : **1 → 4**.

---

### AXE 1 — FRAME TIMING

```
=== AXE 1 — FRAME TIMING ===
Frames        : 1800
FPS moyen     : 61.7
avg           : 16.2 ms
p50           : 15.8 ms
p95           : 24.1 ms   ← seuil confort
p99           : 41.3 ms   ← worst-case joueur
min / max     : 8.1 ms / 67.8 ms
Spikes >33 ms : 12 frames (0.7%)  [< 30 fps]
Spikes >50 ms :  3 frames (0.2%)  [< 20 fps]
```

**Règles d'interprétation :**

| Métrique | Seuil OK | Seuil dégradé | Seuil critique |
|---|---|---|---|
| avg | < 16.7 ms | 16.7–25 ms | > 25 ms |
| p95 | < 20 ms | 20–33 ms | > 33 ms |
| p99 | < 33 ms | 33–50 ms | > 50 ms |
| Spikes >33 ms | < 1 % | 1–5 % | > 5 % |

**Patterns de diagnostic :**

| Pattern observé | Cause probable | Où chercher |
|---|---|---|
| avg élevé ET p99 proportionnel | Code structurellement trop lent | AXE 2 tottime |
| avg OK MAIS p99 très élevé | Spike ponctuel : GC ou chargement | AXE 4 gen0 + AXE 2 cumtime |
| max >> p99 | Spike unique : I/O bloquante ou asset load | AXE 2 cumtime, chercher `load` |
| p95 > 2× avg | Jitter : allocations dans la boucle | AXE 3 delta/frame + AXE 4 |

---

### AXE 2 — CPU HOTSPOTS

```
=== AXE 2 — CPU HOTSPOTS (game/src uniquement) ===

--- TOP 25 par tottime ---
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
    36000    0.841    0.023    1.203    0.033 map/renderer.py:198(render_chunk)
   600000    0.412    0.001    0.412    0.001 entities/sprite.py:44(update_animation)

--- TOP 25 par cumtime ---
    ...
```

**Règles d'interprétation :**

- **tottime** = temps CPU passé **dans** la fonction (hors appelés). C'est le vrai coupable.
- **cumtime** = temps total **incluant** les fonctions appelées. Révèle les chaînes coûteuses.
- **percall** = `tottime / ncalls`. Un percall élevé sur peu d'appels = opération coûteuse.
  Un percall faible sur beaucoup d'appels = optimiser la structure des données.

**Seuils d'action :**

| tottime par fonction | Action |
|---|---|
| > 10 % du budget frame total | Priorité haute — optimiser en premier |
| 5–10 % | Priorité moyenne |
| < 5 % | Ne pas toucher sauf si trivial |

**Budget frame total** = `avg_frame_time × frames` (ex : 16.2 ms × 1800 = 29.16 s de CPU)

**Patterns fréquents et corrections connues :**

| Pattern CPU | Correction |
|---|---|
| `render_*` en tête du tottime | Vérifier fblits() batch, dirty rects, culling viewport |
| `sort` ou `sorted` dans la boucle | Y-sort cache avec dirty flag (`_cache_dirty`) |
| `font.render()` dans la boucle | Pre-render en surface composite au chargement |
| `rotozoom()` / `smoothscale()` dans draw() | Cache bucketed de surfaces pré-scalées |
| `distance_to()` dans les triggers | Remplacer par `distance_squared_to()` |
| `pygame.Rect()` dans les loops | Pré-allouer et réutiliser |
| Beaucoup d'appels à `colliderect` | Passer des tuples `(x, y, w, h)` au lieu de Rect |

**Règle de scope :** Ne corriger QUE les fonctions dans `game/src`. Ignorer pygame/stdlib.

---

### AXE 3 — MÉMOIRE

```
=== AXE 3 — MÉMOIRE (Python heap via tracemalloc) ===
Début         : 48.3 MB
Fin           : 72.1 MB
Delta total   : +23800.0 KB  (+13.22 KB/frame)

--- TOP 20 ALLOCATIONS par fichier:ligne ---
      delta  taille totale  localisation
  +12400 KB       12400 KB  graphics/surface_cache.py:87
   +4100 KB        4100 KB  map/chunk_loader.py:203
```

**Note :** `tracemalloc` mesure le heap Python uniquement (objets Python + surfaces pygame
allouées via Python). Il ne couvre pas les allocations C internes de pygame/SDL.

**Règles d'interprétation :**

| Delta/frame | Interprétation |
|---|---|
| < 1 KB/frame | Normal |
| 1–10 KB/frame | Surveiller — accumulation lente |
| > 10 KB/frame | Fuite ou sur-allocation — corriger |

**Patterns fréquents et corrections connues :**

| Pattern mémoire | Cause probable | Correction |
|---|---|---|
| Grosse allocation unique, stable | Surface ou asset chargé une fois | Acceptable si ne croît pas |
| Delta positif constant par frame | Objets créés sans être libérés dans la boucle | Pré-allouer hors boucle ou pooler |
| `surface_cache.py` en tête | Cache sans LRU ou sans éviction | Ajouter `maxsize` au cache |
| `chunk_loader.py` en tête | Chunks chargés mais jamais déchargés | Ajouter unload des chunks hors viewport |
| `groups.py` en tête | Sprites accumulés dans un groupe | Vérifier `kill()` et `empty()` |

**Règle :** Si delta total > 50 MB sur 30 s ET croît linéairement → fuite confirmée.
Chercher le fichier:ligne en tête du tableau et tracer les allocations.

---

### AXE 4 — GC PRESSURE

```
=== AXE 4 — GC PRESSURE ===
    génération  collections  objets collectés  uncollectable
          gen0           42            18,400              0
          gen1            3             1,200              0
          gen2            0                 0              0
```

**Règles d'interprétation :**

| Métrique | Seuil OK | Problème |
|---|---|---|
| gen0 collections / 30 s | < 30 | > 100 = trop d'objets temporaires dans la boucle |
| gen1 collections / 30 s | < 5 | > 20 = objets qui survivent trop longtemps |
| gen2 collections | 0 | Toute collection = objets de longue durée mal gérés |
| uncollectable | 0 | > 0 = cycle de référence non cassable = fuite confirmée |

**Patterns fréquents et corrections connues :**

| Pattern GC | Cause probable | Correction |
|---|---|---|
| gen0 très élevé (> 100/30 s) | Objets temporaires créés dans la boucle (tuples, dicts, lists) | Pré-allouer hors boucle, réutiliser |
| gen1 élevé | Objets qui survivent plusieurs frames | Chercher les listes qui grossissent |
| uncollectable > 0 | `__del__` + références circulaires | Identifier le cycle, casser avec `weakref` |
| gen2 collection | Fuite de longue durée | Croiser avec AXE 3 pour identifier la source |

**Corrélation AXE 1 / AXE 4 :** Si p99 > 40 ms ET gen0 > 50 collections/30 s,
les spikes sont probablement des pauses GC. Réduire gen0 en pré-allouant les objets
de la boucle principale.

---

## 4. Workflow agent — du rapport aux corrections

```
1. Lire AXE 1 → Classifier le problème (CPU / mémoire / GC / mixte)
2. Aller à l'axe correspondant → Identifier fichier:ligne précis
3. Lire le fichier source concerné (Pre-Edit Investigation Gate)
4. Appliquer la correction minimale (scope : fichier identifié uniquement)
5. Re-lancer le profiler → Vérifier que la métrique s'améliore
6. Si régression → annuler et investiguer autrement
```

**Règle d'or :** Ne jamais corriger sans baseline. Ne jamais valider sans re-profiling.

---

## 5. Comparaison avant/après

Pour mesurer l'impact d'une correction :

```bash
# Baseline
python scripts/dev/profile_game.py --output scripts/dev/profile_before.txt

# [appliquer la correction]

# Post-correction
python scripts/dev/profile_game.py --output scripts/dev/profile_after.txt
```

Comparer les métriques clés :
- AXE 1 : avg, p95, p99, spikes
- AXE 2 : tottime de la fonction corrigée
- AXE 3 : delta/frame
- AXE 4 : gen0 collections

Une correction est valide si **au moins une métrique s'améliore ET aucune ne régresse**.

---

## 6. Deep Links

- **Script de profiling :** [`profile_game.py`](../../../../scripts/dev/profile_game.py)
- **Rapport généré :** `scripts/dev/profile_report.txt`
- **Spec performance existante :** [`performance-system.md`](performance-system.md)
- **Moteur de rendu :** [`render_manager.py`](../../src/engine/render_manager.py)
- **Y-sort cache :** [`groups.py`](../../src/entities/groups.py)
- **Best practices pygame-ce :** [`pygame_ce_python_312_best_practices.md`](pygame_ce_python_312_best_practices.md)

---

## 7. Anti-patterns (à ne PAS faire)

| ❌ | ✅ |
|---|---|
| Optimiser sans rapport de profiling | Toujours profiler d'abord |
| Modifier plusieurs fichiers à la fois | Un fichier à la fois, re-profiler entre chaque |
| Ignorer une régression dans une autre métrique | Toute régression invalide la correction |
| Filtrer `game/src` et ignorer le résultat vide | Si vide, afficher toutes les sources — le problème peut être dans pygame |
| Conclure "OK" sans re-profiling post-correction | Re-profiling est obligatoire avant de valider |
