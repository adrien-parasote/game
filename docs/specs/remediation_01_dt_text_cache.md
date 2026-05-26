# Spec — Steps 1 à 4 : DT Clamp + Text Cache

> Document Type: Implementation
> **Covers:** DT-Clamp, Text-Cache-HUD, Text-Cache-Inventory, Text-Cache-Chest
> **Référence blueprint:** [`best_practices_remediation_blueprint.md`](./strategic/best_practices_remediation_blueprint.md#plan-dimplémentation--10-steps)
> **Guide best practices:** [`pygame_ce_python_312_best_practices.md`](./pygame_ce_python_312_best_practices.md#section-5-architecture)
> **Statut:** SPEC — prêt pour BUILD

---

## Contexte

Deux anti-patterns critiques identifiés dans l'audit (§6 du guide de référence) :

1. **DT non clampé** : `game.py:384` et `game_state_manager.py:55` passent le `dt` brut à la physique. Un freeze > 0.1s téléporte le joueur à travers des collisions.
2. **`font.render()` dans les boucles de dessin** : `hud.py:70/75`, `inventory_draw.py:59,86,123,201,219,231,236,243`, `chest_draw.py:36,85,155` allouent des surfaces à chaque frame.

---

## Constraints

| Tier | Exemples |
|---|---|
| **Always do** | Clamp DT avec `min(raw_dt, 0.1)`. Pre-render les surfaces statiques à `__init__`. Invalider le cache uniquement sur mutation de données. |
| **Ask first** | Modifier la signature de `_render_text_centered`. Ajouter une méthode publique sur `InventoryUI`. |
| **Never do** | Introduire une classe `TextCache` partagée (ADR-006 §"No New Abstractions"). Modifier `TimeSystem`, `RenderManager`, `CameraGroup`. Toucher des fichiers hors scope. |

---

## Cross-Spec Contracts

### Produces
N/A — cette spec ne produit pas d'artefacts consommés par d'autres specs.

### Consumes
| Identifiant | Format | Défini dans | Producteur |
|---|---|---|---|
| `dt: float` passé à `_update(dt)` | float, secondes | `engine-core.md § "Boucle principale"` | `game.py:run()` et `game_state_manager.py:run()` |
| `time_system.time_label` | str, format `"HH:MM"` | `engine-core.md § "TimeSystem"` | `TimeSystem` |
| `time_system.world_time.day` | int | `engine-core.md § "TimeSystem"` | `TimeSystem` |
| `player.hp`, `player.max_hp`, `player.gold`, `player.level` | int | `entities-system.md § "Player"` | `Player` |

### Public Interface
N/A — aucune API publique exposée. Toutes les modifications sont internes aux modules.

### External Invocations
N/A.

### Tracked Concepts
| Concept | Statut dans cette spec | Mentionné dans |
|---|---|---|
| `dt` (delta time) | Contraint à `min(raw_dt, 0.1)` | `engine-core.md`, `entities-system.md` |
| pre-render cache pattern | Inline dict par composant | `ADR-006-perf-constants-pre-render-cache.md` |

---

## Step 1 — DT Clamp

### Cible

Chaque `clock.tick(FPS) / 1000.0` doit être immédiatement suivi d'un `min(raw_dt, 0.1)`.

### Fichiers modifiés

| Fichier | Ligne | Avant | Après |
|---|---|---|---|
| `src/engine/game_state_manager.py` | 55 | `dt = self._game.clock.tick(Settings.FPS) / 1000.0` | `raw_dt = self._game.clock.tick(Settings.FPS) / 1000.0` / `dt = min(raw_dt, 0.1)` |
| `src/engine/game.py` | 384 | `dt = self.clock.tick(Settings.FPS) / 1000.0` | `raw_dt = self.clock.tick(Settings.FPS) / 1000.0` / `dt = min(raw_dt, 0.1)` |
| `src/engine/game.py` | 276 | `dt = self.clock.tick(Settings.FPS) / 1000.0` | `raw_dt = self.clock.tick(Settings.FPS) / 1000.0` / `dt = min(raw_dt, 0.1)` |
| `src/engine/game.py` | 290 | `dt = self.clock.tick(Settings.FPS) / 1000.0` | `raw_dt = self.clock.tick(Settings.FPS) / 1000.0` / `dt = min(raw_dt, 0.1)` |

**Règle :** Toute occurrence de `clock.tick(Settings.FPS) / 1000.0` dans `src/` doit être suivie d'un clamp. Aucune exception.

**Constante :** `DT_MAX = 0.1` dans `src/config.py` ou inline. Pas de magic number nu.

### Vérification

```bash
grep -n "clock.tick" src/engine/game.py src/engine/game_state_manager.py
# → chaque hit doit avoir min(raw_dt, ...) à la ligne suivante
```

---

## Steps 2-4 — Text Cache

### Principe général (conforme ADR-006)

**Pattern :** pre-render dict inline dans chaque composant. Aucune classe partagée.

```python
# PATTERN RÉFÉRENCE (identique à PauseScreen._make_engraved_surface et title_screen.py:168)

# __init__ — pre-render
self._cached_texts: dict[str, pygame.Surface] = {}
self._cached_shadow_texts: dict[str, pygame.Surface] = {}
self._build_static_text_cache()

def _build_static_text_cache(self) -> None:
    """Pre-render surfaces for all static text. Call once at init."""
    for key, text in STATIC_LABELS.items():
        self._cached_texts[key] = self._font.render(text, True, TEXT_COLOR).convert_alpha()
        self._cached_shadow_texts[key] = self._font.render(text, True, SHADOW_COLOR).convert_alpha()

# draw() — zéro alloc
screen.blit(self._cached_texts["time"], rect)
```

**Règle d'invalidation :** Les textes dynamiques (valeurs qui changent) utilisent un cache par valeur, avec une limite de taille stricte pour éviter les fuites mémoire (OOM) :
```python
def _get_cached_text(self, text: str, color: tuple[int, int, int]) -> pygame.Surface:
    key = f"{text}"  # couleur fixe par composant → pas dans la clé
    if key not in self._text_cache:
        # Cache eviction pour le texte dynamique
        if len(self._text_cache) > 512:  # Limite augmentée à 512 pour éviter les micro-stutters
            self._text_cache.clear()
        self._text_cache[key] = self._font.render(text, True, color).convert_alpha()
    return self._text_cache[key]
```

**⛔ JAMAIS dans `draw()` :**
```python
# INTERDIT
def draw(self, screen):
    surf = self._font.render("Day 1", True, COLOR)  # alloc à chaque frame
```

---

## Step 2 — Text Cache HUD (`hud.py`)

### Analyse de la cible

`GameHUD.draw()` appelle `_render_text_centered()` 2× :
1. `self.time_system.time_label` — change 1×/minute en jeu (temps accéléré)
2. `f"{day_label} {wt.day + 1}"` — change 1×/jour en jeu

Chaque appel fait 2 `font.render()` (shadow + main). Total : **4 surfaces/frame**.

### Implémentation

**`GameHUD.__init__` — ajouter :**
```python
self._text_cache: dict[str, pygame.Surface] = {}
self._shadow_cache: dict[str, pygame.Surface] = {}
```

**Remplacer `_render_text_centered` :**
```python
def _render_text_cached(self, surface: pygame.Surface, text: str, center: tuple[int, int]) -> None:
    """Render text with shadow using cache. Zero alloc if text unchanged."""
    if text not in self._shadow_cache:
        self._shadow_cache[text] = self._font.render(text, True, SHADOW_COLOR).convert_alpha()
    if text not in self._text_cache:
        self._text_cache[text] = self._font.render(text, True, TEXT_COLOR).convert_alpha()

    shadow_rect = self._shadow_cache[text].get_rect(
        center=(center[0] + SHADOW_OFFSET, center[1] + SHADOW_OFFSET)
    )
    surface.blit(self._shadow_cache[text], shadow_rect)
    surface.blit(self._text_cache[text], self._text_cache[text].get_rect(center=center))
```

**Remplacer les 2 appels dans `draw()` :**
```python
self._render_text_cached(screen, self.time_system.time_label, ...)
self._render_text_cached(screen, season_day_text, ...)
```

**Cache éviction :** Aucune nécessaire. Le dict grossit de 2-3 clés max (labels de temps). Taille négligeable.

### Fichier modifié

- `src/ui/hud.py` — remplacement de `_render_text_centered` par `_render_text_cached`

---

## Step 3 — Text Cache Inventory (`inventory_draw.py`)

### Analyse de la cible

`_draw_stats()` fait 3 `font.render()` à chaque frame d'inventaire ouvert :
- `f"LVL {player.level}"` — change uniquement lors d'un level-up
- `f"HP {player.hp}/{player.max_hp}"` — change lors de dégâts/soins
- `f"GOLD {player.gold}"` — change lors d'une transaction

`_draw_character_preview()` fait 1 `font.render()` : `"Player"` — **statique**.
`_draw_grid()` fait `font.render()` pour `f"x{item.quantity}"` — change lors d'une transaction.
`_draw_item_info()` fait `font.render()` pour nom et description item — change selon hover.

### Pattern d'invalidation

Les stats HP/GOLD/LVL sont des attributs publics simples sur `Player`. Mutations à l'init + dans `_apply_save_data()`. **Décision : cache par valeur** (conforme G1 résolu).

```python
# InventoryDrawMixin.__init__ (via InventoryUI.__init__)
self._text_cache: dict[str, pygame.Surface] = {}  # ajout

def _get_text_surface(self: "InventoryUIProtocol", text: str, font: pygame.font.Font, color: tuple[int, int, int]) -> pygame.Surface:
    """Cache lookup by (text, font_id, color). Creates on miss."""
    key = (id(font), color, text)  # Tuple unique pour éviter les collisions de couleurs
    if key not in self._text_cache:
        self._text_cache[key] = font.render(text, True, color).convert_alpha()
    return self._text_cache[key]
```

**`"Player"` static label** → pre-rendered à l'init, jamais recalculé.

**Item info (nom + description)** → cache par `item.id`. Invalide implicitement : si l'item hover change, la clé change.

**Quantity `f"x{qty}"`** → cache par valeur string (ex: `"x3"` → réutilisable entre items différents de même quantité).

### Fichier modifié

- `src/ui/inventory_draw.py` — `_draw_stats()`, `_draw_character_preview()`, `_draw_grid()`, `_draw_item_info()`
- `src/ui/inventory.py` (via `InventoryUI.__init__`) — ajout `self._text_cache: dict[str, pygame.Surface] = {}`

---

## Step 4 — Text Cache Chest (`chest_draw.py`)

### Analyse de la cible

Violations dans `chest_draw.py` :
- L36 : titre du coffre (statique)
- L85 : quantité item (semi-statique)
- L155 : label catégorie (statique)

### Implémentation

Même pattern que Step 3. Toutes les surfaces sont soit statiques (pre-render à l'init) soit par-valeur (cache hit sur clé string).

### Fichier modifié

- `src/ui/chest_draw.py`

---

## Anti-Patterns

| # | Anti-Pattern | Violation | Correct Behavior |
|---|---|---|---|
| 1 | `font.render()` dans `draw()` | `surf = self._font.render(text, True, color)` dans une méthode appelée 60×/sec | Pre-render dans `__init__` ou cache dict — zéro alloc dans `draw()` |
| 2 | Classe `TextCache` globale partagée | `from src.engine.text_cache import TextCache` importé dans HUD, Inventory, Chest | Dict inline par composant — conforme [ADR-006](../ADRs/ADR-006-perf-constants-pre-render-cache.md#decision) |
| 3 | Cache avec éviction LRU sur texte borné | Implanter un cache LRU pour 3-20 clés max | `dict[str, Surface]` simple — YAGNI |
| 4 | DT clampé uniquement dans `TimeSystem` | `TimeSystem.update()` clamp en interne, physique reçoit `dt` brut | Clamp à la source : `dt = min(raw_dt, DT_MAX)` avant tout appel à `_update(dt)` |
| 5 | `min(raw_dt, 0.1)` sans constante | Magic number `0.1` inline, aucune constante `DT_MAX` | Définir `DT_MAX = 0.1` dans `src/config.py` ou en tête de module |
| 6 | Clamp dans `TimeSystem` seulement | `TimeSystem` protège son propre état mais pas la physique | Clamp avant `self._update(dt)` — [engine-core.md](./engine-core.md#boucle-principale) |



---

## Test Case Specifications

### Unit Tests — DT Clamp

**TC-DT-001** : `game_state_manager.run()` avec horloge simulant un tick de 500ms → `_handle_playing()` reçoit `dt ≤ 0.1`
```python
# Arrange: mock clock.tick → return 500 (ms)
# Act: one iteration of run() loop
# Assert: dt argument to _handle_playing ≤ 0.1
```

**TC-DT-002** : `game_state_manager.run()` avec tick normal 16ms → `dt ≈ 0.016` (non clampé inutilement)
```python
# Assert: dt ≈ 0.016 (± 0.001)
```

**TC-DT-003** : `game.py` fade-out loop avec tick simulé 200ms → `dt ≤ 0.1` dans la boucle de fade

**TC-DT-004** : Vérification statique (grep "clock.tick" src/engine/game.py) → chaque hit suivi de `min(` dans les 2 lignes suivantes

### Unit Tests — HUD Cache

**TC-HUD-001** : `GameHUD._render_text_cached("12:00", ...)` appelé 2× → `font.render` appelé exactement 1× (pas 2×)
```python
# Arrange: mock self._font.render → return Surface
# Act: _render_text_cached("12:00", center) × 2
# Assert: mock.render.call_count == 1
```

**TC-HUD-002** : `GameHUD._render_text_cached("12:00", ...)` puis `_render_text_cached("12:01", ...)` → `font.render` appelé 2× (cache miss sur nouvelle clé)

**TC-HUD-003** : `GameHUD.draw()` appelé 60× sans changement de `time_label` → `font.render` appelé exactement 2× (1 shadow + 1 main pour le label initial)

### Unit Tests — Inventory Cache

**TC-INV-001** : `_draw_stats()` appelé 2× avec `player.level=1, player.hp=100, player.gold=0` → `noble_font.render` pour LVL appelé 1× seulement

**TC-INV-002** : `_draw_stats()` avec `player.hp=100` puis `player.hp=90` → `noble_font.render` pour HP appelé 2× (cache miss sur nouvelle valeur)

**TC-INV-003** : `_draw_character_preview()` appelé 30× → `noble_font.render("Player", ...)` appelé exactement 1× (pre-rendered à l'init)

**TC-INV-004** : `_get_text_surface(text, font_a, color)` puis `_get_text_surface(text, font_b, color)` → 2 surfaces distinctes (clé inclut `id(font)`)

**TC-INV-005** : `_draw_item_info(item_a)` puis `_draw_item_info(item_b)` → surfaces différentes dans le cache

### Integration Tests

**TC-IT-001** : Ouvrir l'inventaire, ne pas toucher HP/GOLD/LVL pendant 60 frames → 0 appels à `font.render` après le frame 1 (vérifiable via mock + call_count)

**TC-IT-002** : Recevoir des dégâts (HP change), ouvrir l'inventaire → HP surface recalculée avec la nouvelle valeur

**TC-IT-003** : `GameStateManager.run()` avec freeze simulé 2 secondes → joueur ne se téléporte pas (position inchangée après 1 tick long)

---

## Error Handling Matrix

| Error | Fallback | Logging |
|---|---|---|
| `font.render()` échoue (font None) — `AssetManager.get_font()` a échoué | Surface fallback de l'init retournée — pas de crash dans `draw()` | `logging.error` dans `_load_font()` |\n| `clock.tick()` retourne 0 — première frame | `min(0 / 1000.0, 0.1)` = 0.0 — correct, pas de division par zéro | N/A |\n| `clock.tick()` retourne valeur négative — jamais sur pygame-ce | `max(0.0, min(raw_dt, 0.1))` si garde-fou ajouté | N/A — défensif uniquement |\n| Cache `_text_cache` absent — oubli d'initialisation dans `__init__` | `AttributeError` au premier appel de `_get_text_surface` — détectable en test TC-INV-001 | Test TC-INV-001 catch immédiat |


---

## Bundling & Native-Module Audit

- **BM1:** N/A — projet Python pur, pas de framework bundlé Next.js/SvelteKit
- **BM2:** N/A
- **BM3:** N/A — aucun module natif introduit
- **BM4:** N/A — aucune constante renommée dans cette spec

---

## File Tree

```
src/
├── engine/
│   ├── game.py                    [MODIFY] — DT clamp ×3 occurrences
│   └── game_state_manager.py      [MODIFY] — DT clamp ×1 occurrence
└── ui/
    ├── hud.py                     [MODIFY] — _render_text_cached remplace _render_text_centered
    ├── inventory.py               [MODIFY] — ajout self._text_cache dans __init__
    ├── inventory_draw.py          [MODIFY] — _draw_stats, _draw_character_preview, _draw_grid, _draw_item_info
    └── chest_draw.py              [MODIFY] — surfaces titre + quantité pré-rendues
```

---

## Assumptions

| Assumption | Risque | Validation |
|---|---|---|
| `DT_MAX = 0.1` (100ms = 10 FPS minimum) est suffisant | Low — valeur standard pygame-ce | Conforme guide de référence §5.3 |
| `time_label` est un str pur sans caractères spéciaux | Low | Vérifié dans `TimeSystem._format_time()` |
| Le cache `_text_cache` dict ne grossira pas > 50 clés en conditions normales | Low — HUD = 2-3 clés, Inventory stats = 3 clés + N items hover | Pas d'éviction nécessaire |
| `convert_alpha()` est disponible (display initialisé) | Low — conftest.py crée `pygame.HIDDEN` display | Vérifié dans l'analyse des gaps (G3) |
