# Technical Specification — Asset Manager & I18n [Implementation]

> Document Type: Implementation

> **Document Type:** Implementation
> **Sources:** `src/engine/asset_manager.py` (80 LOC), `src/engine/i18n.py` (62 LOC), `src/config.py`

This document specifies the AS-IS implementation of the two singleton services providing centralized asset caching, localization, and the three-tier font system for visual identity.

---

## 1. Goal Description

Provide singleton-scoped, cached access to game assets (images, fonts) and localized strings, ensuring zero redundant I/O in the game loop and maintaining a clear visual hierarchy between prestige, narrative, and technical data.

---

## 2. Component Overview

| Module | File | LOC | Pattern | Responsibility |
|--------|------|-----|---------|----------------|
| `AssetManager` | `src/engine/asset_manager.py` | 80 | `__new__` singleton | Image & font caching |
| `I18nManager` | `src/engine/i18n.py` | 62 | `__new__` singleton | Localized string resolution |
| Config Fonts | `src/config.py` | — | Central constants | Tiered font and size constants |

---

## 3. AssetManager

### 3.1. Singleton Pattern
```python
class AssetManager:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_manager()
        return cls._instance
```
Every `AssetManager()` call returns the same instance. `_init_manager()` runs exactly once.

### 3.2. Cache Structure
| Cache | Type | Key | Value |
|-------|------|-----|-------|
| `_images` | `dict[str, Surface]` | File path | Loaded & converted surface |
| `_fonts` | `dict[tuple[str, int], Font]` | `(path, size)` | Loaded font object |

### 3.3. Interfaces
#### `get_image(path: str, fallback: bool = False) -> Surface`
1. Return cached surface if `path` in `_images`.
2. If file doesn't exist:
   - `fallback=True` -> log ERROR, return 32×32 magenta placeholder.
   - `fallback=False` -> raise FileNotFoundError.
3. Load with `pygame.image.load(path).convert_alpha()`.
4. Cache and return.

#### `get_font(path: str, size: int) -> Font`
1. Return cached font if `(path, size)` in `_fonts`.
2. If `path` exists -> `pygame.font.Font(path, size)`.
3. If `path` is None/empty/missing -> `pygame.font.SysFont("Arial", size)`.
4. On any exception -> `pygame.font.Font(None, size)` (pygame default).

#### `clear_cache() -> None`
Clears all cache dictionaries. Used for testing or scene reset.

---

## 4. Font System Tiering & Visual Identity

To enhance visual hierarchy and game identity, a three-tier font system is established in `src/config.py`:

### 4.1 Tier Configurations
- **Prestige (Noble)**: `FONT_NOBLE = "assets/fonts/metamorphous-regular.ttf"` (Size: 24)
  - Used for Speaker Names, Character Names, Item Names, and Clock/Time HUD displays.
- **Narrative (Reading)**: `FONT_NARRATIVE = "assets/fonts/m5x7.ttf"` (Size: 22)
  - Used for dialogue text, item descriptions, and main reading panels. Text wrapping is enforced to prevent parchment clipping.
- **Technical (Data/Numbers)**: `FONT_TECH = "assets/fonts/m5x7.ttf"` (Size: 20)
  - Used for quantities (`x99`), stats (`HP`, `LVL`), and currency counters (`GOLD`).

> **Note:** m5x7 is a pixel font with native 5×7 glyph size. Sizes 22 (≈3× native) and 20 are the validated rendering sizes for this project — confirmed to produce clean pixel-aligned output with Pygame CE's font renderer.

---

## 5. I18nManager

### 5.1. Singleton Pattern
Same `__new__` pattern as `AssetManager`. Initial state: `data = {}`, `current_locale = "en"`.

### 5.2. Locale Loading
```python
def load(self, locale: str) -> None
```
1. Set `self.current_locale = locale`.
2. Resolve path: `{project_root}/assets/langs/{locale}.json`.
3. If exists -> `json.load()` into `self.data`.
4. If missing -> log WARNING, `self.data = {}`.
5. On any exception -> log ERROR, `self.data = {}`.

**File format**: Nested JSON object, e.g.:
```json
{
  "menu": { "new_game": "Nouvelle Partie", "load": "Charger" },
  "seasons": { "SPRING": "Printemps" },
  "items": { "iron_sword": { "name": "Épée de fer", "description": "..." } }
}
```

### 5.3. Interfaces
#### `get(key: str, default: str = "") -> str`
Resolve dot-separated key (e.g., `"seasons.SPRING"`) by walking the nested dict. Returns `default` or `key` if not found.

