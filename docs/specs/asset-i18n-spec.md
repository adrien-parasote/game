> **Design tokens** – see [design-tokens.md](./design-tokens.md)
[assumption: "All implicit constants and defaults are documented here – pending detailed entries"] – risk: Low

# Technical Specification — Asset Manager & I18n [Implementation]

> Document Type: Implementation
> Sources: `src/engine/asset_manager.py` (80 LOC), `src/engine/i18n.py` (62 LOC)

This document specifies the AS-IS implementation of the two singleton services providing centralized asset caching and localization.

## 1. Goal Description

Provide singleton-scoped, cached access to game assets (images, fonts) and localized strings, ensuring zero redundant I/O in the game loop.

## 2. Component Overview

| Module | File | LOC | Pattern | Responsibility |
|--------|------|-----|---------|----------------|
| `AssetManager` | `src/engine/asset_manager.py` | 80 | `__new__` singleton | Image & font caching |
| `I18nManager` | `src/engine/i18n.py` | 62 | `__new__` singleton | Localized string resolution |

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

**Implication**: Every `AssetManager()` call returns the same instance. `_init_manager()` runs exactly once.

### 3.2. Cache Structure

| Cache | Type | Key | Value |
|-------|------|-----|-------|
| `_images` | `dict[str, Surface]` | File path | Loaded & converted surface |
| `_fonts` | `dict[tuple[str, int], Font]` | `(path, size)` | Loaded font object |
| `_tilesets` | `dict` | — | Reserved (unused) |
| `_sounds` | `dict` | — | Reserved (unused) |

### 3.3. Interfaces

#### `get_image(path: str, fallback: bool = False) -> Surface`

**Behavior**:
1. Return cached surface if `path` in `_images`
2. If file doesn't exist:
   - `fallback=True` → log ERROR, return 32×32 magenta placeholder
   - `fallback=False` → raise FileNotFoundError
3. Load with `pygame.image.load(path).convert_alpha()`
4. Cache and return

#### `get_font(path: str, size: int) -> Font`

**Behavior**:
1. Return cached font if `(path, size)` in `_fonts`
2. If `path` exists → `pygame.font.Font(path, size)`
3. If `path` is None/empty/missing → `pygame.font.SysFont("Arial", size)`
4. On any exception → `pygame.font.Font(None, size)` (pygame default)

#### `clear_cache() -> None`

Clears all 4 cache dictionaries. Used for testing or scene reset.

### 3.4. Consumers

| Caller | Method Used | Context |
|--------|-------------|---------|
| `DialogueManager` | `get_font()` | Load narrative & title fonts |
| `TitleScreen` | `get_font()` via `__import__` | Load menu fonts |
| `PauseScreen` | `get_font()` via `__import__` | Load pause menu fonts |
| `SaveMenuOverlay` | `get_font()` via `__import__` | Load slot fonts |
| `InventoryUI` | `get_font()` | Load inventory fonts |
| `HUD` | `get_font()` | Load HUD display fonts |

> **Anti-pattern noted**: `TitleScreen`, `PauseScreen`, and `SaveMenuOverlay` use `__import__("src.engine.asset_manager", fromlist=["AssetManager"])` to break circular imports. This is fragile and should be refactored to constructor injection.

## 4. I18nManager

### 4.1. Singleton Pattern

Same `__new__` pattern as `AssetManager`. Initial state: `data = {}`, `current_locale = "en"`.

### 4.2. Locale Loading

```python
def load(self, locale: str) -> None
```

**Behavior**:
1. Set `self.current_locale = locale`
2. Resolve path: `{project_root}/assets/langs/{locale}.json`
3. If exists → `json.load()` into `self.data`
4. If missing → log WARNING, `self.data = {}`
5. On any exception → log ERROR, `self.data = {}`

**File format**: Nested JSON object, e.g.:
```json
{
  "menu": { "new_game": "Nouvelle Partie", "load": "Charger" },
  "seasons": { "SPRING": "Printemps" },
  "items": { "iron_sword": { "name": "Épée de fer", "description": "..." } }
}
```

### 4.3. Interfaces

#### `get(key: str, default: str = "") -> str`

**Behavior**: Resolve dot-separated key (e.g., `"seasons.SPRING"`) by walking the nested dict. Returns `default` or `key` if not found.

#### `get_item(item_id: str) -> dict[str, str]`

**Returns**: `{"name": ..., "description": ...}` from `data["items"][item_id]`.

**Fallback**:
- `name` → `item_id.replace("_", " ").capitalize()`
- `description` → `"No description available."`

#### `get_translations() -> dict`

Returns the full `self.data` dictionary.

### 4.4. Consumers

| Caller | Usage |
|--------|-------|
| `Inventory.create_item()` | `get_item(item_id)` for localized name/description |
| `TitleScreen` | `get(key)` for menu labels |
| `PauseScreen` | `get(key)` for pause button labels |
| `SaveMenuOverlay` | `get(key)` for slot details |
| `HUD` | `get(key)` for season/time display |
| `GameStateManager` | `load(locale)` at startup |

## 5. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Call `pygame.image.load()` directly in game loop | Use `AssetManager.get_image()` | Disk I/O per frame kills performance |
| Create new `AssetManager()` expecting a fresh instance | Understand singleton — it returns the same object | State is shared |
| Access `i18n.data` directly | Use `get()` or `get_item()` | Handles missing keys gracefully |
| Hardcode translated strings | Use `I18nManager.get(key, default)` | Breaks localization |
| Use `__import__` to access AssetManager | Import normally or inject via constructor | Fragile, hides dependencies |

## 6. Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Image file not found | `os.path.exists()` | Log ERROR | Magenta placeholder or raise |
| Image load failure | `pygame.error` | Log ERROR | Magenta placeholder or raise |
| Font file not found | `os.path.exists()` | Silent | `SysFont("Arial", size)` |
| Font load failure | `Exception` | Log ERROR | `pygame.font.Font(None, size)` |
| Locale file not found | `os.path.exists()` | Log WARNING | `data = {}` |
| Locale JSON invalid | `Exception` | Log ERROR | `data = {}` |
| Translation key missing | `KeyError`/`TypeError` | Silent | Return `default` or `key` |

## 7. Test Case Specifications

### Unit Tests
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

## 8. Deep Links
- **AssetManager**: [asset_manager.py:7](../../src/engine/asset_manager.py#L7)
- **I18nManager**: [i18n.py:7](../../src/engine/i18n.py#L7)
- **Locale files**: `assets/langs/*.json`

## 9. Assumptions

| # | Assumption | Risk | Validation |
|---|-----------|------|------------|
| 1 | Singleton pattern is intentional and final | Low | ADR-pattern |
| 2 | All images use `.convert_alpha()` (RGBA) | Low | No opaque-only optimization needed |
| 3 | Locale files are well-formed JSON | Medium | No schema validation currently |
| 4 | `__import__` pattern for AssetManager access will be refactored | Medium | Tech debt item |
