# Spec — Steps 1 to 4: DT Clamp + Text Cache

> Document Type: Implementation
> **Covers:** DT-Clamp, Text-Cache-HUD, Text-Cache-Inventory, Text-Cache-Chest
> **Blueprint Reference:** [`best_practices_remediation_blueprint.md`](../strategic/best_practices_remediation_blueprint.md#implementation-plan--10-steps)
> **Best Practices Guide:** [`pygame_ce_python_312_best_practices.md`](./pygame_ce_python_312_best_practices.md#section-5-architecture)
> **Status:** SPEC — ready for BUILD

---

## Context

Two critical anti-patterns identified in the audit (§6 of the reference guide):

1. **Unclamped DT**: `game.py:384` and `game_state_manager.py:55` pass the raw `dt` to physics. A freeze > 0.1s teleports the player through collisions.
2. **`font.render()` in drawing loops**: `hud.py:70/75`, `inventory_draw.py:59,86,123,201,219,231,236,243`, and `chest_draw.py:36,85,155` allocate surfaces on every frame.

---

## Test Cases

| ID | Description | Assertion |
|---|---|---|
| IT-999 | -> pipeline | A |


| ID | Description | Assertion |
|---|---|---|
| UT-001 | pipeline test | A |
| UT-002 | TBD | A |
| UT-003 | TBD | A |
| UT-004 | TBD | A |
| UT-005 | TBD | A |
| IT-001 | pipeline integration test | A |
| IT-002 | TBD | A |
| IT-003 | TBD | A |
| TC-001 | TBD | A |

## Anti-patterns

| Anti-pattern | Why it's bad | What to do instead |
|---|---|---|
| TBD | TBD | TBD |
| TBD | TBD | TBD |
| TBD | TBD | TBD |
| TBD | TBD | TBD |
| TBD | TBD | TBD |

## Constraints

| Tier | Examples |
|---|---|
| **Always do** | Clamp DT with `min(raw_dt, 0.1)`. Pre-render static surfaces in `__init__`. Invalidate the cache only when data mutates. |
| **Ask first** | Modify the signature of `_render_text_centered`. Add a public method to `InventoryUI`. |
| **Never do** | Introduce a shared `TextCache` class (ADR-006 §"No New Abstractions"). Modify `TimeSystem`, `RenderManager`, or `CameraGroup`. Touch files out of scope. |

---

## Cross-Spec Contracts

### Produces
N/A - Not applicable

### Consumes
N/A - Not applicable

### Public Interface
N/A - Not applicable

### External Invocations
- N/A

### Tracked Concepts
- N/A

## Step 1 — DT Clamp

### Target

Each `clock.tick(FPS) / 1000.0` must be immediately followed by a `min(raw_dt, 0.1)`.

### Modified Files

| File | Line | Before | After |
|---|---|---|---|
| `src/engine/game_state_manager.py` | 55 | `dt = self._game.clock.tick(Settings.FPS) / 1000.0` | `raw_dt = self._game.clock.tick(Settings.FPS) / 1000.0` / `dt = min(raw_dt, 0.1)` |
| `src/engine/game.py` | 384 | `dt = self.clock.tick(Settings.FPS) / 1000.0` | `raw_dt = self.clock.tick(Settings.FPS) / 1000.0` / `dt = min(raw_dt, 0.1)` |
| `src/engine/game.py` | 276 | `dt = self.clock.tick(Settings.FPS) / 1000.0` | `raw_dt = self.clock.tick(Settings.FPS) / 1000.0` / `dt = min(raw_dt, 0.1)` |
| `src/engine/game.py` | 290 | `dt = self.clock.tick(Settings.FPS) / 1000.0` | `raw_dt = self.clock.tick(Settings.FPS) / 1000.0` / `dt = min(raw_dt, 0.1)` |

**Rule:** Every occurrence of `clock.tick(Settings.FPS) / 1000.0` in `src/` must be followed by a clamp. No exceptions.

**Constant:** `DT_MAX = 0.1` in `src/config.py` or inline. No naked magic numbers.

### Verification

```bash
grep -n "clock.tick" src/engine/game.py src/engine/game_state_manager.py
# → each hit must have min(raw_dt, ...) on the following line
```

---

## Steps 2-4 — Text Cache

### General Principle (conforming to ADR-006)

**Pattern:** Inline pre-render dict in each component. No shared classes.

```python
# REFERENCE PATTERN (identical to PauseScreen._make_engraved_surface and title_screen.py:168)

# __init__ — pre-render
self._cached_texts: dict[str, pygame.Surface] = {}
self._cached_shadow_texts: dict[str, pygame.Surface] = {}
self._build_static_text_cache()

def _build_static_text_cache(self) -> None:
    """Pre-render surfaces for all static text. Call once at init."""
    for key, text in STATIC_LABELS.items():
        self._cached_texts[key] = self._font.render(text, True, TEXT_COLOR).convert_alpha()
        self._cached_shadow_texts[key] = self._font.render(text, True, SHADOW_COLOR).convert_alpha()

# draw() — zero allocations
screen.blit(self._cached_texts["time"], rect)
```

**Invalidation Rule:** Dynamic text (values that change) uses a cache-by-value, with a strict size limit to prevent memory leaks (OOM):
```python
def _get_cached_text(self, text: str, color: tuple[int, int, int]) -> pygame.Surface:
    key = f"{text}"  # fixed color per component → not in the key
    if key not in self._text_cache:
        # Cache eviction for dynamic text
        if len(self._text_cache) > 512:  # Limit increased to 512 to prevent micro-stutters
            self._text_cache.clear()
        self._text_cache[key] = self._font.render(text, True, color).convert_alpha()
    return self._text_cache[key]
```

**⛔ NEVER in `draw()`:**
```python
# FORBIDDEN
def draw(self, screen):
    surf = self._font.render("Day 1", True, COLOR)  # allocates every frame
```

---

## Step 2 — Text Cache HUD (`hud.py`)

### Target Analysis

`GameHUD.draw()` calls `_render_text_centered()` 2×:
1. `self.time_system.time_label` — changes 1×/minute in-game (accelerated time)
2. `f"{day_label} {wt.day + 1}"` — changes 1×/day in-game

Each call performs 2 `font.render()` operations (shadow + main). Total: **4 surfaces/frame**.

### Implementation

**`GameHUD.__init__` — add:**
```python
self._text_cache: dict[str, pygame.Surface] = {}
self._shadow_cache: dict[str, pygame.Surface] = {}
```

**Replace `_render_text_centered`:**
```python
def _render_text_cached(self, surface: pygame.Surface, text: str, center: tuple[int, int]) -> None:
    """Render text with shadow using cache. Zero allocations if text unchanged."""
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

**Replace the 2 calls in `draw()`:**
```python
self._render_text_cached(screen, self.time_system.time_label, ...)
self._render_text_cached(screen, season_day_text, ...)
```

**Cache Eviction:** None required. The dict grows by 2-3 keys max (time labels). Negligible size.

### Modified File

- `src/ui/hud.py` — replace `_render_text_centered` with `_render_text_cached`

---

## Step 3 — Text Cache Inventory (`inventory_draw.py`)

### Target Analysis

`_draw_stats()` performs 3 `font.render()` calls on every frame the inventory is open:
- `f"LVL {player.level}"` — changes only on level-up
- `f"HP {player.hp}/{player.max_hp}"` — changes on damage/heal
- `f"GOLD {player.gold}"` — changes on transaction

`_draw_character_preview()` performs 1 `font.render()` call: `"Player"` — **static**.
`_draw_grid()` performs `font.render()` for `f"x{item.quantity}"` — changes on transaction.
`_draw_item_info()` performs `font.render()` for item name and description — changes on hover.

### Invalidation Pattern

The HP/GOLD/LVL stats are simple public attributes on `Player`. Mutations happen at init + inside `_apply_save_data()`. **Decision: cache by value** (conforms to G1 resolution).

```python
# InventoryDrawMixin.__init__ (via InventoryUI.__init__)
self._text_cache: dict[str, pygame.Surface] = {}  # added

def _get_text_surface(self: "InventoryUIProtocol", text: str, font: pygame.font.Font, color: tuple[int, int, int]) -> pygame.Surface:
    """Cache lookup by (text, font_id, color). Creates on miss."""
    key = (id(font), color, text)  # Unique tuple to avoid color collisions
    if key not in self._text_cache:
        self._text_cache[key] = font.render(text, True, color).convert_alpha()
    return self._text_cache[key]
```

**`"Player"` static label** → pre-rendered at init, never recalculated.

**Item info (name + description)** → cache by `item.id`. Implicitly invalidates: if the hovered item changes, the key changes.

**Quantity `f"x{qty}"`** → cache by string value (e.g., `"x3"` → reusable across different items of the same quantity).

### Modified Files

- `src/ui/inventory_draw.py` — `_draw_stats()`, `_draw_character_preview()`, `_draw_grid()`, `_draw_item_info()`
- `src/ui/inventory.py` (via `InventoryUI.__init__`) — add `self._text_cache: dict[str, pygame.Surface] = {}`

---

## Step 4 — Text Cache Chest (`chest_draw.py`)

### Target Analysis

Violations in `chest_draw.py`:
- L36: chest title (static)
- L85: item quantity (semi-static)
- L155: category label (static)

### Implementation

Same pattern as Step 3. All surfaces are either static (pre-rendered at init) or by-value (cache hit on string key).

### Modified File

- `src/ui/chest_draw.py`

---

## Anti-Patterns

| # | Anti-Pattern | Violation | Correct Behavior |
|---|---|---|---|
| 1 | `font.render()` in `draw()` | `surf = self._font.render(text, True, color)` in a method called 60×/sec | Pre-render in `__init__` or cache dict — zero allocations in `draw()` |
| 2 | Shared global `TextCache` class | `from src.engine.text_cache import TextCache` imported in HUD, Inventory, Chest | Inline dict per component — conforms to [ADR-006](../ADRs/ADR-006-perf-constants-pre-render-cache.md#decision) |
| 3 | Cache with LRU eviction on bounded text | Implement an LRU cache for only 3-20 keys max | Simple `dict[str, Surface]` — YAGNI |
| 4 | DT clamped only in `TimeSystem` | `TimeSystem.update()` clamps internally, physics receives raw `dt` | Clamp at the source: `dt = min(raw_dt, DT_MAX)` before any `_update(dt)` call |
| 5 | `min(raw_dt, 0.1)` without constant | Magic number `0.1` inline, no `DT_MAX` constant | Define `DT_MAX = 0.1` in `src/config.py` or at the top of the module |
| 6 | Clamp in `TimeSystem` only | `TimeSystem` protects its own state but not the physics engine | Clamp before `self._update(dt)` — [engine-core.md](./engine-core.md#main-loop) |

---

## Test Case Specifications

### Unit Tests — DT Clamp

| Test ID | Function | File | Description |
|---------|----------|------|-------------|
| TC-DT-001 | `test_gsm_dt_clamped_on_long_tick` | `../../tests/engine/test_dt_clamp.py` | `game_state_manager.run()` with a clock simulating a 500ms tick → `_handle_playing()` receives `dt ≤ 0.1` |
| TC-DT-002 | `test_gsm_dt_not_clamped_on_normal_tick` | `../../tests/engine/test_dt_clamp.py` | `game_state_manager.run()` with a normal 16ms tick → `dt ≈ 0.016` (not clamped unnecessarily) |
| TC-DT-003 | — | — | `game.py` fade-out loop with a simulated 200ms tick → `dt ≤ 0.1` in the fade loop |
| TC-DT-004 | `test_static_clock_tick_followed_by_clamp` | `../../tests/engine/test_dt_clamp.py` | Static check (grep "clock.tick" src/engine/game.py) → each hit followed by `min(` within the next 2 lines |

### Unit Tests — HUD Cache

| Test ID | Function | File | Description |
|---------|----------|------|-------------|
| TC-HUD-001 | `test_hud_font_render_called_once_on_double_draw_same_label` | `../../tests/ui/test_text_cache.py` | `GameHUD._render_text_cached("12:00", ...)` called 2× → `font.render` called exactly 1× (not 2×) |
| TC-HUD-002 | `test_hud_cache_miss_on_new_label` | `../../tests/ui/test_text_cache.py` | `GameHUD._render_text_cached("12:00", ...)` then `_render_text_cached("12:01", ...)` → `font.render` called 2× (cache miss on new key) |
| TC-HUD-003 | `test_hud_cache_attribute_present` | `../../tests/ui/test_text_cache.py` | `GameHUD.draw()` called 60× without `time_label` changing → `font.render` called exactly 2× (1 shadow + 1 main for the initial label) |

### Unit Tests — Inventory Cache

| Test ID | Function | File | Description |
|---------|----------|------|-------------|
| TC-INV-CACHE-001 | `test_inventory_text_cache_attribute` | `../../tests/ui/test_text_cache.py` | InventoryUI must have `_text_cache` dict after `__init__` |
| TC-INV-CACHE-002 | — | — | `_draw_stats()` called 2× with `player.level=1, player.hp=100, player.gold=0` → `noble_font.render` for LVL called 1× only |
| TC-INV-CACHE-003 | — | — | `_draw_stats()` with `player.hp=100` then `player.hp=90` → `noble_font.render` for HP called 2× (cache miss on new value) |
| TC-INV-CACHE-004 | — | — | `_draw_character_preview()` called 30× → `noble_font.render("Player", ...)` called exactly 1× (pre-rendered at init) |
| TC-INV-CACHE-005 | — | — | `_get_text_surface(text, font_a, color)` then `_get_text_surface(text, font_b, color)` → 2 distinct surfaces (key includes `id(font)`) |

### Unit Tests — Chest Cache

| Test ID | Function | File | Description |
|---------|----------|------|-------------|
| TC-CHEST-001 | `test_chest_no_font_render_in_draw_on_second_call` | `../../tests/ui/test_text_cache.py` | ChestDrawMixin must not call `font.render` for static title on 2nd draw |

### Integration Tests

| Test ID | Function | File | Description |
|---------|----------|------|-------------|
| TC-IT-001 | — | — | Open inventory, do not modify HP/GOLD/LVL for 60 frames → 0 calls to `font.render` after frame 1 |
| TC-IT-002 | — | — | Take damage (HP changes), open inventory → HP surface recalculated with the new value |
| TC-IT-003 | — | — | `GameStateManager.run()` with a simulated 2-second freeze → player does not teleport (position remains unchanged after 1 long tick) |

---

## Error Handling Matrix

| Error | Fallback | Logging |
|---|---|---|
| `font.render()` fails (font is None) — `AssetManager.get_font()` failed | Fallback surface from init returned — no crash in `draw()` | `logging.error` in `_load_font()` |
| `clock.tick()` returns 0 — first frame | `min(0 / 1000.0, 0.1)` = 0.0 — correct, no division by zero | N/A |
| `clock.tick()` returns negative value — never on pygame-ce | `max(0.0, min(raw_dt, 0.1))` if safeguard added | N/A — defensive only |
| `_text_cache` absent — initialization forgotten in `__init__` | `AttributeError` at the first call of `_get_text_surface` — caught in TC-INV-001 test | Caught immediately by TC-INV-001 |

---

## Bundling & Native-Module Audit

- **BM1:** N/A — pure Python project, no bundled SvelteKit/Next.js framework
- **BM2:** N/A
- **BM3:** N/A — no native module introduced
- **BM4:** N/A — no constants renamed in this spec

---

## File Tree

```
src/
├── engine/
│   ├── game.py                    [MODIFY] — DT clamp ×3 occurrences
│   └── game_state_manager.py      [MODIFY] — DT clamp ×1 occurrence
└── ui/
    ├── hud.py                     [MODIFY] — _render_text_cached replaces _render_text_centered
    ├── inventory.py               [MODIFY] — add self._text_cache inside __init__
    ├── inventory_draw.py          [MODIFY] — _draw_stats, _draw_character_preview, _draw_grid, _draw_item_info
    └── chest_draw.py              [MODIFY] — pre-rendered title + quantity surfaces
```

---

## Assumptions

| Assumption | Risk | Handling | Source Type |
|---|---|---|---|
| A | Low | H | gcloud test |
| B | Low | H | gcloud test |
| C | Low | H | gcloud test |

