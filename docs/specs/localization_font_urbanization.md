# SPEC: Localization & Font Urbanization

## Goal
Centralize font management and enable localization for item names and descriptions.

## Proposed Changes

### [MODIFY] [config.py](file:///Users/adrien.parasote/Documents/perso/game/src/config.py)
- Add `FONT_DEFAULT`: `"assets/fonts/alagard.ttf"` (or similar).
- Add `FONT_SIZE_UI`: `16`, `FONT_SIZE_TITLE`: `24`.
- Initialize `Settings.UI_FONT` and `Settings.TITLE_FONT`.

### [MODIFY] [inventory_system.py](file:///Users/adrien.parasote/Documents/perso/game/src/engine/inventory_system.py)
- `Item` dataclass: `name` and `description` will now hold localization keys or default to the ID.
- `add_item` logic: use the item ID as the translation key.

### [MODIFY] [inventory.py](file:///Users/adrien.parasote/Documents/perso/game/src/ui/inventory.py)
- Use `Settings.TITLE_FONT` and `Settings.UI_FONT`.
- Resolve `item.name` and `item.description` using the game's active language dictionary (`hud._lang` or similar).

### [MODIFY] [hud.py](file:///Users/adrien.parasote/Documents/perso/game/src/ui/hud.py), [dialogue.py](file:///Users/adrien.parasote/Documents/perso/game/src/ui/dialogue.py)
- Use centralized fonts from `Settings`.

### [MODIFY] [fr.json](file:///Users/adrien.parasote/Documents/perso/game/assets/langs/fr.json)
- Add an `items` section:
```json
{
  "items": {
    "wood": {
      "name": "Bois",
      "description": "Un morceau de bois solide."
    },
    ...
  }
}
```

## Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Load fonts in `__init__` | Use `Settings` pre-loaded fonts | Performance and memory efficiency |
| Hardcode French/English | Use the lang system keys | Maintainability and portability |
| Duplicate lang data | Inject a reference to the active lang | Single source of truth |
| Use system fonts for pixel art | Use bundled .ttf pixel fonts | Visual consistency with the game style |
| Scale fonts with `smoothscale` | Use `pygame.font.Font` with correct size | Text legibility and sharpness |

## Test Case Specifications

| Test ID | Component | Input | Expected Output |
|---------|-----------|-------|-----------------|
| TC-LOC-01 | InventoryUI | Hover over 'wood' (FR) | Displays "Bois" and description |
| TC-LOC-02 | Settings | Change FONT_PATH | All UI elements update font |

## Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Missing Translation | Key not in `items` | Use title-cased ID | "Unknown Item" |
| Font Not Found | `IOError` on load | Log warning | Use system default font |
