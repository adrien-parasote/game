# SPEC: Font System Tiering & Visual Identity

> Document Type: Implementation


## Goal
Establish a three-tier font system to enhance visual hierarchy and game identity, separating prestige, narrative, and technical data.

## Proposed Changes

### [MODIFY] [config.py](file:///Users/adrien.parasote/Documents/perso/game/src/config.py)
- Replace `MAIN_FONT` with tiered constants:
    - `FONT_NOBLE`: `assets/fonts/metamorphous-regular.ttf` (Prestige)
    - `FONT_NARRATIVE`: `assets/fonts/vcr_osd_mono.ttf` (Reading)
    - `FONT_TECH`: `assets/fonts/m5x7.ttf` (Data/Numbers)
- Centralize sizes: `FONT_SIZE_NOBLE` (24), `FONT_SIZE_NARRATIVE` (22), `FONT_SIZE_TECH` (20).

### [MODIFY] [inventory.py](file:///Users/adrien.parasote/Documents/perso/game/src/ui/inventory.py)
- Use `FONT_NOBLE` for Character Name and Item Names.
- Use `FONT_NARRATIVE` for Item Descriptions.
- Use `FONT_TECH` for HP, LVL, GOLD, and item quantities (x99).

### [MODIFY] [hud.py](file:///Users/adrien.parasote/Documents/perso/game/src/ui/hud.py)
- Use `FONT_NOBLE` for the clock and time display (prestige).

### [MODIFY] [dialogue.py](file:///Users/adrien.parasote/Documents/perso/game/src/ui/dialogue.py)
- Use `FONT_NOBLE` for Speaker Names, scaled by 1.5x (e.g., `int(Settings.FONT_SIZE_NOBLE * 1.5)`).
- Use `FONT_NARRATIVE` for Dialogue text, scaled by 1.5x (e.g., `int(Settings.FONT_SIZE_NARRATIVE * 1.5)`).

### [MODIFY] [inventory.py](file:///Users/adrien.parasote/Documents/perso/game/src/ui/inventory.py)
- Implement text wrapping for `FONT_NARRATIVE` in descriptions to prevent text clipping.
- Start description Y-offset immediately below the item name to ensure fit within the parchment background.

## Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Use a single font for all UI | Use tiered fonts based on role | Improves visual hierarchy |
| Use `Settings.MAIN_FONT` | Use `Settings.FONT_NOBLE/NARRATIVE/TECH` | Legacy constant removal |
| Use Noble font for small numbers | Use Tech font | Noble is too wide for small slots |
| Scale fonts manually | Use appropriate sizes in `Settings` | Crisp rendering of pixel fonts |

## Test Case Specifications

| Test ID | Component | Input | Expected Output |
|---------|-----------|-------|-----------------|
| TC-FONT-01 | Settings | Access `FONT_NOBLE` | Returns Metamorphous path |
| TC-FONT-02 | InventoryUI | Render quantity | Uses `tech_font` |
| TC-FONT-03 | Dialogue | Render title | Uses `noble_font` |

## Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Missing Font File | `os.path.exists` | Log Error | Fallback to `pygame.font.Font(None, size)` |
| Invalid Size | `Settings` | Log Warning | Use default size (20) |

## Deep Links
- **Font config**: [config.py L1](file:///Users/adrien.parasote/Documents/perso/game/src/config.py#L1)
- **`InventoryUI` font usage**: [inventory.py L1](file:///Users/adrien.parasote/Documents/perso/game/src/ui/inventory.py#L1)
- **`HUD` font usage**: [hud.py L1](file:///Users/adrien.parasote/Documents/perso/game/src/ui/hud.py#L1)
- **`DialogueManager`**: [dialogue.py L1](file:///Users/adrien.parasote/Documents/perso/game/src/ui/dialogue.py#L1)
- **`i18n` module**: [i18n.py L1](file:///Users/adrien.parasote/Documents/perso/game/src/engine/i18n.py#L1)