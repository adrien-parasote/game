# Technical Spec - RPG Inventory Interface (v1.1)

## 📋 System Architecture

### 1. Asset Mapping
| Component | Path | Description |
|-----------|------|-------------|
| Background | `assets/images/ui/01-inventory.png` | Main 1344x704 parchment background |
| Slot Frame | `assets/images/ui/03-inventory_slot.png` | Used for grid slots only (55x58) |
| Active Tab | `assets/images/ui/02-active_tab.png` | Highlight overlay (143x67) |

### 2. Layout & Positioning (Relative to Background Top-Left)

#### Character Preview (Center Left)
- **Position:** (358, 311)
- **Behavior:** No scaling (base sprite size).
- **Controls:** Animates in place. Direction can be changed using `MOVE_UP/DOWN/LEFT/RIGHT` keys while inventory is open.

#### Equipment Zones (Interaction Only)
- **Rendering:** No slot frames drawn (transparent zones).
- **Coordinates (Centers):**
    - HEAD: (354, 160) | BAG: (212, 290) | BELT: (211, 405) | LEFT_HAND: (242, 529)
    - UPPER_BODY: (499, 291) | LOWER_BODY: (498, 406) | RIGHT_HAND: (469, 529) | SHOES: (354, 549)

#### Inventory Grid (Right Tab)
- **Dimensions:** 7 Columns x 4 Rows (28 total slots).
- **Spacing:** Equalized at 72px (horizontal & vertical).
- **Start Pos:** (713, 219)

#### Tab System
- **Quantity:** 4 Tabs.
- **Positions (Centers):** X: [733, 863, 992, 1121] | Y: 130
- **Logic:** `02-active_tab.png` is rendered only on the currently selected tab.

#### Info Bar (Bottom Right)
- **Green Zone:** Center (929, 551).
- **Content:** LVL (Left), HP (Center), GOLD (Right) aligned in the bar.

### 3. Interaction Matrix

| Action | Input | Result |
|--------|-------|--------|
| Toggle | Key 'I' | Toggles `is_open`, pauses `TimeSystem`, manages `mouse_visible`. |
| Rotate Preview | Dir Keys | Updates `preview_state` ('up', 'down', 'left', 'right'). |
| Select Tab | Left Click | Updates `active_tab` index. |
| Click Slot | Left Click | Logs interaction for grid index or equipment ID. |

## ❌ Anti-Patterns (DO NOT)
1.  **Do NOT scale** the character preview sprite; use native resolution.
2.  **Do NOT draw** `03-inventory_slot.png` over equipment zones.
3.  **Do NOT process** movement while inventory is open (pause logic).
4.  **Do NOT hardcode** offsets; always relate to `bg_rect.topleft`.

## 🔍 Verification
- **TDD:** `tests/test_inventory.py` covers logic states.
- **Coords:** Verified via `detect_clusters_fuzzy.py` on the legacy asset.
