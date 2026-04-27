# Technical Spec - RPG Inventory Interface

## 📋 AI-Ready Documentation

### 1. Asset Mapping

| Component | Path | fallback |
|-----------|------|----------|
| Background | `assets/images/ui/01-inventory.png` | None |
| Slot Frame | `assets/images/ui/03-inventory_slot.png` | None |
| Active Tab | `assets/images/ui/02-active_tab.png` | None |

### 2. Layout & Coordinates (Screen: 1280x720)

#### Character Zone (Left)
- **Position:** Orange zone on background.
- **Content:** Player 'Idle' animation scaled to fit.
- **Equipment Slots (Magenta):** 
    1. HEAD
    2. UPPER BODY
    3. LOWER BODY
    4. SHOES
    5. RIGHT HAND
    6. LEFT HAND
    7. BELT
    8. BAG
    *(Exact pixels to be determined by background asset analysis or manual alignment)*

#### Tabs & Grid (Right)
- **Tabs (Rouge):** 4 tabs. 
    - Tab 1: 'Inventaire' (Default active).
- **Grid (Blue):** 24 slots (6x4).
    - Grid Start Pos: (To be determined).
    - Slot Size: 32x32 (standard) or adjusted to asset.

#### Info Zone (Bottom Right - Green)
- **Stats:** 'LVL {n}', 'HP {current}/{max}', 'GOLD {n}'.
- **Font:** Use HUD font (pixel-friendly).

### 3. Interaction Matrix

| Action | Input | Result |
|--------|-------|--------|
| Open | Key 'I' | `is_inventory_open = True`, TimeSystem paused, `mouse_visible = True` |
| Close | Key 'I' | `is_inventory_open = False`, TimeSystem resumed, `mouse_visible = False` |
| Switch Tab | Mouse Click | Updates `active_tab`, renders `08-active_tab.png` on selected tab. |
| Hover Slot | Mouse Move | Highlight slot (if visual feedback asset exists) |

## Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Update game entities while inventory is open | Early return in `update()` | Prevents physics/logic glitches during pause |
| Hardcode all coordinates in `Game` | Use a dedicated `InventoryUI` class | Separation of concerns |
| Redraw background every frame unnecessarily | Cache background surface if possible | Performance |
| Mix UI assets with Game assets | Keep them in `assets/images/ui/` | Organization |
| Use raw pixels without scaling awareness | Use relative offsets or scale constants | Resolution flexibility |

## Test Case Specifications

### Unit Tests Required
| Test ID | Component | Input | Expected Output |
|---------|-----------|-------|-----------------|
| INV-001 | InventoryUI | `toggle()` | `is_open` toggles correctly |
| INV-002 | Player | `stats` init | Level=1, HP=100, Gold=0 |
| INV-003 | InventoryUI | Click Tab 2 | `active_tab` = 1 (index 1) |

### Integration Tests Required
| Test ID | Flow | Setup | Verification |
|---------|------|-------|--------------|
| IT-INV-01 | Toggle Pause | Open Inventory | `Game` loop skips system updates |
| IT-INV-02 | Mouse Visibility | Toggle Inventory | `pygame.mouse.get_visible()` matches state |

## Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Missing Asset | `FileNotFoundError` | Log error | Render colored placeholder box |
| Invalid Tab Index | `IndexError` | Clamp to 0..3 | Default to tab 0 |
| Player Ref Missing | `None` check | Log CRITICAL | Disable Inventory |

## Deep Links
- [Game Engine Loop](file:///Users/adrien.parasote/Documents/perso/game/src/engine/game.py#L494)
- [Player Stats](file:///Users/adrien.parasote/Documents/perso/game/src/entities/player.py)
- [Control Settings](file:///Users/adrien.parasote/Documents/perso/game/src/config.py#L25)