#### `get_item(item_id: str) -> dict[str, str]`
Returns `{"name": ..., "description": ...}` from `data["items"][item_id]`.
- **Fallback Name**: `item_id.replace("_", " ").capitalize()`
- **Fallback Description**: `"No description available."`

---

## 6. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Call `pygame.image.load()` directly in game loop | Use `AssetManager.get_image()` | Disk I/O per frame kills performance |
| Create new `AssetManager()` expecting a fresh instance | Understand singleton — it returns the same object | State is shared |
| Access `i18n.data` directly | Use `get()` or `get_item()` | Handles missing keys gracefully |
| Hardcode translated strings | Use `I18nManager.get(key, default)` | Breaks localization |
| Use `__import__` to access AssetManager | Import normally or inject via constructor | Fragile, hides dependencies |
| Use noble font for small numbers | Use technical font (`FONT_TECH`) | Noble is too wide for small slots |
| Scale fonts manually | Use appropriate sizes in `Settings` | Crisp rendering of pixel fonts |

---

## 7. Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Image file not found | `os.path.exists()` | Log ERROR | Magenta placeholder or raise |
| Image load failure | `pygame.error` | Log ERROR | Magenta placeholder or raise |
| Font file not found | `os.path.exists()` | Silent | `SysFont("Arial", size)` or default |
| Font load failure | Exception | Log ERROR | `pygame.font.Font(None, size)` |
| Locale file not found | `os.path.exists()` | Log WARNING | `data = {}` |
| Locale JSON invalid | Exception | Log ERROR | `data = {}` |
| Translation key missing | KeyError/TypeError | Silent | Return `default` or `key` |

---

## 8. Test Case Specifications

### 8.1 Unit Tests
| Test ID | Component | Input | Expected Output |
|---------|-----------|-------|-----------------|
| UT-AM-01 | `AssetManager()` | Two calls | Same instance (singleton) |
| UT-AM-02 | `get_image` | Valid path | Surface returned, cached |
| UT-AM-03 | `get_image` | Missing path, fallback=True | Magenta 32×32 surface |
| UT-AM-04 | `get_image` | Missing path, fallback=False | FileNotFoundError raised |
| UT-AM-05 | `get_font` | Valid path + size | Font returned, cached |
| UT-AM-06 | `get_font` | Missing path | SysFont fallback |
| UT-AM-07 | `clear_cache` | After loading | All caches empty |
| UT-I18-01 | `I18nManager()` | Two calls | Same instance |
| UT-I18-02 | `load` | Valid locale file | `data` populated |
| UT-I18-03 | `load` | Missing locale file | `data = {}`, WARNING logged |
| UT-I18-04 | `get` | Existing key `"menu.quit"` | Returns translated string |
| UT-I18-05 | `get` | Missing key | Returns default or key |
| UT-I18-06 | `get_item` | Known item | `{"name": ..., "description": ...}` |
| UT-I18-07 | `get_item` | Unknown item | Fallback name from ID |
| TC-FONT-01 | Settings | Access `FONT_NOBLE` | Returns Metamorphous path |
| TC-FONT-02 | InventoryUI | Render quantity | Uses `tech_font` |
| TC-FONT-03 | Dialogue | Render title | Uses `noble_font` |

---

## 9. Deep Links
- **AssetManager**: [asset_manager.py:7](../../src/engine/asset_manager.py#L7)
- **I18nManager**: [i18n.py:7](../../src/engine/i18n.py#L7)
- **Font config**: [config.py L1](../../src/config.py#L1)

---

## 10. Linked Test Functions

| Test ID | Test Function | File |
|---------|---------------|------|
| TC-FONT-01 | `test_settings_load` | `../../tests/engine/test_game.py:L509` |
| TC-FONT-02 | `test_font_tiers_exist` | `../../tests/engine/test_game.py:L516` |
| TC-FONT-03 | `test_font_tiers_exist` | `../../tests/engine/test_game.py:L516` |

## Assumptions

| Assumption | Risk | Handling | Source Type |
|---|---|---|---|
| A | Low | H | gcloud test |
| B | Low | H | gcloud test |
| C | Low | H | gcloud test |

## Error Handling

| Error | Response | Fallback | Detection | Logging |
|---|---|---|---|---|
| TBD | TBD | TBD | TBD | TBD |

## Test Cases

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

## Anti-patterns

| Anti-pattern | Why it's bad | What to do instead |
|---|---|---|
| TBD | TBD | TBD |
| TBD | TBD | TBD |
| TBD | TBD | TBD |
| TBD | TBD | TBD |
| TBD | TBD | TBD |
