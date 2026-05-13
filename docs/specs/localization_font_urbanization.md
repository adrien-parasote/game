> **Design tokens** – see [design-tokens.md](./design-tokens.md)
[assumption: "All implicit constants and defaults are documented here – pending detailed entries"] – risk: Low

# SPEC: Font System Tiering & Visual Identity

> Document Type: Implementation


## Goal
Establish a three-tier font system to enhance visual hierarchy and game identity, separating prestige, narrative, and technical data.

## Proposed Changes

### [MODIFY] [config.py](../../src/config.py#L1)
- Replace `MAIN_FONT` with tiered constants:
    - `FONT_NOBLE`: `assets/fonts/metamorphous-regular.ttf` (Prestige)
    - `FONT_NARRATIVE`: `assets/fonts/m5x7.ttf` (Reading)
    - `FONT_TECH`: `assets/fonts/m5x7.ttf` (Data/Numbers)
- Centralize sizes: `FONT_SIZE_NOBLE` (24), `FONT_SIZE_NARRATIVE` (22), `FONT_SIZE_TECH` (20).

### [MODIFY] [inventory.py](../../src/ui/inventory.py#L1)
- Use `FONT_NOBLE` for Character Name and Item Names.
- Use `FONT_NARRATIVE` for Item Descriptions.
- Use `FONT_TECH` for HP, LVL, GOLD, and item quantities (x99).

### [MODIFY] [hud.py](../../src/ui/hud.py#L1)
- Use `FONT_NOBLE` for the clock and time display (prestige).

### [MODIFY] [dialogue.py](../../src/ui/dialogue.py#L1)
- Use `FONT_NOBLE` for Speaker Names, scaled by 1.5x (e.g., `int(Settings.FONT_SIZE_NOBLE * 1.5)`).
- Use `FONT_NARRATIVE` for Dialogue text, scaled by 1.5x (e.g., `int(Settings.FONT_SIZE_NARRATIVE * 1.5)`).

### [MODIFY] [inventory.py](../../src/ui/inventory.py#L1)
- Implement text wrapping for `FONT_NARRATIVE` in descriptions to prevent text clipping.
- Start description Y-offset immediately below the item name to ensure fit within the parchment background.

## Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Use a single font for all UI | Use tiered fonts based on role | Improves visual hierarchy |
| Use Settings.MAIN_FONT | Use `Settings.FONT_NOBLE/NARRATIVE/TECH` | Legacy constant removal |
| Use Noble font for small numbers | Use Tech font | Noble is too wide for small slots |
| Scale fonts manually | Use appropriate sizes in `Settings` | Crisp rendering of pixel fonts |
| Hardcode font paths | Load from centralized Settings | Enables easy swapping and prevents missing files |

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
- **Font config**: [config.py L1](../../src/config.py#L1)
- **`InventoryUI` font usage**: [inventory.py L1](../../src/ui/inventory.py#L1)
- **`HUD` font usage**: [hud.py L1](../../src/ui/hud.py#L1)
- **`DialogueManager`**: [dialogue.py L1](../../src/ui/dialogue.py#L1)
- **`i18n` module**: [i18n.py L1](../../src/engine/i18n.py#L1)

### Linked Test Functions

| Test ID | Test Function | File |
|---------|---------------|------|
| TC-FONT-01 | `test_settings_load` | `../../tests/engine/test_game.py:L509` |
| TC-FONT-02 | `test_font_tiers_exist` | `../../tests/engine/test_game.py:L516` |
| TC-FONT-03 | `test_font_tiers_exist` | `../../tests/engine/test_game.py:L516` |


## Assumptions
| # | Assumption | Risk | Validation |
|---|---|---|---|
| 1 | System performs adequately | Low | Playtest |
| 2 | Inputs are sanitized | Low | Code review |
| 3 | Components interact seamlessly | Low | Integration tests |

## Test Case Specifications
| ID | Description | Type |
|---|---|---|
| TC-001 | Validate initialization | Unit |
| TC-002 | Validate state transition | Unit |
| TC-003 | Validate edge case handling | Unit |
| TC-004 | Validate error raising | Unit |
| TC-005 | Validate boundary conditions | Unit |
| IT-001 | Validate module integration | Integration |
| IT-002 | Validate state persistence | Integration |
| IT-003 | Validate system flow | Integration |
